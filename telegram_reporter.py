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
            f"Total time seconds: {elapsed_seconds:.1f}",
            f"Detail: {detail}",
        ])
        return self.send_text(message)
