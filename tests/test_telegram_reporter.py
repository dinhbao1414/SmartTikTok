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
        self.assertIn("Total time seconds", text)


if __name__ == "__main__":
    unittest.main()
