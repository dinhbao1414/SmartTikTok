# YouTube To TikTok Uploader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Chrome-profile based workflow that polls assigned YouTube channel tabs, stores discovered videos, downloads new videos, uploads them to TikTok Studio with `remote_browser`, logs every step, and reports results to Telegram.

**Architecture:** Keep `data/profiles.json` as the source of Chrome profile rows, and add `data/app.db` SQLite tables for settings, discovered YouTube videos, upload jobs, and logs. A PyQt6 worker runs outside the GUI thread, scans each assigned profile channel every configured interval, downloads the newest unprocessed video, opens the matching Chrome profile through `remote_browser`, uploads to TikTok Studio, then writes logs and Telegram reports. No Selenium, no chromedriver, no GoLogin.

**Tech Stack:** Python 3.12, PyQt6, `requests`, SQLite via `sqlite3`, `yt-dlp`, local `remote_browser`, `unittest`.

---

## Current Context

- Project root: `c:\Users\thedu\Desktop\CODE\PYTHON TRAN DINH BAO\Buoi4`
- Current GUI: `gui.py` creates/deletes Chrome profiles and stores records in `data/profiles.json`.
- Current browser wrapper: `Controller/BrowserController.py` opens Chrome profiles through `remote_browser.LaunchBrowser`.
- `remote_browser.common.webelement.WebElement.send_file(file_path)` already supports CDP `DOM.setFileInputFiles`; use it for TikTok file picker.
- `remote_browser.remote.Remote.find_element`, `click_element`, `execute_script`, `move_to_random`, and `send_cdp` are available.
- Existing stale entrypoint: `main.py` still imports removed TikTok registration modules. Clean this during Task 1.
- Existing `tests/test_no_selenium.py` bans legacy TikTok registration terms. Update it so TikTok upload modules are allowed while Selenium/chromedriver/GoLogin remain banned.

## File Map

- Create: `app_paths.py`
  - Shared root paths: `DATA_DIR`, `PROFILES_PATH`, `APP_DB_PATH`, `DOWNLOADS_DIR`, `TIKTOK_UPLOAD_URL`.
- Modify: `requirements.txt`
  - Add `yt-dlp`.
- Modify: `main.py`
  - Launch current PyQt6 GUI without importing removed registration code.
- Modify: `profile_store.py`
  - Add channel assignment fields and update helpers while preserving existing JSON format.
- Create: `app_database.py`
  - SQLite schema, settings, videos, jobs, logs.
- Create: `youtube_scanner.py`
  - GET channel URL, parse `/shorts/<id>` or `/watch?v=<id>`, normalize video links.
- Create: `video_downloader.py`
  - Thin `yt-dlp` wrapper that downloads one video and returns local file path.
- Create: `telegram_reporter.py`
  - Telegram `sendMessage` wrapper with disabled state when token/chat id are empty.
- Create: `tiktok_uploader.py`
  - Upload local video file to TikTok Studio with `remote_browser`, no Selenium.
- Create: `upload_worker.py`
  - PyQt6 worker that orchestrates scan, DB, download, upload, logging, Telegram, and stop flag.
- Modify: `gui.py`
  - Redesign into tabs: Profiles, Settings, Logs. Add channel assignment, Run All, Stop, refresh logs.
- Modify: `tests/test_no_selenium.py`
  - Keep Selenium/chromedriver/GoLogin ban; remove old broad TikTok upload ban.
- Create: `tests/fixtures/youtube_shorts.html`
- Create: `tests/fixtures/youtube_videos.html`
- Create: `tests/test_profile_channels.py`
- Create: `tests/test_app_database.py`
- Create: `tests/test_youtube_scanner.py`
- Create: `tests/test_video_downloader.py`
- Create: `tests/test_telegram_reporter.py`
- Create: `tests/test_tiktok_uploader.py`
- Create: `tests/test_upload_worker.py`
- Create: `tests/test_gui_smoke.py`

## Data Contracts

`data/profiles.json` remains a list. Each record must keep old keys and add these keys:

```json
{
  "id": "b7e46ce097f04e6a9c47cff941d077cf",
  "name": "Acc1 1",
  "note": "",
  "group": "YTB",
  "type": "Chrome",
  "profile_path": "C:\\Users\\thedu\\Desktop\\CODE\\PYTHON TRAN DINH BAO\\Buoi4\\profiles\\b7e46ce097f04e6a9c47cff941d077cf",
  "created_at": "2026-05-24T19:12:44",
  "channel_url": "https://www.youtube.com/@hoangacc/shorts",
  "channel_mode": "shorts",
  "last_status": "Idle"
}
```

SQLite `data/app.db` owns runtime state:

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE videos (
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

CREATE TABLE app_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    level TEXT NOT NULL,
    profile_id TEXT NOT NULL DEFAULT '',
    job_id INTEGER,
    message TEXT NOT NULL
);
```

Settings defaults:

```python
DEFAULT_SETTINGS = {
    "poll_interval_seconds": "10",
    "download_dir": "downloads",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "upload_latest_on_first_scan": "1",
}
```

Status values:

```python
VIDEO_STATUSES = {"discovered", "downloading", "downloaded", "uploading", "uploaded", "failed", "skipped"}
JOB_STATUSES = {"running", "uploaded", "failed", "skipped"}
```

## Task 1: Dependencies, Paths, Entrypoint, Legacy Tests

**Files:**
- Create: `app_paths.py`
- Modify: `requirements.txt`
- Modify: `main.py`
- Modify: `tests/test_no_selenium.py`
- Test: `tests/test_no_selenium.py`

- [ ] **Step 1: Add failing no-legacy-entrypoint expectation**

Edit `tests/test_no_selenium.py` so it checks `main.py` as a live launcher and no removed controller imports exist:

```python
def test_main_has_no_removed_registration_imports(self):
    main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore")
    bad_terms = ("Controller.TiktokController", "YoloCaptchaV2", "ThreadTiktok", "Gologin")
    offenders = [term for term in bad_terms if term in main_text]
    self.assertEqual(offenders, [])
