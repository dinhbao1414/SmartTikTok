import subprocess
import unittest
from unittest.mock import Mock, patch

from remote_browser.launcher import LaunchBrowser


class RemoteBrowserLauncherTest(unittest.TestCase):
    def test_start_browser_quotes_browser_path_and_hides_console_window(self):
        class FakeOptions:
            binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

            def to_command_args(self):
                return r'--remote-debugging-port=9222 --user-data-dir="C:\Profiles\Acc 1"'

        launcher = LaunchBrowser.__new__(LaunchBrowser)
        launcher._options = FakeOptions()
        launcher._LaunchBrowser__list_pid = set()

        process = Mock()
        process.pid = 1234
        with patch("remote_browser.launcher.subprocess.Popen", return_value=process) as mock_popen:
            launcher._LaunchBrowser__start_browser(["--flag=value"])

        command = mock_popen.call_args.args[0]
        self.assertTrue(command.startswith('"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '))
        self.assertIn('--user-data-dir="C:\\Profiles\\Acc 1"', command)
        self.assertIn("--flag=value", command)
        self.assertEqual(
            mock_popen.call_args.kwargs["creationflags"],
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(launcher._pid, 1234)


if __name__ == "__main__":
    unittest.main()
