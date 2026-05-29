from pathlib import Path

import psutil

from remote_browser import LaunchBrowser
from remote_browser.type.browser import Browser as BrowserType


class ChromeProfileBrowser:
    def __init__(self, profile_path, width=1100, height=800):
        self.profile_path = Path(profile_path)
        self.profile_path.mkdir(parents=True, exist_ok=True)
        self.browser = LaunchBrowser(
            browser_type=BrowserType.CHROME,
            property_browser={
                "profile_path": str(self.profile_path),
                "width": width,
                "height": height,
            },
        )

    def open(self, url="https://www.google.com"):
        self.browser.get(url, wait_load=False)
        return self

    def close(self):
        try:
            self.browser.quit_browser()
        finally:
            self._kill_profile_processes()

    def _kill_profile_processes(self):
        profile_path = str(self.profile_path.resolve()).lower()
        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = process.info.get("cmdline") or []
                command_text = " ".join(str(part) for part in cmdline).lower()
                if profile_path not in command_text:
                    continue
                process.terminate()
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    process.kill()
                except TimeoutError:
                    process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