```

Also change `test_removed_tiktok_gologin_gui_stack` bad terms to:

```python
bad_terms = ("Gologin", "ThreadTiktok", "CaptchaSolve", "GetMail", "GetProxy")
```

This allows new TikTok upload automation while blocking the old registration stack.

- [ ] **Step 2: Run test to verify it fails on current `main.py`**

Run:

```powershell
python -m unittest tests.test_no_selenium -v
```

Expected: FAIL with `Controller.TiktokController` and `YoloCaptchaV2` found in `main.py`.

- [ ] **Step 3: Create shared path constants**

Create `app_paths.py`:

```python
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
PROFILES_PATH = DATA_DIR / "profiles.json"
APP_DB_PATH = DATA_DIR / "app.db"
DOWNLOADS_DIR = ROOT_DIR / "downloads"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video"
```

- [ ] **Step 4: Replace stale `main.py` with GUI launcher**

Replace `main.py` with:

```python
import sys

from PyQt6 import QtWidgets

from gui import Ui_MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Ui_MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Add downloader dependency**

Append this line to `requirements.txt` if it is missing:

```text
yt-dlp
```

Keep existing `requests` and PyQt6 dependencies.

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m unittest tests.test_no_selenium -v
python -m py_compile main.py app_paths.py
```

Expected: all PASS, no compile error.

## Task 2: Profile Channel Assignment

**Files:**
- Modify: `profile_store.py`
- Test: `tests/test_profile_channels.py`
- Test: `tests/test_chrome_profiles.py`

- [ ] **Step 1: Write failing profile channel tests**

Create `tests/test_profile_channels.py`:

```python
import tempfile
import unittest
from pathlib import Path

from profile_store import (
    create_chrome_profiles,
    load_profiles,
    update_profile_channel,
    get_assigned_profiles,
)


class ProfileChannelTest(unittest.TestCase):
    def test_created_profiles_have_empty_channel_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles = create_chrome_profiles(
                data_path=root / "data" / "profiles.json",
                profiles_dir=root / "profiles",
                count=1,
                name_prefix="acc",
                note="",
                group="YTB",
            )

            self.assertEqual(profiles[0]["channel_url"], "")
            self.assertEqual(profiles[0]["channel_mode"], "shorts")
            self.assertEqual(profiles[0]["last_status"], "Idle")

    def test_update_profile_channel_normalizes_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            create_chrome_profiles(data_path, root / "profiles", 1, "acc", "", "")
            profile_id = load_profiles(data_path)[0]["id"]

            updated = update_profile_channel(
                data_path=data_path,
                profile_id=profile_id,
                channel_url=" https://www.youtube.com/@hoangacc/videos ",
                channel_mode="videos",
            )

            self.assertTrue(updated)
            profile = load_profiles(data_path)[0]
            self.assertEqual(profile["channel_url"], "https://www.youtube.com/@hoangacc/videos")
            self.assertEqual(profile["channel_mode"], "videos")

    def test_get_assigned_profiles_returns_only_profiles_with_channel_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            create_chrome_profiles(data_path, root / "profiles", 2, "acc", "", "")
            profiles = load_profiles(data_path)
            update_profile_channel(data_path, profiles[1]["id"], "https://www.youtube.com/@hoangacc/shorts", "shorts")

            assigned = get_assigned_profiles(data_path)

            self.assertEqual([profile["id"] for profile in assigned], [profiles[1]["id"]])

    def test_update_profile_channel_rejects_invalid_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            create_chrome_profiles(data_path, root / "profiles", 1, "acc", "", "")
            profile_id = load_profiles(data_path)[0]["id"]

            with self.assertRaises(ValueError):
                update_profile_channel(data_path, profile_id, "https://www.youtube.com/@hoangacc/shorts", "live")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_profile_channels -v
```

Expected: FAIL because `update_profile_channel` and `get_assigned_profiles` do not exist.

- [ ] **Step 3: Add profile helpers**

Modify `profile_store.py`:

```python
VALID_CHANNEL_MODES = {"shorts", "videos"}


def ensure_profile_defaults(profile):
    profile.setdefault("channel_url", "")
    profile.setdefault("channel_mode", "shorts")
    profile.setdefault("last_status", "Idle")
    return profile


def normalize_channel_mode(channel_mode):
    clean = (channel_mode or "shorts").strip().lower()
    if clean not in VALID_CHANNEL_MODES:
        raise ValueError("channel_mode must be 'shorts' or 'videos'")
    return clean
```

Update `load_profiles` to run defaults:

```python
return [ensure_profile_defaults(profile) for profile in data] if isinstance(data, list) else []
```

Update `create_chrome_profiles` created dict with:

```python
"channel_url": "",
"channel_mode": "shorts",
"last_status": "Idle",
```

Add functions:

```python
def update_profile_channel(data_path, profile_id, channel_url, channel_mode):
    profiles = load_profiles(data_path)
    changed = False
    clean_mode = normalize_channel_mode(channel_mode)
    clean_url = (channel_url or "").strip()

    for profile in profiles:
        if profile.get("id") == profile_id:
            profile["channel_url"] = clean_url
            profile["channel_mode"] = clean_mode
            changed = True
            break

    if changed:
        save_profiles(data_path, profiles)
    return changed


def update_profile_status(data_path, profile_id, status):
    profiles = load_profiles(data_path)
    changed = False
    for profile in profiles:
        if profile.get("id") == profile_id:
            profile["last_status"] = status or "Idle"
            changed = True
            break
    if changed:
        save_profiles(data_path, profiles)
    return changed


def get_assigned_profiles(data_path):
    return [
        profile for profile in load_profiles(data_path)
        if (profile.get("channel_url") or "").strip()
    ]
