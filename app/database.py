import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    channel_url TEXT NOT NULL,
    channel_mode TEXT NOT NULL CHECK(channel_mode IN ('shorts', 'videos')),
    video_id TEXT NOT NULL,
    video_url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    downloaded_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'discovered',
    UNIQUE(profile_id, channel_mode, video_id)
);

CREATE TABLE IF NOT EXISTS upload_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    video_url TEXT NOT NULL,
    channel_url TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    elapsed_seconds REAL NOT NULL DEFAULT 0,
    uploaded_count INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS app_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    level TEXT NOT NULL,
    profile_id TEXT NOT NULL DEFAULT '',
    job_id INTEGER,
    message TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "poll_interval_seconds": "10",
    "profiles_dir": "profiles",
    "download_dir": "downloads",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "upload_latest_on_first_scan": "1",
    "split_threshold_minutes": "10",
    "short_pad_threshold_seconds": "55",
    "split_schedule_enabled": "0",
    "split_schedule_gap_hours": "3",
    "daily_upload_limit_per_account": "3",
    "ffmpeg_path": r"C:\ffmpeg\bin\ffmpeg.exe",
}

VIDEO_STATUSES = {"discovered", "downloading", "downloaded", "uploading", "uploaded", "failed", "skipped"}
JOB_STATUSES = {"running", "uploaded", "failed", "skipped"}

class AppDatabase:
    def __init__(self, db_path):
        self.db_path = Path(db_path)

    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with closing(self.connect()) as connection:
            connection.executescript(SCHEMA_SQL)
            self._migrate_schema(connection)
            connection.executemany(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                DEFAULT_SETTINGS.items(),
            )
            connection.commit()

    def _migrate_schema(self, connection):
        upload_job_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(upload_jobs)").fetchall()
        }
        if "uploaded_count" not in upload_job_columns:
            connection.execute(
                "ALTER TABLE upload_jobs ADD COLUMN uploaded_count INTEGER NOT NULL DEFAULT 0"
            )

    def get_setting(self, key, default=""):
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        with closing(self.connect()) as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
            connection.commit()

    def upsert_videos(self, profile_id, channel_url, channel_mode, videos):
        now = datetime.now().isoformat(timespec="seconds")
        inserted = 0
        with closing(self.connect()) as connection:
            for video in videos:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO videos(
                        profile_id, channel_url, channel_mode, video_id, video_url, first_seen_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (profile_id, channel_url, channel_mode, video["video_id"], video["video_url"], now),
                )
                inserted += cursor.rowcount
            connection.commit()
        return inserted

    def get_newest_unprocessed_video(self, profile_id):
        with closing(self.connect()) as connection:
            row = connection.execute(
                """
                SELECT * FROM videos
                WHERE profile_id = ? AND status IN ('discovered', 'failed')
                ORDER BY id DESC
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
            return dict(row) if row else None

    def update_video_status(self, video_id, status, downloaded_path=""):
        with closing(self.connect()) as connection:
            connection.execute(
                """
                UPDATE videos
                SET status = ?, downloaded_path = COALESCE(NULLIF(?, ''), downloaded_path)
                WHERE id = ?
                """,
                (status, downloaded_path, video_id),
            )
            connection.commit()

    def create_job(self, profile_id, video_id, video_url, channel_url):
        now = datetime.now().isoformat(timespec="seconds")
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO upload_jobs(profile_id, video_id, video_url, channel_url, status, started_at)
                VALUES(?, ?, ?, ?, 'running', ?)
                """,
                (profile_id, video_id, video_url, channel_url, now),
            )
            connection.commit()
            return cursor.lastrowid

    def finish_job(self, job_id, status, elapsed_seconds, error="", uploaded_count=0):
        now = datetime.now().isoformat(timespec="seconds")
        count = max(0, int(uploaded_count or 0)) if status == "uploaded" else 0
        with closing(self.connect()) as connection:
            connection.execute(
                """
                UPDATE upload_jobs
                SET status = ?, finished_at = ?, elapsed_seconds = ?, error = ?, uploaded_count = ?
                WHERE id = ?
                """,
                (status, now, float(elapsed_seconds), error or "", count, job_id),
            )
            connection.commit()

    def get_uploaded_count_today(self, profile_id, now=None):
        current = self._coerce_datetime(now) if now is not None else datetime.now()
        start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        with closing(self.connect()) as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(
                    CASE WHEN uploaded_count > 0 THEN uploaded_count ELSE 1 END
                ), 0) AS total
                FROM upload_jobs
                WHERE profile_id = ?
                  AND status = 'uploaded'
                  AND finished_at >= ?
                  AND finished_at < ?
                """,
                (
                    profile_id,
                    start.isoformat(timespec="seconds"),
                    end.isoformat(timespec="seconds"),
                ),
            ).fetchone()
        return int(row["total"] if row else 0)

    def _coerce_datetime(self, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def get_job(self, job_id):
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT * FROM upload_jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def has_running_job(self, profile_id):
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM upload_jobs WHERE profile_id = ? AND status = 'running' LIMIT 1",
                (profile_id,),
            ).fetchone()
            return row is not None

    def recover_interrupted_jobs(self, reason):
        now = datetime.now().isoformat(timespec="seconds")
        with closing(self.connect()) as connection:
            job_cursor = connection.execute(
                """
                UPDATE upload_jobs
                SET status = 'failed', finished_at = ?, error = ?
                WHERE status = 'running'
                """,
                (now, reason),
            )
            video_cursor = connection.execute(
                """
                UPDATE videos
                SET status = 'failed'
                WHERE status IN ('downloading', 'uploading')
                """,
            )
            connection.commit()
            return {"jobs": job_cursor.rowcount, "videos": video_cursor.rowcount}

    def write_log(self, level, profile_id, job_id, message):
        now = datetime.now().isoformat(timespec="seconds")
        with closing(self.connect()) as connection:
            connection.execute(
                "INSERT INTO app_logs(created_at, level, profile_id, job_id, message) VALUES(?, ?, ?, ?, ?)",
                (now, level, profile_id or "", job_id, message),
            )
            connection.commit()

    def get_recent_logs(self, limit=200):
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM app_logs ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]
