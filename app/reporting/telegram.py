from html import escape

import requests


class TelegramReporter:
    def __init__(self, bot_token, chat_id, timeout=20):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self.timeout = timeout

    @property
    def enabled(self):
        return bool(self.bot_token and self.chat_id)

    def send_text(self, text, parse_mode=None, disable_web_page_preview=False):
        if not self.enabled:
            return {"sent": False, "reason": "disabled"}

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview:
            payload["disable_web_page_preview"] = True
        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return {"sent": True, "response": response.json()}

    def send_job_report(self, profile_name, channel_url, video_url, status, elapsed_seconds, detail=""):
        status_text = str(status or "unknown")
        status_icon = {
            "uploaded": "✅",
            "failed": "❌",
            "skipped": "⏭️",
        }.get(status_text.lower(), "ℹ️")
        message = "\n".join([
            f"{status_icon} <b>SmartTikTok Report</b>",
            f"<b>Status:</b> {escape(status_text)}",
            f"👤 <b>Profile:</b> {escape(str(profile_name or '-'))}",
            f"🎬 <b>Video:</b> {escape(str(video_url or '-'))}",
            f"🔗 <b>Channel:</b> {escape(str(channel_url or '-'))}",
            f"⏱️ <b>Elapsed:</b> {float(elapsed_seconds or 0):.1f}s",
            "",
            "📄 <b>Detail</b>",
            *self._format_detail_lines(detail),
        ])
        return self.send_text(message, parse_mode="HTML", disable_web_page_preview=True)

    def _format_detail_lines(self, detail):
        if not detail:
            return ["- none"]
        lines = []
        for part in str(detail).split("; "):
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                lines.append(f"- <b>{escape(key.strip())}:</b> {escape(value.strip())}")
            else:
                lines.append(f"- {escape(part.strip())}")
        return lines or ["- none"]
