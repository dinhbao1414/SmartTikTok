import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app.database import AppDatabase
import app.workers.upload_worker as upload_worker_module
from app.workers.upload_worker import UploadWorkerCore, YoutubeToTikTokWorker


class FakeScanner:
    def __init__(self):
        self.calls = 0
        self.scanned = []

    def scan(self, channel_url, mode):
        self.calls += 1
        self.scanned.append((channel_url, mode))
        return [{"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"}]

class MultiUrlScanner(FakeScanner):
    def scan(self, channel_url, mode):
        self.calls += 1
        self.scanned.append((channel_url, mode))
        video_id = "aaaaaaaaaaa" if channel_url.endswith("@a") else "bbbbbbbbbbb"
        return [{"video_id": video_id, "video_url": f"https://www.youtube.com/watch?v={video_id}"}]


class FakeDownloader:
    def __init__(self, tmp):
        self.tmp = Path(tmp)

    def download(self, video_url):
        file_path = self.tmp / "aaaaaaaaaaa.mp4"
        file_path.write_bytes(b"video")
        return {"video_id": "aaaaaaaaaaa", "title": "Video A", "file_path": str(file_path)}


class FakeUploader:
    def __init__(self):
        self.title = ""
        self.uploads = []
        self.upload_many_calls = []

    def upload(self, profile_path, video_path, title=""):
        self.title = title
        self.uploads.append({"profile_path": profile_path, "video_path": video_path, "title": title})
        return {"status": "uploaded", "file_path": str(video_path)}

    def upload_many(self, profile_path, upload_items, **kwargs):
        self.upload_many_calls.append({"profile_path": profile_path, "upload_items": upload_items, "kwargs": kwargs})
        results = []
        for item in upload_items:
            self.uploads.append({
                "profile_path": profile_path,
                "video_path": item["file_path"],
                "title": item["title"],
            })
            self.title = item["title"]
            results.append({"status": "uploaded", "file_path": str(item["file_path"])})
        return results

class FakeSplitter:
    def __init__(self):
        self.calls = []

    def split_into_equal_parts(self, video_path, duration_seconds, parts=3):
        self.calls.append((video_path, duration_seconds, parts))
        base = Path(video_path).parent
        result = []
        for part_number in range(1, parts + 1):
            file_path = base / f"part_{part_number}.mp4"
            file_path.write_bytes(b"part")
            result.append({"part_number": part_number, "file_path": str(file_path)})
        return result

class FakePadder:
    def __init__(self):
        self.calls = []

    def pad_last_frame_to_duration(self, video_path, duration_seconds, target_seconds=61):
        self.calls.append((video_path, duration_seconds, target_seconds))
        padded_path = Path(video_path).with_name(f"{Path(video_path).stem}_padded_61s.mp4")
        padded_path.write_bytes(b"padded")
        return str(padded_path)


class FakeReporter:
    def __init__(self):
        self.reports = []

    def send_job_report(self, **kwargs):
        self.reports.append(kwargs)
        return {"sent": True}


