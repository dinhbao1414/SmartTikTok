from pathlib import Path

import yt_dlp


class VideoDownloader:
    def __init__(self, download_dir):
        self.download_dir = Path(download_dir)

    def download(self, video_url):
        self.download_dir.mkdir(parents=True, exist_ok=True)
        options = {
            "format": "b[ext=mp4][vcodec!=none][acodec!=none]/b[vcodec!=none][acodec!=none]",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(self.download_dir / "%(id)s" / "%(id)s.%(ext)s"),
        }

        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(video_url, download=True)
            file_path = Path(downloader.prepare_filename(info))

        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        return {
            "video_id": info.get("id", ""),
            "title": info.get("title", ""),
            "duration": info.get("duration") or 0,
            "file_path": str(file_path),
        }
