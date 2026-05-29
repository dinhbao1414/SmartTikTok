import tempfile
import unittest
from pathlib import Path

from app_database import AppDatabase


class AppDatabaseTest(unittest.TestCase):
    def test_initialize_creates_default_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()

            self.assertEqual(db.get_setting("poll_interval_seconds"), "10")
            self.assertEqual(db.get_setting("telegram_bot_token"), "")
            self.assertEqual(db.get_setting("split_threshold_minutes"), "10")
            self.assertEqual(db.get_setting("ffmpeg_path"), r"C:\ffmpeg\bin\ffmpeg.exe")

    def test_upsert_videos_deduplicates_per_profile_and_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()

            inserted_first = db.upsert_videos(
                profile_id="p1",
                channel_url="https://www.youtube.com/@hoangacc/shorts",
                channel_mode="shorts",
                videos=[{"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"}],
            )
            inserted_second = db.upsert_videos(
                profile_id="p1",
                channel_url="https://www.youtube.com/@hoangacc/shorts",
                channel_mode="shorts",
                videos=[{"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"}],
            )

            self.assertEqual(inserted_first, 1)
            self.assertEqual(inserted_second, 0)
            newest = db.get_newest_unprocessed_video("p1")
            self.assertEqual(newest["video_id"], "aaaaaaaaaaa")

    def test_job_and_log_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()

            job_id = db.create_job(
                "p1",
                "aaaaaaaaaaa",
                "https://www.youtube.com/watch?v=aaaaaaaaaaa",
                "https://www.youtube.com/@hoangacc/videos",
            )
            db.write_log("INFO", "p1", job_id, "download started")
            db.finish_job(job_id, "uploaded", 12.5, "")

            logs = db.get_recent_logs(limit=10)
            self.assertEqual(logs[0]["message"], "download started")
            self.assertEqual(db.get_job(job_id)["status"], "uploaded")

    def test_has_running_job_tracks_profile_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()

            job_id = db.create_job(
                "p1",
                "aaaaaaaaaaa",
                "https://www.youtube.com/shorts/aaaaaaaaaaa",
                "https://www.youtube.com/@hoangacc/shorts",
            )

            self.assertTrue(db.has_running_job("p1"))
            self.assertFalse(db.has_running_job("p2"))
            db.finish_job(job_id, "uploaded", 10, "")
            self.assertFalse(db.has_running_job("p1"))

    def test_recover_interrupted_jobs_unlocks_running_jobs_and_retryable_videos(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            db.upsert_videos(
                profile_id="p1",
                channel_url="https://www.youtube.com/@hoangacc/shorts",
                channel_mode="shorts",
                videos=[{"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"}],
            )
            video = db.get_newest_unprocessed_video("p1")
            db.update_video_status(video["id"], "uploading", "downloads/a.mp4")
            job_id = db.create_job(
                "p1",
                "aaaaaaaaaaa",
                "https://www.youtube.com/shorts/aaaaaaaaaaa",
                "https://www.youtube.com/@hoangacc/shorts",
            )

            result = db.recover_interrupted_jobs("Worker restarted")

            self.assertEqual(result, {"jobs": 1, "videos": 1})
            self.assertFalse(db.has_running_job("p1"))
            self.assertEqual(db.get_job(job_id)["status"], "failed")
            self.assertEqual(db.get_job(job_id)["error"], "Worker restarted")
            self.assertEqual(db.get_newest_unprocessed_video("p1")["status"], "failed")


if __name__ == "__main__":
    unittest.main()