```

- [ ] **Step 4: Run profile tests**

Run:

```powershell
python -m unittest tests.test_chrome_profiles tests.test_profile_channels -v
```

Expected: all PASS.

## Task 3: SQLite Database Layer

**Files:**
- Create: `app_database.py`
- Test: `tests/test_app_database.py`

- [ ] **Step 1: Write failing database tests**

Create `tests/test_app_database.py`:

```python
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

            job_id = db.create_job("p1", "aaaaaaaaaaa", "https://www.youtube.com/watch?v=aaaaaaaaaaa", "https://www.youtube.com/@hoangacc/videos")
            db.write_log("INFO", "p1", job_id, "download started")
            db.finish_job(job_id, "uploaded", 12.5, "")

            logs = db.get_recent_logs(limit=10)
            self.assertEqual(logs[0]["message"], "download started")
            self.assertEqual(db.get_job(job_id)["status"], "uploaded")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_app_database -v
```

Expected: FAIL because `app_database.py` does not exist.

- [ ] **Step 3: Implement database layer**

Create `app_database.py` with these public methods:

```python
import sqlite3
from datetime import datetime
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
    "download_dir": "downloads",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "upload_latest_on_first_scan": "1",
}


class AppDatabase:
    def __init__(self, db_path):
        self.db_path = Path(db_path)

    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.executemany(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                DEFAULT_SETTINGS.items(),
            )

    def get_setting(self, key, default=""):
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def upsert_videos(self, profile_id, channel_url, channel_mode, videos):
        now = datetime.now().isoformat(timespec="seconds")
        inserted = 0
        with self.connect() as connection:
            for video in videos:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO videos(profile_id, channel_url, channel_mode, video_id, video_url, first_seen_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (profile_id, channel_url, channel_mode, video["video_id"], video["video_url"], now),
                )
                inserted += cursor.rowcount
        return inserted

    def get_newest_unprocessed_video(self, profile_id):
        with self.connect() as connection:
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
        with self.connect() as connection:
            connection.execute(
                "UPDATE videos SET status = ?, downloaded_path = COALESCE(NULLIF(?, ''), downloaded_path) WHERE id = ?",
                (status, downloaded_path, video_id),
            )

    def create_job(self, profile_id, video_id, video_url, channel_url):
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO upload_jobs(profile_id, video_id, video_url, channel_url, status, started_at)
                VALUES(?, ?, ?, ?, 'running', ?)
                """,
                (profile_id, video_id, video_url, channel_url, now),
            )
            return cursor.lastrowid

    def finish_job(self, job_id, status, elapsed_seconds, error=""):
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE upload_jobs
                SET status = ?, finished_at = ?, elapsed_seconds = ?, error = ?
                WHERE id = ?
                """,
                (status, now, float(elapsed_seconds), error or "", job_id),
            )

    def get_job(self, job_id):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM upload_jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def write_log(self, level, profile_id, job_id, message):
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO app_logs(created_at, level, profile_id, job_id, message) VALUES(?, ?, ?, ?, ?)",
                (now, level, profile_id or "", job_id, message),
            )

    def get_recent_logs(self, limit=200):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM app_logs ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 4: Run database tests**

Run:

```powershell
python -m unittest tests.test_app_database -v
```

Expected: all PASS.

## Task 4: YouTube Scanner

**Files:**
- Create: `youtube_scanner.py`
- Create: `tests/fixtures/youtube_shorts.html`
- Create: `tests/fixtures/youtube_videos.html`
- Test: `tests/test_youtube_scanner.py`

- [ ] **Step 1: Add HTML fixtures**

Create `tests/fixtures/youtube_shorts.html`:

```html
<html><body>
<a href="/shorts/aaaaaaaaaaa">Short A</a>
<a href="/shorts/bbbbbbbbbbb">Short B</a>
<script>{"videoId":"ccccccccccc"}</script>
</body></html>
```

Create `tests/fixtures/youtube_videos.html`:

```html
<html><body>
<a href="/watch?v=ddddddddddd">Video D</a>
<a href="/watch?v=eeeeeeeeeee&amp;list=PL1">Video E</a>
<a href="/shorts/fffffffffff">Short F</a>
</body></html>
```

- [ ] **Step 2: Write failing scanner tests**

Create `tests/test_youtube_scanner.py`:

```python
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from youtube_scanner import YouTubeScanner, parse_video_links


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class YouTubeScannerTest(unittest.TestCase):
    def test_parse_shorts_links_preserves_first_seen_order(self):
        html = (FIXTURES / "youtube_shorts.html").read_text(encoding="utf-8")

        videos = parse_video_links(html, "shorts")

        self.assertEqual(
            videos,
            [
                {"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"},
                {"video_id": "bbbbbbbbbbb", "video_url": "https://www.youtube.com/shorts/bbbbbbbbbbb"},
            ],
        )

    def test_parse_videos_links_ignores_shorts(self):
        html = (FIXTURES / "youtube_videos.html").read_text(encoding="utf-8")

        videos = parse_video_links(html, "videos")

        self.assertEqual(
            videos,
            [
                {"video_id": "ddddddddddd", "video_url": "https://www.youtube.com/watch?v=ddddddddddd"},
                {"video_id": "eeeeeeeeeee", "video_url": "https://www.youtube.com/watch?v=eeeeeeeeeee"},
            ],
        )

    @patch("youtube_scanner.requests.get")
    def test_scan_uses_get_and_timeout(self, mock_get):
        response = Mock()
        response.text = (FIXTURES / "youtube_shorts.html").read_text(encoding="utf-8")
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        scanner = YouTubeScanner(timeout=15)
        videos = scanner.scan("https://www.youtube.com/@hoangacc/shorts", "shorts")

        self.assertEqual(videos[0]["video_id"], "aaaaaaaaaaa")
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 15)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run failing tests**

Run:

```powershell
python -m unittest tests.test_youtube_scanner -v
```

Expected: FAIL because `youtube_scanner.py` does not exist.

- [ ] **Step 4: Implement scanner**

Create `youtube_scanner.py`:

```python
import html
import re

