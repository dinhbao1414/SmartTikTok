import html
import re
from urllib.parse import urlsplit, urlunsplit

import requests

VIDEO_ID_RE = r"[A-Za-z0-9_-]{11}"
SHORTS_RE = re.compile(r"/shorts/(" + VIDEO_ID_RE + r")")
VIDEOS_RE = re.compile(r"/watch\?v=(" + VIDEO_ID_RE + r")(?:[\"&])")


def normalize_mode(mode):
    clean_mode = (mode or "shorts").strip().lower()
    if clean_mode not in {"shorts", "videos"}:
        raise ValueError("mode must be 'shorts' or 'videos'")
    return clean_mode


def build_channel_tab_url(channel_url, mode):
    clean_mode = normalize_mode(mode)
    clean_url = (channel_url or "").strip()
    if not clean_url:
        return clean_url

    parts = urlsplit(clean_url)
    path = parts.path.rstrip("/")
    if path.endswith("/shorts") or path.endswith("/videos"):
        path = path.rsplit("/", 1)[0]
    path = f"{path}/{clean_mode}" if path else f"/{clean_mode}"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def parse_video_links(page_html, mode):
    clean_mode = normalize_mode(mode)
    decoded = (
        html.unescape(page_html or "")
        .replace("\\/", "/")
        .replace("\\u0026", "&")
        .replace("\\u003d", "=")
    )
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
        scan_url = build_channel_tab_url(channel_url, mode)
        response = requests.get(scan_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return parse_video_links(response.text, mode)
