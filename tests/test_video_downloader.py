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
            instance.extract_info.return_value = {"id": "aaaaaaaaaaa", "ext": "mp4", "duration": 615}
            instance.prepare_filename.return_value = str(output_file)
            youtube_dl.return_value = instance

            result = VideoDownloader(Path(tmp)).download("https://www.youtube.com/watch?v=aaaaaaaaaaa")

            self.assertEqual(result["video_id"], "aaaaaaaaaaa")
            self.assertEqual(result["file_path"], str(output_file))
            self.assertEqual(result["duration"], 615)
            options = youtube_dl.call_args.args[0]
            self.assertNotIn("+", options["format"])
            self.assertNotIn("merge_output_format", options)
            instance.extract_info.assert_called_once_with("https://www.youtube.com/watch?v=aaaaaaaaaaa", download=True)


if __name__ == "__main__":
    unittest.main()
