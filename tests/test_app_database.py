import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.database import AppDatabase


class AppDatabaseTest(unittest.TestCase):
    def test_initialize_creates_default_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()

            self.assertEqual(db.get_setting("poll_interval_seconds"), "10")
            self.assertEqual(db.get_setting("profiles_dir"), "profiles")
            self.assertEqual(db.get_setting("telegram_bot_token"), "")
            self.assertEqual(db.get_setting("split_threshold_minutes"), "10")
            self.assertEqual(db.get_setting("short_pad_threshold_seconds"), "55")
            self.assertEqual(db.get_setting("split_schedule_enabled"), "0")
            self.assertEqual(db.get_setting("split_schedule_gap_hours"), "3")
            self.assertEqual(db.get_setting("daily_upload_limit_per_account"), "3")
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
            db.finish_job(job_id, "uploaded", 12.5, "", uploaded_count=3)

            logs = db.get_recent_logs(limit=10)
            self.assertEqual(logs[0]["message"], "download started")
            self.assertEqual(db.get_job(job_id)["status"], "uploaded")
            self.assertEqual(db.get_job(job_id)["uploaded_count"], 3)

    def test_get_uploaded_count_today_sums_uploaded_parts_per_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            today_job = db.create_job("p1", "a", "https://youtu.be/a", "https://www.youtube.com/@a")
            other_profile_job = db.create_job("p2", "b", "https://youtu.be/b", "https://www.youtube.com/@b")
            old_job = db.create_job("p1", "c", "https://youtu.be/c", "https://www.youtube.com/@c")
            db.finish_job(today_job, "uploaded", 1, "", uploaded_count=3)
            db.finish_job(other_profile_job, "uploaded", 1, "", uploaded_count=2)
            db.finish_job(old_job, "uploaded", 1, "", uploaded_count=3)
            with closing(db.connect()) as connection:
                connection.execute(
                    "UPDATE upload_jobs SET finished_at = ? WHERE id = ?",
                    ("2026-05-30T23:59:59", old_job),
                )
                connection.commit()

            self.assertEqual(db.get_uploaded_count_today("p1", now="2026-05-31T12:00:00"), 3)
            self.assertEqual(db.get_uploaded_count_today("p2", now="2026-05-31T12:00:00"), 2)

    def test_initialize_migrates_existing_upload_jobs_uploaded_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "app.db"
            db = AppDatabase(db_path)
            with closing(db.connect()) as connection:
                connection.executescript(
                    """
                    CREATE TABLE upload_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_id TEXT NOT NULL,
                        video_id TEXT NOT NULL,
                        video_url TEXT NOT NULL,
                        channel_url TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT NOT NULL DEFAULT '',
                        elapsed_seconds REAL NOT NULL DEFAULT 0,
                        error TEXT NOT NULL DEFAULT ''
                    );
                    """
                )
                connection.commit()

            db.initialize()
            job_id = db.create_job("p1", "a", "https://youtu.be/a", "https://www.youtube.com/@a")
            db.finish_job(job_id, "uploaded", 1, "", uploaded_count=2)

            self.assertEqual(db.get_job(job_id)["uploaded_count"], 2)

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
