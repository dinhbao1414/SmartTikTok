import tempfile
import unittest
from pathlib import Path

from app.database import AppDatabase
from app.workers.upload_worker import UploadWorkerCore, YoutubeToTikTokWorker


class FakeScanner:
    def __init__(self):
        self.calls = 0

    def scan(self, channel_url, mode):
        self.calls += 1
        return [{"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"}]


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

    def upload_many(self, profile_path, upload_items):
        self.upload_many_calls.append({"profile_path": profile_path, "upload_items": upload_items})
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


class FakeReporter:
    def __init__(self):
        self.reports = []

    def send_job_report(self, **kwargs):
        self.reports.append(kwargs)
        return {"sent": True}


class UploadWorkerCoreTest(unittest.TestCase):
    def test_poll_interval_allows_values_below_ten_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "app.db"
            db = AppDatabase(db_path)
            db.initialize()
            db.set_setting("poll_interval_seconds", "1")
            worker = YoutubeToTikTokWorker(db_path=db_path)

            self.assertEqual(worker._poll_interval(), 1)

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
