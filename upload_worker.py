import time

from PyQt6 import QtCore

from app_database import AppDatabase
from app_paths import APP_DB_PATH, DOWNLOADS_DIR, PROFILES_PATH
from profile_store import get_assigned_profiles, update_profile_status
from telegram_reporter import TelegramReporter
from tiktok_uploader import TikTokUploader
from video_downloader import VideoDownloader
from video_splitter import VideoSplitter
from youtube_scanner import YouTubeScanner, build_channel_tab_url


class UploadWorkerCore:
    def __init__(
        self,
        database,
        scanner,
        downloader,
        uploader,
        reporter,
        splitter=None,
        split_threshold_minutes=10,
    ):
        self.database = database
        self.scanner = scanner
        self.downloader = downloader
        self.uploader = uploader
        self.reporter = reporter
        self.splitter = splitter
        self.split_threshold_minutes = float(split_threshold_minutes or 10)

    def process_profile(self, profile):
        profile_id = profile.get("id", "")
        profile_name = profile.get("name", "")
        channel_url = (profile.get("channel_url") or "").strip()
        channel_mode = (profile.get("channel_mode") or "shorts").strip().lower()
        if not channel_url:
            self.database.write_log("WARN", profile_id, None, f"{profile_name}: missing YouTube channel URL")
            return {"status": "skipped", "reason": "missing_channel_url"}
        if self.database.has_running_job(profile_id):
            self.database.write_log("INFO", profile_id, None, f"{profile_name}: skipped because profile has running job")
            return {"status": "skipped", "reason": "profile_locked"}

        start = time.time()
        job_id = None
        video = None
        try:
            scan_url = build_channel_tab_url(channel_url, channel_mode)
            self.database.write_log("INFO", profile_id, None, f"{profile_name}: scanning {scan_url}")
            videos = self.scanner.scan(channel_url, channel_mode)
            inserted = self.database.upsert_videos(profile_id, channel_url, channel_mode, videos)
            self.database.write_log("INFO", profile_id, None, f"{profile_name}: found {len(videos)} videos, {inserted} new")

            video = self.database.get_newest_unprocessed_video(profile_id)
            if not video:
                return {"status": "skipped", "reason": "no_new_video"}

            job_id = self.database.create_job(profile_id, video["video_id"], video["video_url"], channel_url)
            self.database.update_video_status(video["id"], "downloading")
            downloaded = self.downloader.download(video["video_url"])

            self.database.update_video_status(video["id"], "uploading", downloaded["file_path"])
            upload_title = downloaded.get("title") or video["video_id"]
            upload_items = self._build_upload_items(downloaded, upload_title)
            upload_results = self._upload_items(profile.get("profile_path", ""), upload_items)

            elapsed = time.time() - start
            self.database.update_video_status(video["id"], "uploaded", downloaded["file_path"])
            self.database.finish_job(job_id, "uploaded", elapsed)
            self.database.write_log("INFO", profile_id, job_id, f"{profile_name}: uploaded {video['video_url']}")
            self._send_report(
                profile_id=profile_id,
                job_id=job_id,
                profile_name=profile_name,
                channel_url=channel_url,
                video_url=video["video_url"],
                status="uploaded",
                elapsed_seconds=elapsed,
                detail="; ".join([
                    f"job_id={job_id}",
                    f"video_id={video['video_id']}",
                    f"title={upload_title}",
                    f"file={downloaded['file_path']}",
                    f"uploaded_parts={len(upload_items)}",
                    f"tiktok_status={upload_results[-1].get('status', '') if upload_results else ''}",
                ]),
            )
            return {
                "status": "uploaded",
                "video_url": video["video_url"],
                "uploaded_parts": len(upload_items),
                "uploads": upload_results,
            }
        except Exception as error:
            elapsed = time.time() - start
            if video:
                self.database.update_video_status(video["id"], "failed")
            if job_id:
                self.database.finish_job(job_id, "failed", elapsed, str(error))
            self.database.write_log("ERROR", profile_id, job_id, f"{profile_name}: {error}")
            self._send_report(
                profile_id=profile_id,
                job_id=job_id,
                profile_name=profile_name,
                channel_url=channel_url,
                video_url=video["video_url"] if video else "",
                status="failed",
                elapsed_seconds=elapsed,
                detail=str(error),
            )
            return {"status": "failed", "error": str(error)}

    def _build_upload_items(self, downloaded, upload_title):
        duration = float(downloaded.get("duration") or 0)
        if self.splitter and duration > self.split_threshold_minutes * 60:
            parts = self.splitter.split_into_equal_parts(downloaded["file_path"], duration, parts=3)
            return [
                {
                    "file_path": part["file_path"],
                    "title": f"{upload_title} Part {part['part_number']}",
                }
                for part in parts
            ]
        return [{"file_path": downloaded["file_path"], "title": upload_title}]

    def _upload_items(self, profile_path, upload_items):
        if len(upload_items) > 1 and hasattr(self.uploader, "upload_many"):
            return self.uploader.upload_many(profile_path, upload_items)
        return [
            self.uploader.upload(profile_path, item["file_path"], title=item["title"])
            for item in upload_items
        ]

    def _send_report(self, profile_id, job_id, **kwargs):
        try:
            return self.reporter.send_job_report(**kwargs)
        except Exception as error:
            self.database.write_log("ERROR", profile_id, job_id, f"Telegram report failed: {error}")
            return {"sent": False, "reason": str(error)}


