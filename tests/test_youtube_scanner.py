import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from youtube_scanner import YouTubeScanner, build_channel_tab_url, parse_video_links

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

    def test_parse_shorts_links_from_youtube_json_commands(self):
        page_html = (
            '{"commandMetadata":{"webCommandMetadata":'
            '{"url":"/shorts/EQHRLfqx6u8","webPageType":"WEB_PAGE_TYPE_SHORTS"}},'
            '"reelWatchEndpoint":{"videoId":"EQHRLfqx6u8"}}'
        )

        videos = parse_video_links(page_html, "shorts")

        self.assertEqual(
            videos,
            [{"video_id": "EQHRLfqx6u8", "video_url": "https://www.youtube.com/shorts/EQHRLfqx6u8"}],
        )

    def test_build_channel_tab_url_appends_mode_for_base_channel_url(self):
        self.assertEqual(
            build_channel_tab_url("https://www.youtube.com/channel/UCbKjbwwhzKt6y7ulG62Ugzw/", "shorts"),
            "https://www.youtube.com/channel/UCbKjbwwhzKt6y7ulG62Ugzw/shorts",
        )
        self.assertEqual(
            build_channel_tab_url("https://www.youtube.com/@hoangacc", "videos"),
            "https://www.youtube.com/@hoangacc/videos",
        )

    @patch("youtube_scanner.requests.get")
    def test_scan_uses_get_and_timeout(self, mock_get):
        response = Mock()
        response.text = (FIXTURES / "youtube_shorts.html").read_text(encoding="utf-8")
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        scanner = YouTubeScanner(timeout=15)
        videos = scanner.scan("https://www.youtube.com/@hoangacc", "shorts")

        self.assertEqual(videos[0]["video_id"], "aaaaaaaaaaa")
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.args[0], "https://www.youtube.com/@hoangacc/shorts")
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 15)


if __name__ == "__main__":
    unittest.main()
