import time
from datetime import datetime, timedelta

from PyQt6 import QtCore

from app.database import AppDatabase
from app.paths import APP_DB_PATH, DOWNLOADS_DIR, PROFILES_PATH, resolve_app_path
from app.profiles.cache import clean_tiktok_upload_cache
from app.profiles.store import get_assigned_profiles, split_channel_urls, update_profile_status
from app.reporting.telegram import TelegramReporter
from app.tiktok.uploader import TikTokUploader
from app.video.padder import VideoPadder
from app.video.splitter import VideoSplitter
from app.youtube.downloader import VideoDownloader
from app.youtube.scanner import YouTubeScanner, build_channel_tab_url

class UploadWorkerCore:
    def __init__(
        self,
        database,
        scanner,
        downloader,
        uploader,
        reporter,
        splitter=None,
        padder=None,
        split_threshold_minutes=10,
        short_pad_threshold_seconds=55,
        short_pad_target_seconds=61,
        split_schedule_enabled=False,
        split_schedule_gap_hours=3,
        daily_upload_limit=3,
        profile_cache_cleaner=clean_tiktok_upload_cache,
        clock=None,
    ):
        self.database = database
        self.scanner = scanner
        self.downloader = downloader
        self.uploader = uploader
        self.reporter = reporter
        self.splitter = splitter
        self.padder = padder
        self.split_threshold_minutes = float(split_threshold_minutes or 10)
        self.short_pad_threshold_seconds = float(short_pad_threshold_seconds or 55)
        self.short_pad_target_seconds = float(short_pad_target_seconds or 61)
        self.split_schedule_enabled = bool(split_schedule_enabled)
        self.split_schedule_gap_hours = int(split_schedule_gap_hours or 3)
        self.daily_upload_limit = self._coerce_daily_upload_limit(daily_upload_limit)
        self.profile_cache_cleaner = profile_cache_cleaner
        self.clock = clock or datetime.now

    def process_profile(self, profile):
        profile_id = profile.get("id", "")
        profile_name = profile.get("name", "")
        channel_urls = split_channel_urls(profile.get("channel_url") or "")
        channel_mode = (profile.get("channel_mode") or "shorts").strip().lower()
        if not channel_urls:
            self.database.write_log("WARN", profile_id, None, f"{profile_name}: missing YouTube channel URL")
            return {"status": "skipped", "reason": "missing_channel_url"}
        if self.database.has_running_job(profile_id):
            self.database.write_log("INFO", profile_id, None, f"{profile_name}: skipped because profile has running job")
            return {"status": "skipped", "reason": "profile_locked"}

        quota = self._daily_upload_quota(profile_id)
        if quota["remaining_slots"] <= 0:
            self.database.write_log(
                "INFO",
                profile_id,
                None,
                f"{profile_name}: skipped because daily TikTok upload limit reached "
                f"({quota['uploaded_today']}/{quota['daily_limit']})",
            )
            return self._daily_upload_limit_result(quota)

        start = time.time()
        job_id = None
        video = None
        try:
            total_videos = 0
            total_inserted = 0
            first_channel_url = channel_urls[0]
            for channel_url in channel_urls:
                scan_url = build_channel_tab_url(channel_url, channel_mode)
                self.database.write_log("INFO", profile_id, None, f"{profile_name}: scanning {scan_url}")
                videos = self.scanner.scan(channel_url, channel_mode)
                inserted = self.database.upsert_videos(profile_id, channel_url, channel_mode, videos)
                total_videos += len(videos)
                total_inserted += inserted
            self.database.write_log(
                "INFO",
                profile_id,
                None,
                f"{profile_name}: found {total_videos} videos, {total_inserted} new from {len(channel_urls)} URLs",
            )

            video = self.database.get_newest_unprocessed_video(profile_id)
            if not video:
                return {"status": "skipped", "reason": "no_new_video"}

            self.database.update_video_status(video["id"], "downloading")
            downloaded = self.downloader.download(video["video_url"])

            self.database.update_video_status(video["id"], "downloaded", downloaded["file_path"])
            upload_title = downloaded.get("title") or video["video_id"]
            upload_items = self._build_upload_items(downloaded, upload_title, channel_mode)
            needed_uploads = len(upload_items)
            quota = self._daily_upload_quota(profile_id)
            if needed_uploads > quota["remaining_slots"]:
                self.database.update_video_status(video["id"], "discovered", downloaded["file_path"])
                self.database.write_log(
                    "INFO",
                    profile_id,
                    None,
                    f"{profile_name}: skipped {video['video_url']} because daily TikTok upload slots are not enough "
                    f"(need {needed_uploads}, remaining {quota['remaining_slots']})",
                )
                return self._daily_upload_limit_result(quota, needed_uploads=needed_uploads)

            job_id = self.database.create_job(
                profile_id,
                video["video_id"],
                video["video_url"],
                video.get("channel_url") or first_channel_url,
            )
            self.database.update_video_status(video["id"], "uploading", downloaded["file_path"])
            upload_results = self._upload_items(profile.get("profile_path", ""), upload_items)
            cache_result = self._clean_tiktok_upload_cache(profile_id, job_id, profile.get("profile_path", ""))
            padded_short = any(item.get("padded_short") for item in upload_items)

            elapsed = time.time() - start
            self.database.update_video_status(video["id"], "uploaded", downloaded["file_path"])
            self.database.finish_job(job_id, "uploaded", elapsed, uploaded_count=needed_uploads)
            self.database.write_log("INFO", profile_id, job_id, f"{profile_name}: uploaded {video['video_url']}")
            self._send_report(
                profile_id=profile_id,
                job_id=job_id,
                profile_name=profile_name,
                channel_url=video.get("channel_url") or first_channel_url,
                video_url=video["video_url"],
                status="uploaded",
                elapsed_seconds=elapsed,
                detail="; ".join([
                    f"job_id={job_id}",
                    f"video_id={video['video_id']}",
                    f"title={upload_title}",
                    f"file={downloaded['file_path']}",
                    f"padded_short={'true' if padded_short else 'false'}",
                    f"uploaded_parts={len(upload_items)}",
                    f"cache_cleaned_mb={cache_result.get('deleted_bytes', 0) / 1024 / 1024:.2f}",
                    f"tiktok_status={upload_results[-1].get('status', '') if upload_results else ''}",
                ]),
            )
            return {
                "status": "uploaded",
                "video_url": video["video_url"],
                "uploaded_parts": needed_uploads,
                "padded_short": padded_short,
                "cache_cleaned_bytes": cache_result.get("deleted_bytes", 0),
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
                channel_url=video.get("channel_url") if video else "\n".join(channel_urls),
                video_url=video["video_url"] if video else "",
                status="failed",
                elapsed_seconds=elapsed,
                detail=str(error),
            )
            return {"status": "failed", "error": str(error)}

    def _build_upload_items(self, downloaded, upload_title, channel_mode="shorts"):
        duration = float(downloaded.get("duration") or 0)
        if self.splitter and duration > self.split_threshold_minutes * 60:
            parts = self.splitter.split_into_equal_parts(downloaded["file_path"], duration, parts=3)
            upload_items = []
            for index, part in enumerate(parts):
                item = {
                    "file_path": part["file_path"],
                    "title": f"{upload_title} Part {part['part_number']}",
                }
                if self.split_schedule_enabled and index > 0:
                    item["schedule"] = self._schedule_for_split_part(index)
                upload_items.append(item)
            return upload_items
        file_path = downloaded["file_path"]
        padded_short = False
        if self._should_pad_short(channel_mode, duration):
            file_path = self.padder.pad_last_frame_to_duration(
                downloaded["file_path"],
                duration,
                target_seconds=self.short_pad_target_seconds,
            )
            padded_short = True
        return [{"file_path": file_path, "title": upload_title, "padded_short": padded_short}]

    def _coerce_daily_upload_limit(self, value):
        try:
            limit = int(float(value))
        except (TypeError, ValueError):
            limit = 3
        return max(1, limit)

    def _daily_upload_quota(self, profile_id):
        uploaded_today = self.database.get_uploaded_count_today(profile_id, now=self.clock())
        remaining_slots = max(0, self.daily_upload_limit - uploaded_today)
        return {
            "uploaded_today": uploaded_today,
            "daily_limit": self.daily_upload_limit,
            "remaining_slots": remaining_slots,
        }

    def _daily_upload_limit_result(self, quota, needed_uploads=None):
        result = {
            "status": "skipped",
            "reason": "daily_upload_limit",
            "uploaded_today": quota["uploaded_today"],
            "daily_limit": quota["daily_limit"],
            "remaining_slots": quota["remaining_slots"],
        }
        if needed_uploads is not None:
            result["needed_uploads"] = needed_uploads
        return result

    def _should_pad_short(self, channel_mode, duration_seconds):
        return (
            self.padder is not None
            and (channel_mode or "").strip().lower() == "shorts"
            and self.short_pad_threshold_seconds <= float(duration_seconds or 0) < self.short_pad_target_seconds
        )

    def _schedule_for_split_part(self, part_index):
        scheduled_at = self._schedule_base_time() + timedelta(hours=self.split_schedule_gap_hours * part_index)
        return {
            "day": scheduled_at.day,
            "month": scheduled_at.month,
            "year": scheduled_at.year,
            "hour": scheduled_at.hour,
            "minute": scheduled_at.minute,
        }

    def _schedule_base_time(self):
        base = self.clock().replace(second=0, microsecond=0)
        remainder = base.minute % 5
        if remainder:
            base += timedelta(minutes=5 - remainder)
        return base

    def _upload_items(self, profile_path, upload_items):
        if len(upload_items) > 1 and hasattr(self.uploader, "upload_many"):
            return self.uploader.upload_many(profile_path, upload_items)
        return [
            self.uploader.upload(profile_path, item["file_path"], title=item["title"])
            for item in upload_items
        ]

    def _clean_tiktok_upload_cache(self, profile_id, job_id, profile_path):
        if not self.profile_cache_cleaner or not profile_path:
            return {"deleted_bytes": 0, "deleted_paths": [], "errors": []}
        try:
            result = self.profile_cache_cleaner(profile_path) or {}
        except Exception as error:
            self.database.write_log("WARN", profile_id, job_id, f"Dọn cache tải lên TikTok lỗi: {error}")
            return {"deleted_bytes": 0, "deleted_paths": [], "errors": [str(error)]}

        deleted_bytes = int(result.get("deleted_bytes") or 0)
        errors = result.get("errors") or []
        if deleted_bytes:
            deleted_mb = deleted_bytes / 1024 / 1024
            self.database.write_log("INFO", profile_id, job_id, f"Đã dọn cache tải lên TikTok: {deleted_mb:.2f} MB")
        if errors:
            self.database.write_log("WARN", profile_id, job_id, f"Dọn cache tải lên TikTok lỗi: {'; '.join(errors)}")
        return result

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
        ffmpeg_path = self.database.get_setting("ffmpeg_path", r"C:\ffmpeg\bin\ffmpeg.exe")
        reporter = TelegramReporter(
            self.database.get_setting("telegram_bot_token", ""),
            self.database.get_setting("telegram_chat_id", ""),
        )
        core = UploadWorkerCore(
            database=self.database,
            scanner=YouTubeScanner(),
            downloader=VideoDownloader(self._download_dir()),
            uploader=TikTokUploader(),
            reporter=reporter,
            splitter=VideoSplitter(ffmpeg_path),
            padder=VideoPadder(ffmpeg_path),
            split_threshold_minutes=self._split_threshold_minutes(),
            short_pad_threshold_seconds=self._short_pad_threshold_seconds(),
            split_schedule_enabled=self._split_schedule_enabled(),
            split_schedule_gap_hours=self._split_schedule_gap_hours(),
            daily_upload_limit=self._daily_upload_limit(),
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

    def _download_dir(self):
        return resolve_app_path(self.database.get_setting("download_dir", str(DOWNLOADS_DIR)), DOWNLOADS_DIR)

    def _split_threshold_minutes(self):
        try:
            value = float(self.database.get_setting("split_threshold_minutes", "10"))
        except ValueError:
            value = 10
        return max(1, value)

    def _short_pad_threshold_seconds(self):
        try:
            value = float(self.database.get_setting("short_pad_threshold_seconds", "55"))
        except ValueError:
            value = 55
        return max(1, value)

    def _split_schedule_enabled(self):
        return self.database.get_setting("split_schedule_enabled", "0") == "1"

    def _split_schedule_gap_hours(self):
        try:
            value = int(float(self.database.get_setting("split_schedule_gap_hours", "3")))
        except ValueError:
            value = 3
        return max(1, value)

    def _daily_upload_limit(self):
        try:
            value = int(float(self.database.get_setting("daily_upload_limit_per_account", "3")))
        except ValueError:
            value = 3
        return max(1, value)
