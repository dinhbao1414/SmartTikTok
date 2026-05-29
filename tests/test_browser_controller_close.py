import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Controller.BrowserController import ChromeProfileBrowser


class FakeBrowser:
    def __init__(self):
        self.quit_called = False

    def quit_browser(self):
        self.quit_called = True


class FakeProcess:
    def __init__(self, profile_path):
        self.info = {
            "pid": 123,
            "name": "chrome.exe",
            "cmdline": ["chrome.exe", f"--user-data-dir={profile_path}"],
        }
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=0):
        raise TimeoutError("still running")

    def kill(self):
        self.killed = True


class BrowserControllerCloseTest(unittest.TestCase):
    def test_close_terminates_chrome_processes_for_profile_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp).resolve()
            fake_browser = FakeBrowser()
            fake_process = FakeProcess(profile_path)
            controller = ChromeProfileBrowser.__new__(ChromeProfileBrowser)
            controller.profile_path = profile_path
            controller.browser = fake_browser

            with patch("Controller.BrowserController.psutil.process_iter", return_value=[fake_process]):
                controller.close()

            self.assertTrue(fake_browser.quit_called)
            self.assertTrue(fake_process.terminated)
            self.assertTrue(fake_process.killed)


if __name__ == "__main__":
    unittest.main()