class YoutubeToTikTokWorker(QtCore.QObject):
    log_created = QtCore.pyqtSignal()
    profile_status = QtCore.pyqtSignal(str, str)
    finished = QtCore.pyqtSignal()

    def __init__(self, profiles_path=PROFILES_PATH, db_path=APP_DB_PATH):
        super().__init__()
        self.profiles_path = profiles_path
        self.database = AppDatabase(db_path)
        self.stop_requested = False

    def stop(self):
        self.stop_requested = True

    def run_forever(self):
        self.database.initialize()
        recovered = self.database.recover_interrupted_jobs("Worker restarted")
        if recovered["jobs"] or recovered["videos"]:
            self.database.write_log(
                "WARN",
                "",
                None,
                f"Recovered interrupted jobs: jobs={recovered['jobs']}, videos={recovered['videos']}",
            )
        poll_interval = self._poll_interval()
        download_dir = self.database.get_setting("download_dir", str(DOWNLOADS_DIR))
        ffmpeg_path = self.database.get_setting("ffmpeg_path", r"C:\ffmpeg\bin\ffmpeg.exe")
        reporter = TelegramReporter(
            self.database.get_setting("telegram_bot_token", ""),
            self.database.get_setting("telegram_chat_id", ""),
        )
        core = UploadWorkerCore(
            database=self.database,
            scanner=YouTubeScanner(),
            downloader=VideoDownloader(download_dir),
            uploader=TikTokUploader(),
            reporter=reporter,
            splitter=VideoSplitter(ffmpeg_path),
            split_threshold_minutes=self._split_threshold_minutes(),
        )

        while not self.stop_requested:
            profiles = get_assigned_profiles(self.profiles_path)
            for profile in profiles:
                if self.stop_requested:
                    break
                update_profile_status(self.profiles_path, profile["id"], "Running")
                self.profile_status.emit(profile["id"], "Running")
                result = core.process_profile(profile)
                update_profile_status(self.profiles_path, profile["id"], result["status"])
                self.profile_status.emit(profile["id"], result["status"])
                self.log_created.emit()

            for _ in range(poll_interval):
                if self.stop_requested:
                    break
                time.sleep(1)

        self.finished.emit()

    def _poll_interval(self):
        try:
            value = int(self.database.get_setting("poll_interval_seconds", "10"))
        except ValueError:
            value = 10
        return max(1, value)

    def _split_threshold_minutes(self):
        try:
            value = float(self.database.get_setting("split_threshold_minutes", "10"))
        except ValueError:
            value = 10
        return max(1, value)