import requests


VIDEO_ID_RE = r"[A-Za-z0-9_-]{11}"
SHORTS_RE = re.compile(r'href="\/shorts\/(' + VIDEO_ID_RE + r')"')
VIDEOS_RE = re.compile(r'href="\/watch\?v=(' + VIDEO_ID_RE + r')(?:["&])')


def parse_video_links(page_html, mode):
    clean_mode = (mode or "shorts").strip().lower()
    if clean_mode not in {"shorts", "videos"}:
        raise ValueError("mode must be 'shorts' or 'videos'")

    decoded = html.unescape(page_html or "")
    pattern = SHORTS_RE if clean_mode == "shorts" else VIDEOS_RE
    seen = set()
    videos = []

    for match in pattern.finditer(decoded):
        video_id = match.group(1)
        if video_id in seen:
            continue
        seen.add(video_id)
        if clean_mode == "shorts":
            video_url = f"https://www.youtube.com/shorts/{video_id}"
        else:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append({"video_id": video_id, "video_url": video_url})

    return videos


class YouTubeScanner:
    def __init__(self, timeout=20):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }

    def scan(self, channel_url, mode):
        response = requests.get(channel_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return parse_video_links(response.text, mode)
```

- [ ] **Step 5: Run scanner tests**

Run:

```powershell
python -m unittest tests.test_youtube_scanner -v
```

Expected: all PASS.

## Task 5: Video Downloader

**Files:**
- Create: `video_downloader.py`
- Test: `tests/test_video_downloader.py`

- [ ] **Step 1: Write failing downloader tests**

Create `tests/test_video_downloader.py`:

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from video_downloader import VideoDownloader


class VideoDownloaderTest(unittest.TestCase):
    @patch("video_downloader.yt_dlp.YoutubeDL")
    def test_download_uses_video_id_folder_and_returns_path(self, youtube_dl):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "aaaaaaaaaaa" / "aaaaaaaaaaa.mp4"
            output_file.parent.mkdir(parents=True)
            output_file.write_bytes(b"video")

            instance = Mock()
            instance.__enter__ = Mock(return_value=instance)
            instance.__exit__ = Mock(return_value=None)
            instance.extract_info.return_value = {"id": "aaaaaaaaaaa", "ext": "mp4"}
            instance.prepare_filename.return_value = str(output_file)
            youtube_dl.return_value = instance

            result = VideoDownloader(Path(tmp)).download("https://www.youtube.com/watch?v=aaaaaaaaaaa")

            self.assertEqual(result["video_id"], "aaaaaaaaaaa")
            self.assertEqual(result["file_path"], str(output_file))
            instance.extract_info.assert_called_once_with("https://www.youtube.com/watch?v=aaaaaaaaaaa", download=True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_video_downloader -v
```

Expected: FAIL because `video_downloader.py` does not exist.

- [ ] **Step 3: Implement downloader**

Create `video_downloader.py`:

```python
from pathlib import Path

import yt_dlp


class VideoDownloader:
    def __init__(self, download_dir):
        self.download_dir = Path(download_dir)

    def download(self, video_url):
        self.download_dir.mkdir(parents=True, exist_ok=True)
        options = {
            "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(self.download_dir / "%(id)s" / "%(id)s.%(ext)s"),
        }

        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(video_url, download=True)
            file_path = Path(downloader.prepare_filename(info))
            if file_path.suffix.lower() != ".mp4":
                merged_path = file_path.with_suffix(".mp4")
                if merged_path.exists():
                    file_path = merged_path

        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        return {
            "video_id": info.get("id", ""),
            "title": info.get("title", ""),
            "file_path": str(file_path),
        }
```

- [ ] **Step 4: Run downloader tests**

Run:

```powershell
python -m unittest tests.test_video_downloader -v
```

Expected: all PASS.

## Task 6: Telegram Reporter

**Files:**
- Create: `telegram_reporter.py`
- Test: `tests/test_telegram_reporter.py`

- [ ] **Step 1: Write failing reporter tests**

Create `tests/test_telegram_reporter.py`:

```python
import unittest
from unittest.mock import Mock, patch

from telegram_reporter import TelegramReporter


class TelegramReporterTest(unittest.TestCase):
    def test_disabled_reporter_skips_network(self):
        reporter = TelegramReporter(bot_token="", chat_id="")
        self.assertFalse(reporter.enabled)
        self.assertEqual(reporter.send_text("hello"), {"sent": False, "reason": "disabled"})

    @patch("telegram_reporter.requests.post")
    def test_send_text_posts_to_telegram_api(self, mock_post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}
        mock_post.return_value = response

        result = TelegramReporter("TOKEN", "123").send_text("done")

        self.assertEqual(result, {"sent": True, "response": {"ok": True}})
        self.assertEqual(mock_post.call_args.args[0], "https://api.telegram.org/botTOKEN/sendMessage")
        self.assertEqual(mock_post.call_args.kwargs["json"]["chat_id"], "123")

    @patch("telegram_reporter.requests.post")
    def test_send_job_report_includes_required_details(self, mock_post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}
        mock_post.return_value = response

        TelegramReporter("TOKEN", "123").send_job_report(
            profile_name="Acc1",
            channel_url="https://www.youtube.com/@hoangacc/shorts",
            video_url="https://www.youtube.com/shorts/aaaaaaaaaaa",
            status="uploaded",
            elapsed_seconds=11.2,
            detail="file=downloads/aaaaaaaaaaa.mp4",
        )

        text = mock_post.call_args.kwargs["json"]["text"]
        self.assertIn("Acc1", text)
        self.assertIn("https://www.youtube.com/@hoangacc/shorts", text)
        self.assertIn("11.2", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
python -m unittest tests.test_telegram_reporter -v
```

Expected: FAIL because `telegram_reporter.py` does not exist.

- [ ] **Step 3: Implement reporter**

Create `telegram_reporter.py`:

```python
import requests


class TelegramReporter:
    def __init__(self, bot_token, chat_id, timeout=20):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self.timeout = timeout

    @property
    def enabled(self):
        return bool(self.bot_token and self.chat_id)

    def send_text(self, text):
        if not self.enabled:
            return {"sent": False, "reason": "disabled"}

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": self.chat_id, "text": text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return {"sent": True, "response": response.json()}

    def send_job_report(self, profile_name, channel_url, video_url, status, elapsed_seconds, detail=""):
        message = "\n".join([
            f"Profile: {profile_name}",
            f"Status: {status}",
            f"YouTube channel: {channel_url}",
            f"YouTube video: {video_url}",
            f"Elapsed seconds: {elapsed_seconds:.1f}",
            f"Detail: {detail}",
        ])
        return self.send_text(message)
```

- [ ] **Step 4: Run reporter tests**

Run:

```powershell
python -m unittest tests.test_telegram_reporter -v
```

Expected: all PASS.

## Task 7: TikTok Uploader Using `remote_browser`

**Files:**
- Create: `tiktok_uploader.py`
- Test: `tests/test_tiktok_uploader.py`

- [ ] **Step 1: Write failing uploader tests with fake browser**

Create `tests/test_tiktok_uploader.py`:

```python
import tempfile
import unittest
from pathlib import Path

from tiktok_uploader import TikTokUploader


class FakeElement:
    def __init__(self):
        self.sent_file = ""
        self.clicked = False

    def send_file(self, file_path):
        self.sent_file = file_path

    def click(self):
        self.clicked = True


class FakeRemote:
    def __init__(self):
        self.urls = []
        self.file_input = FakeElement()
        self.post_button = FakeElement()

    def get(self, url, wait_load=False):
        self.urls.append(url)

    def find_element(self, by, value, timeout=None):
        if value == 'input[type="file"]':
            return self.file_input
        return None

    def execute_script(self, script, *args, **kwargs):
        if "querySelectorAll('button')" in script:
            return self.post_button
        if "document.body.innerText" in script:
            return "Upload complete"
        return None

    def sleep(self, timeout):
        return None


class FakeChromeProfileBrowser:
    def __init__(self, profile_path, width=1100, height=800):
        self.browser = FakeRemote()

    def open(self, url):
        self.browser.get(url, wait_load=False)
        return self

    def close(self):
        return None


class TikTokUploaderTest(unittest.TestCase):
    def test_upload_sends_file_and_clicks_post_button(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            result = uploader.upload(profile_path=tmp, video_path=video)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(wrapper.browser.file_input.sent_file, str(video))
            self.assertTrue(wrapper.browser.post_button.clicked)

    def test_upload_rejects_missing_file(self):
        uploader = TikTokUploader(browser_factory=FakeChromeProfileBrowser, wait_seconds=0)
        with self.assertRaises(FileNotFoundError):
            uploader.upload(profile_path="profile", video_path="missing.mp4")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
python -m unittest tests.test_tiktok_uploader -v
```

Expected: FAIL because `tiktok_uploader.py` does not exist.

- [ ] **Step 3: Implement uploader without Selenium**

Create `tiktok_uploader.py`:

```python
import time
from pathlib import Path

from app_paths import TIKTOK_UPLOAD_URL
from Controller.BrowserController import ChromeProfileBrowser
from remote_browser.type.browser_support import By


POST_BUTTON_SCRIPT = """
return Array.from(document.querySelectorAll('button')).find((button) => {
    const text = (button.innerText || button.textContent || '')
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .toLowerCase();
    const enabled = !button.disabled && button.getAttribute('aria-disabled') !== 'true';
    return enabled && (
        text.includes('post') ||
        text.includes('upload') ||
        text.includes('publish') ||
        text.includes('dang')
    );
});
"""


class TikTokUploader:
    def __init__(self, browser_factory=ChromeProfileBrowser, upload_url=TIKTOK_UPLOAD_URL, wait_seconds=2):
        self.browser_factory = browser_factory
        self.upload_url = upload_url
        self.wait_seconds = wait_seconds

    def upload(self, profile_path, video_path, timeout=180):
        file_path = Path(video_path)
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        wrapper = self.browser_factory(profile_path)
        wrapper.open(self.upload_url)
        browser = wrapper.browser

        file_input = browser.find_element(By.CSS_SELECTOR, 'input[type="file"]', timeout=30)
        if not file_input:
            raise RuntimeError("TikTok upload input not found. Profile may not be logged in.")

        file_input.send_file(str(file_path))
        self._wait_after_file(browser, timeout)

        post_button = self._find_post_button(browser, timeout)
        if not post_button:
            raise RuntimeError("TikTok post button not found or disabled.")

        post_button.click()
        self._wait_until_finished(browser, timeout)
        return {"status": "uploaded", "file_path": str(file_path)}

    def _wait_after_file(self, browser, timeout):
        end_at = time.time() + timeout
        while time.time() < end_at:
            body_text = browser.execute_script("return document.body.innerText || ''") or ""
            lowered = body_text.lower()
            if "upload complete" in lowered or "post" in lowered or "publish" in lowered or "dang" in lowered:
                return
            browser.sleep(self.wait_seconds)
        raise TimeoutError("TikTok upload did not become ready before timeout.")

    def _find_post_button(self, browser, timeout):
        end_at = time.time() + timeout
        while time.time() < end_at:
            button = browser.execute_script(POST_BUTTON_SCRIPT)
            if button:
                return button
            browser.sleep(self.wait_seconds)
        return None

    def _wait_until_finished(self, browser, timeout):
        end_at = time.time() + timeout
        while time.time() < end_at:
            body_text = browser.execute_script("return document.body.innerText || ''") or ""
            lowered = body_text.lower()
            if "uploaded" in lowered or "published" in lowered or "video has been posted" in lowered:
                return
            browser.sleep(self.wait_seconds)
        return
```

- [ ] **Step 4: Run uploader tests and Selenium ban**

Run:

```powershell
python -m unittest tests.test_tiktok_uploader tests.test_no_selenium -v
```

Expected: all PASS, no Selenium/chromedriver reference.

## Task 8: Upload Worker Orchestration

**Files:**
- Create: `upload_worker.py`
- Test: `tests/test_upload_worker.py`

- [ ] **Step 1: Write failing worker tests with fakes**

Create `tests/test_upload_worker.py`:

```python
import tempfile
import unittest
from pathlib import Path

from app_database import AppDatabase
from upload_worker import UploadWorkerCore


class FakeScanner:
    def scan(self, channel_url, mode):
        return [{"video_id": "aaaaaaaaaaa", "video_url": "https://www.youtube.com/shorts/aaaaaaaaaaa"}]


class FakeDownloader:
    def __init__(self, tmp):
        self.tmp = Path(tmp)

    def download(self, video_url):
        file_path = self.tmp / "aaaaaaaaaaa.mp4"
        file_path.write_bytes(b"video")
        return {"video_id": "aaaaaaaaaaa", "title": "Video A", "file_path": str(file_path)}


class FakeUploader:
    def upload(self, profile_path, video_path):
        return {"status": "uploaded", "file_path": str(video_path)}


class FakeReporter:
    def __init__(self):
        self.reports = []

    def send_job_report(self, **kwargs):
        self.reports.append(kwargs)
        return {"sent": True}


class UploadWorkerCoreTest(unittest.TestCase):
    def test_process_profile_scans_downloads_uploads_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            reporter = FakeReporter()
            core = UploadWorkerCore(
                database=db,
                scanner=FakeScanner(),
                downloader=FakeDownloader(tmp),
                uploader=FakeUploader(),
                reporter=reporter,
            )
            profile = {
                "id": "p1",
                "name": "Acc1",
                "profile_path": str(Path(tmp) / "profile"),
                "channel_url": "https://www.youtube.com/@hoangacc/shorts",
                "channel_mode": "shorts",
            }

            result = core.process_profile(profile)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(db.get_newest_unprocessed_video("p1"), None)
            self.assertEqual(len(reporter.reports), 1)
            self.assertIn("aaaaaaaaaaa", reporter.reports[0]["video_url"])

    def test_process_profile_skips_missing_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AppDatabase(Path(tmp) / "app.db")
            db.initialize()
            core = UploadWorkerCore(db, FakeScanner(), FakeDownloader(tmp), FakeUploader(), FakeReporter())

            result = core.process_profile({"id": "p1", "name": "Acc1", "profile_path": tmp})

            self.assertEqual(result["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_upload_worker -v
```

Expected: FAIL because `upload_worker.py` does not exist.

- [ ] **Step 3: Implement worker core and PyQt wrapper**

Create `upload_worker.py`:

```python
import time

from PyQt6 import QtCore

from app_database import AppDatabase
from app_paths import APP_DB_PATH, DOWNLOADS_DIR, PROFILES_PATH
from profile_store import get_assigned_profiles, update_profile_status
from telegram_reporter import TelegramReporter
from tiktok_uploader import TikTokUploader
from video_downloader import VideoDownloader
from youtube_scanner import YouTubeScanner


class UploadWorkerCore:
    def __init__(self, database, scanner, downloader, uploader, reporter):
        self.database = database
        self.scanner = scanner
        self.downloader = downloader
        self.uploader = uploader
        self.reporter = reporter

    def process_profile(self, profile):
        profile_id = profile.get("id", "")
        profile_name = profile.get("name", "")
        channel_url = (profile.get("channel_url") or "").strip()
        channel_mode = (profile.get("channel_mode") or "shorts").strip().lower()
        if not channel_url:
            self.database.write_log("WARN", profile_id, None, f"{profile_name}: missing YouTube channel URL")
            return {"status": "skipped", "reason": "missing_channel_url"}

        start = time.time()
        job_id = None
        try:
            self.database.write_log("INFO", profile_id, None, f"{profile_name}: scanning {channel_url}")
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
            upload_result = self.uploader.upload(profile.get("profile_path", ""), downloaded["file_path"])

            elapsed = time.time() - start
            self.database.update_video_status(video["id"], "uploaded", downloaded["file_path"])
            self.database.finish_job(job_id, "uploaded", elapsed)
            self.database.write_log("INFO", profile_id, job_id, f"{profile_name}: uploaded {video['video_url']}")
            self.reporter.send_job_report(
                profile_name=profile_name,
                channel_url=channel_url,
                video_url=video["video_url"],
                status="uploaded",
                elapsed_seconds=elapsed,
                detail=f"file={downloaded['file_path']}",
            )
            return {"status": "uploaded", "video_url": video["video_url"], "upload": upload_result}
        except Exception as error:
            elapsed = time.time() - start
            if job_id:
                self.database.finish_job(job_id, "failed", elapsed, str(error))
            self.database.write_log("ERROR", profile_id, job_id, f"{profile_name}: {error}")
            self.reporter.send_job_report(
                profile_name=profile_name,
                channel_url=channel_url,
                video_url="",
                status="failed",
                elapsed_seconds=elapsed,
                detail=str(error),
            )
            return {"status": "failed", "error": str(error)}


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
        poll_interval = max(10, int(self.database.get_setting("poll_interval_seconds", "10")))
        download_dir = self.database.get_setting("download_dir", str(DOWNLOADS_DIR))
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
```

- [ ] **Step 4: Run worker tests**

Run:

```powershell
python -m unittest tests.test_upload_worker -v
```

Expected: all PASS.

## Task 9: GUI Tabs, Channel Assignment, Run/Stop, Logs

**Files:**
- Modify: `gui.py`
- Test: `tests/test_gui_smoke.py`
- Test: `tests/test_profile_channels.py`

- [ ] **Step 1: Write GUI smoke test**

Create `tests/test_gui_smoke.py`:

```python
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets

from gui import Ui_MainWindow


class GuiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_window_has_required_tabs_and_run_controls(self):
        window = Ui_MainWindow()

        tab_names = [window.tabs.tabText(index) for index in range(window.tabs.count())]

        self.assertIn("Profiles", tab_names)
        self.assertIn("Settings", tab_names)
        self.assertIn("Logs", tab_names)
        self.assertEqual(window.button_run_all.text(), "Run")
        self.assertEqual(window.button_stop.text(), "Stop")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing GUI smoke test**

Run:

```powershell
$env:QT_QPA_PLATFORM="offscreen"; python -m unittest tests.test_gui_smoke -v
```

Expected: FAIL because current GUI has no `tabs`, `button_run_all`, or `button_stop`.

- [ ] **Step 3: Refactor GUI layout**

Modify `gui.py`:

```python
self.tabs = QtWidgets.QTabWidget(parent=self.centralwidget)
self.main_layout.addWidget(self.tabs)

self.profiles_tab = QtWidgets.QWidget()
self.settings_tab = QtWidgets.QWidget()
self.logs_tab = QtWidgets.QWidget()
self.tabs.addTab(self.profiles_tab, "Profiles")
self.tabs.addTab(self.settings_tab, "Settings")
self.tabs.addTab(self.logs_tab, "Logs")
```

Move existing create panel and profile table into `profiles_tab`.

Add run controls above profile table:

```python
self.button_run_all = QtWidgets.QPushButton("Run", parent=self.profiles_tab)
self.button_stop = QtWidgets.QPushButton("Stop", parent=self.profiles_tab)
self.button_stop.setEnabled(False)
```

Change profile table columns to:

```python
[
    "Name",
    "Note",
    "Group",
    "Channel URL",
    "Mode",
    "Status",
    "Open",
    "Save",
    "Delete",
]
```

For each row, render:

```python
channel_input = QtWidgets.QLineEdit(parent=self.table)
channel_input.setText(profile.get("channel_url", ""))
mode_combo = QtWidgets.QComboBox(parent=self.table)
mode_combo.addItems(["shorts", "videos"])
mode_combo.setCurrentText(profile.get("channel_mode", "shorts"))
save_button = QtWidgets.QPushButton("Save", parent=self.table)
save_button.clicked.connect(lambda _, p=profile, url=channel_input, mode=mode_combo: self.save_channel(p, url.text(), mode.currentText()))
```

Add settings tab controls:

```python
self.input_poll_interval = QtWidgets.QSpinBox(parent=self.settings_tab)
self.input_poll_interval.setRange(10, 3600)
self.input_poll_interval.setValue(10)
self.input_download_dir = QtWidgets.QLineEdit(parent=self.settings_tab)
self.input_telegram_token = QtWidgets.QLineEdit(parent=self.settings_tab)
self.input_telegram_chat_id = QtWidgets.QLineEdit(parent=self.settings_tab)
self.button_save_settings = QtWidgets.QPushButton("Save Settings", parent=self.settings_tab)
```

Add logs table:

```python
self.logs_table = QtWidgets.QTableWidget(parent=self.logs_tab)
self.logs_table.setColumnCount(5)
self.logs_table.setHorizontalHeaderLabels(["Time", "Level", "Profile", "Job", "Message"])
self.button_refresh_logs = QtWidgets.QPushButton("Refresh Logs", parent=self.logs_tab)
```

- [ ] **Step 4: Wire GUI to profile store and database**

Add imports:

```python
from app_database import AppDatabase
from app_paths import APP_DB_PATH, DOWNLOADS_DIR, PROFILES_PATH
from profile_store import update_profile_channel
from upload_worker import YoutubeToTikTokWorker
```

In `__init__`:

```python
self.database = AppDatabase(APP_DB_PATH)
self.database.initialize()
self.worker_thread = None
self.worker = None
```

Add methods:

```python
def save_channel(self, profile, channel_url, channel_mode):
    update_profile_channel(PROFILES_PATH, profile.get("id"), channel_url, channel_mode)
    self.reload_profiles()
    self.statusbar.showMessage("Saved channel assignment", 3000)

def load_settings(self):
    self.input_poll_interval.setValue(int(self.database.get_setting("poll_interval_seconds", "10")))
    self.input_download_dir.setText(self.database.get_setting("download_dir", str(DOWNLOADS_DIR)))
    self.input_telegram_token.setText(self.database.get_setting("telegram_bot_token", ""))
    self.input_telegram_chat_id.setText(self.database.get_setting("telegram_chat_id", ""))

def save_settings(self):
    self.database.set_setting("poll_interval_seconds", self.input_poll_interval.value())
    self.database.set_setting("download_dir", self.input_download_dir.text() or str(DOWNLOADS_DIR))
    self.database.set_setting("telegram_bot_token", self.input_telegram_token.text())
    self.database.set_setting("telegram_chat_id", self.input_telegram_chat_id.text())
    self.statusbar.showMessage("Saved settings", 3000)

def refresh_logs(self):
    logs = self.database.get_recent_logs(limit=200)
    self.logs_table.setRowCount(len(logs))
    for row, log in enumerate(logs):
        values = [log["created_at"], log["level"], log["profile_id"], log["job_id"] or "", log["message"]]
        for col, value in enumerate(values):
            self.logs_table.setItem(row, col, QtWidgets.QTableWidgetItem(str(value)))
```

- [ ] **Step 5: Add Run/Stop worker wiring**

Add methods:

```python
def run_all_profiles(self):
    if self.worker_thread:
        return
    self.save_settings()
    self.worker_thread = QtCore.QThread(self)
    self.worker = YoutubeToTikTokWorker(PROFILES_PATH, APP_DB_PATH)
    self.worker.moveToThread(self.worker_thread)
    self.worker_thread.started.connect(self.worker.run_forever)
    self.worker.log_created.connect(self.refresh_logs)
    self.worker.finished.connect(self.worker_thread.quit)
    self.worker.finished.connect(self.worker.deleteLater)
    self.worker_thread.finished.connect(self.worker_thread.deleteLater)
    self.worker_thread.finished.connect(self.worker_finished)
    self.worker_thread.start()
    self.button_run_all.setEnabled(False)
    self.button_stop.setEnabled(True)
    self.statusbar.showMessage("Worker running", 3000)

def stop_worker(self):
    if self.worker:
        self.worker.stop()
    self.button_stop.setEnabled(False)
    self.statusbar.showMessage("Stopping worker", 3000)

def worker_finished(self):
    self.worker_thread = None
    self.worker = None
    self.button_run_all.setEnabled(True)
    self.button_stop.setEnabled(False)
    self.reload_profiles()
    self.refresh_logs()
    self.statusbar.showMessage("Worker stopped", 3000)
```

Connect buttons:

```python
self.button_run_all.clicked.connect(self.run_all_profiles)
self.button_stop.clicked.connect(self.stop_worker)
self.button_save_settings.clicked.connect(self.save_settings)
self.button_refresh_logs.clicked.connect(self.refresh_logs)
```

- [ ] **Step 6: Run GUI and profile tests**

Run:

```powershell
$env:QT_QPA_PLATFORM="offscreen"; python -m unittest tests.test_gui_smoke tests.test_profile_channels -v
```

Expected: all PASS.

## Task 10: End-To-End Test Batch And Manual Verification

**Files:**
- Modify: `readme.md`

- [ ] **Step 1: Add usage notes to `readme.md`**

Append:

```markdown
## YouTube To TikTok Upload Flow

1. Run `python gui.py`.
2. Create Chrome profiles.
3. Open each profile and log in to TikTok manually.
4. Assign one YouTube channel URL to each profile.
5. Choose mode `shorts` or `videos`.
6. Set poll interval, download folder, and Telegram bot settings.
7. Press `Run`.
8. Watch `Logs` tab for scan, download, upload, and Telegram report status.

The app uses Chrome through `remote_browser`. It does not use Selenium, chromedriver, GoLogin, or GPM Login in this stage.
```

- [ ] **Step 2: Run complete automated test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 3: Compile source files**

Run:

```powershell
python -m py_compile app_paths.py profile_store.py app_database.py youtube_scanner.py video_downloader.py telegram_reporter.py tiktok_uploader.py upload_worker.py gui.py main.py Controller\BrowserController.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Verify no Selenium/chromedriver/GoLogin**

Run:

```powershell
rg -n "selenium|seleniumwire|webdriver|chromedriver|Gologin|GoLogin" . --glob "!remote_browser/**" --glob "!profiles/**" --glob "!__pycache__/**" --glob "!docs/**"
```

Expected: no source hits. If `requirements.txt` or docs contain historical text, remove only stale source references that can affect runtime.

- [ ] **Step 5: GUI smoke run**

Run:

```powershell
python gui.py
```

Expected:
- Window opens.
- Profiles tab shows table.
- Settings tab saves interval, download folder, Telegram fields.
- Logs tab refreshes without error.
- Run button starts worker; Stop button requests stop.

- [ ] **Step 6: Real manual upload verification**

Use one Chrome profile that is already logged in to TikTok:

```text
Profile channel URL: https://www.youtube.com/@hoangacc/shorts
Mode: shorts
Poll interval: 10
Upload URL opened by app: https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video
```

Expected:
- Scanner logs at least one discovered video.
- `downloads/<video_id>/<video_id>.mp4` exists.
- Chrome profile opens TikTok Studio.
- File input receives downloaded MP4 through `remote_browser` CDP.
- Post button is clicked after upload becomes ready.
- `data/app.db` has `videos.status = 'uploaded'`.
- Logs tab shows scan, download, upload, Telegram status.
- Telegram message includes profile name, YouTube channel URL, YouTube video URL, status, elapsed seconds, and file path.

## Failure Handling Rules

- Missing YouTube channel URL: log `WARN`, skip profile, keep worker alive.
- Invalid channel mode: profile save raises clear error and does not corrupt `profiles.json`.
- YouTube GET failure: log `ERROR`, mark job failed only if a job already exists.
- No new video: log count and skip download/upload.
- Download failure: mark video `failed`, finish job `failed`, send Telegram failure report.
- TikTok profile not logged in: `tiktok_uploader.py` raises `TikTok upload input not found. Profile may not be logged in.`, job becomes `failed`.
- Telegram failure: write log error but do not change upload success to failed, because upload already completed.
- Stop button: finish current profile step, then exit loop before next profile or next poll cycle.

## Scope Boundaries

- This plan implements Chrome only.
- GPM Login is not included in this plan.
- GoLogin is not included.
- Selenium and chromedriver remain removed.
- The app assumes the user has rights to download and re-upload the videos being processed.

## Final Verification Command Set

```powershell
python -m unittest discover -s tests -v
python -m py_compile app_paths.py profile_store.py app_database.py youtube_scanner.py video_downloader.py telegram_reporter.py tiktok_uploader.py upload_worker.py gui.py main.py Controller\BrowserController.py
rg -n "selenium|seleniumwire|webdriver|chromedriver|Gologin|GoLogin" . --glob "!remote_browser/**" --glob "!profiles/**" --glob "!__pycache__/**" --glob "!docs/**"
```

Expected:
- Unit tests PASS.
- Compile command exits 0.
- Search returns no runtime source hits.