class UploadWorkerCoreTest(unittest.TestCase):
    def test_clean_tiktok_upload_cache_removes_blob_cache_only(self):
        from app.profiles.cache import clean_tiktok_upload_cache

        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile"
            blob_dir = profile_path / "Default" / "IndexedDB" / "https_www.tiktok.com_0.indexeddb.blob"
            leveldb_dir = profile_path / "Default" / "IndexedDB" / "https_www.tiktok.com_0.indexeddb.leveldb"
            cookie_file = profile_path / "Default" / "Network" / "Cookies"
            blob_dir.mkdir(parents=True)
            leveldb_dir.mkdir(parents=True)
            cookie_file.parent.mkdir(parents=True)
            (blob_dir / "blob-a").write_bytes(b"a" * 11)
            (leveldb_dir / "meta").write_bytes(b"metadata")
            cookie_file.write_bytes(b"cookies")

            result = clean_tiktok_upload_cache(profile_path)

            self.assertEqual(result["deleted_bytes"], 11)
            self.assertFalse(blob_dir.exists())
            self.assertTrue(leveldb_dir.exists())
            self.assertTrue(cookie_file.exists())

    def test_process_profile_cleans_tiktok_upload_cache_after_success(self):
        class CacheCleaner:
            def __init__(self):
                self.calls = []

            def __call__(self, profile_path):
                self.calls.append(profile_path)
                return {"deleted_bytes": 11, "deleted_paths": ["blob"]}

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            cleaner = CacheCleaner()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=FakeDownloader(tmp),
                uploader=FakeUploader(),
                reporter=FakeReporter(),
                profile_cache_cleaner=cleaner,
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "shorts",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(cleaner.calls, [profile["profile_path"]])
            self.assertEqual(result["cache_cleaned_bytes"], 11)
            logs = db.get_recent_logs(10)
            self.assertTrue(any("Đã dọn cache tải lên TikTok" in log["message"] for log in logs))

    def test_process_profile_skips_before_scan_when_daily_upload_limit_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            existing_job = db.create_job("p1", "old", "https://youtu.be/old", "https://www.youtube.com/@old")
            db.finish_job(existing_job, "uploaded", 1, "", uploaded_count=3)
            scanner = FakeScanner()
            uploader = FakeUploader()
            core = UploadWorkerCore(
                database=db,
                scanner=scanner,
                downloader=FakeDownloader(tmp),
                uploader=uploader,
                reporter=FakeReporter(),
                daily_upload_limit=3,
                clock=lambda: datetime.now(),
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "shorts",
            }

            result = core.process_profile(profile)

            self.assertEqual(result, {
                "status": "skipped",
                "reason": "daily_upload_limit",
                "uploaded_today": 3,
                "daily_limit": 3,
                "remaining_slots": 0,
            })
            self.assertEqual(scanner.calls, 0)
            self.assertEqual(uploader.uploads, [])

    def test_process_profile_skips_split_video_when_remaining_slots_are_not_enough(self):
        class LongVideoDownloader(FakeDownloader):
            def download(self, video_url):
                result = super().download(video_url)
                result["duration"] = 11 * 60
                return result

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            existing_job = db.create_job("p1", "old", "https://youtu.be/old", "https://www.youtube.com/@old")
            db.finish_job(existing_job, "uploaded", 1, "", uploaded_count=1)
            uploader = FakeUploader()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=LongVideoDownloader(tmp),
                uploader=uploader,
                reporter=FakeReporter(),
                splitter=FakeSplitter(),
                split_threshold_minutes=10,
                daily_upload_limit=3,
                clock=lambda: datetime.now(),
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "videos",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["reason"], "daily_upload_limit")
            self.assertEqual(result["needed_uploads"], 3)
            self.assertEqual(result["remaining_slots"], 2)
            self.assertEqual(uploader.uploads, [])
            self.assertEqual(db.get_newest_unprocessed_video("p1")["status"], "discovered")

    def test_poll_interval_allows_values_below_ten_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "app.db"
            db = AppDatabase(db_path)
            db.initialize()
            db.set_setting("poll_interval_seconds", "1")
            worker = YoutubeToTikTokWorker(db_path=db_path)

            self.assertEqual(worker._poll_interval(), 1)

    def test_worker_resolves_relative_download_dir_under_app_downloads_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            app_downloads = Path(tmp) / "tool" / "downloads"
            db_path = Path(tmp) / "app.db"
            db = AppDatabase(db_path)
            db.initialize()
            db.set_setting("download_dir", "downloads")
            with patch.object(upload_worker_module, "DOWNLOADS_DIR", app_downloads):
                worker = YoutubeToTikTokWorker(db_path=db_path)
                self.assertEqual(worker._download_dir(), app_downloads)

    def test_process_profile_scans_downloads_uploads_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            reporter = FakeReporter()
            uploader = FakeUploader()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=FakeDownloader(tmp),
                uploader=uploader,
                reporter=reporter,
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "shorts",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(uploader.title, "Video A")
            self.assertEqual(db.get_newest_unprocessed_video("p1"), None)
            self.assertEqual(len(reporter.reports), 1)
            self.assertIn("aaaaaaaaaaa", reporter.reports[0]["video_url"])
            self.assertIn("title=Video A", reporter.reports[0]["detail"])
            self.assertIn("video_id=aaaaaaaaaaa", reporter.reports[0]["detail"])
            self.assertIn("tiktok_status=uploaded", reporter.reports[0]["detail"])
            logs = db.get_recent_logs(10)
            self.assertTrue(
                any("scanning https://www.youtube.com/@hoangacc/shorts" in log["message"] for log in logs)
            )

    def test_process_profile_scans_each_channel_url_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            scanner = MultiUrlScanner()
            core = UploadWorkerCore(
                database=db,
                scanner=scanner,
                downloader=FakeDownloader(tmp),
                uploader=FakeUploader(),
                reporter=FakeReporter(),
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@a\n\nhttps://www.youtube.com/@b",
                "channel_mode": "videos",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(scanner.scanned, [
                ("https://www.youtube.com/@a", "videos"),
                ("https://www.youtube.com/@b", "videos"),
            ])
            self.assertEqual(db.get_newest_unprocessed_video("p1")["video_id"], "aaaaaaaaaaa")

    def test_process_profile_splits_long_video_and_uploads_three_parts(self):
        class LongVideoDownloader(FakeDownloader):
            def download(self, video_url):
                result = super().download(video_url)
                result["duration"] = 11 * 60
                return result

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            uploader = FakeUploader()
            splitter = FakeSplitter()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=LongVideoDownloader(tmp),
                uploader=uploader,
                reporter=FakeReporter(),
                splitter=splitter,
                split_threshold_minutes=10,
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "videos",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(result["uploaded_parts"], 3)
            self.assertEqual([upload["title"] for upload in uploader.uploads], [
                "Video A Part 1",
                "Video A Part 2",
                "Video A Part 3",
            ])
            self.assertEqual(len(uploader.upload_many_calls), 1)
            self.assertEqual(len(splitter.calls), 1)

    def test_process_profile_schedules_split_parts_after_first_upload(self):
        class LongVideoDownloader(FakeDownloader):
            def download(self, video_url):
                result = super().download(video_url)
                result["duration"] = 11 * 60
                return result

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            uploader = FakeUploader()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=LongVideoDownloader(tmp),
                uploader=uploader,
                reporter=FakeReporter(),
                splitter=FakeSplitter(),
                split_threshold_minutes=10,
                split_schedule_enabled=True,
                split_schedule_gap_hours=3,
                clock=lambda: datetime(2026, 5, 29, 21, 10),
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "videos",
            }

            result = core.process_profile(profile)

            upload_items = uploader.upload_many_calls[0]["upload_items"]
            self.assertEqual(result["uploaded_parts"], 3)
            self.assertNotIn("schedule", upload_items[0])
            self.assertEqual(upload_items[1]["schedule"], {
                "day": 30,
                "month": 5,
                "year": 2026,
                "hour": 0,
                "minute": 10,
            })
            self.assertEqual(upload_items[2]["schedule"], {
                "day": 30,
                "month": 5,
                "year": 2026,
                "hour": 3,
                "minute": 10,
            })

    def test_successful_split_video_counts_as_three_daily_uploads(self):
        class LongVideoDownloader(FakeDownloader):
            def download(self, video_url):
                result = super().download(video_url)
                result["duration"] = 11 * 60
                return result

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=LongVideoDownloader(tmp),
                uploader=FakeUploader(),
                reporter=FakeReporter(),
                splitter=FakeSplitter(),
                split_threshold_minutes=10,
                daily_upload_limit=3,
                clock=lambda: datetime.now(),
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "videos",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(result["uploaded_parts"], 3)
            self.assertEqual(db.get_uploaded_count_today("p1"), 3)

    def test_process_profile_pads_short_at_threshold_before_upload(self):
        class ShortVideoDownloader(FakeDownloader):
            def download(self, video_url):
                result = super().download(video_url)
                result["duration"] = 55
                return result

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            uploader = FakeUploader()
            padder = FakePadder()
            reporter = FakeReporter()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=ShortVideoDownloader(tmp),
                uploader=uploader,
                reporter=reporter,
                padder=padder,
                short_pad_threshold_seconds=55,
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "shorts",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(result["padded_short"], True)
            self.assertEqual(len(padder.calls), 1)
            self.assertTrue(uploader.uploads[0]["video_path"].endswith("_padded_61s.mp4"))
            self.assertIn("padded_short=true", reporter.reports[0]["detail"])

    def test_process_profile_does_not_pad_regular_videos_mode(self):
        class ShortVideoDownloader(FakeDownloader):
            def download(self, video_url):
                result = super().download(video_url)
                result["duration"] = 55
                return result

        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            uploader = FakeUploader()
            padder = FakePadder()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=ShortVideoDownloader(tmp),
                uploader=uploader,
                reporter=FakeReporter(),
                padder=padder,
                short_pad_threshold_seconds=55,
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "videos",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["padded_short"], False)
            self.assertEqual(padder.calls, [])
            self.assertTrue(uploader.uploads[0]["video_path"].endswith("aaaaaaaaaaa.mp4"))

    def test_split_schedule_rounds_up_to_supported_five_minute_option(self):
        core = UploadWorkerCore(
            database=None,
            scanner=None,
            downloader=None,
            uploader=None,
            reporter=None,
            split_schedule_enabled=True,
            split_schedule_gap_hours=3,
            clock=lambda: datetime(2026, 5, 29, 21, 13),
        )

        self.assertEqual(core._schedule_for_split_part(1), {
            "day": 30,
            "month": 5,
            "year": 2026,
            "hour": 0,
            "minute": 15,
        })

    def test_process_profile_skips_missing_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            core = UploadWorkerCore(db, FakeScanner(), FakeDownloader(tmp), FakeUploader(), FakeReporter())

            result = core.process_profile({"id": "p1", "name": "Acc1", "profile_path": tmp})

            self.assertEqual(result["status"], "skipped")

    def test_process_profile_skips_when_profile_has_running_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            scanner = FakeScanner()
            core = UploadWorkerCore(db, scanner, FakeDownloader(tmp), FakeUploader(), FakeReporter())
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc",
                "channel_mode": "shorts",
            }
            db.create_job(
                "p1",
                "aaaaaaaaaaa",
                "https://www.youtube.com/shorts/aaaaaaaaaaa",
                "https://www.youtube.com/@hoangacc/shorts",
            )

            result = core.process_profile(profile)

            self.assertEqual(result, {"status": "skipped", "reason": "profile_locked"})
            self.assertEqual(scanner.calls, 0)


if __name__ == "__main__":
    unittest.main()
