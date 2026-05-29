import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
LEGACY_BROWSER = "se" + "lenium"
LEGACY_BROWSER_WIRE = "se" + "leniumwire"
LEGACY_DRIVER_API = "web" + "driver"
LEGACY_CHROME_DRIVER = "chrome" + "driver"
LEGACY_PROFILE_STACK = "Go" + "login"

SOURCE_PATHS = [
    ROOT / "Controller",
    ROOT / "Common",
    ROOT / "CaptchaSolve",
    ROOT / "gui.py",
    ROOT / "main.py",
    ROOT / "requirements.txt",
]


def iter_source_files():
    for path in SOURCE_PATHS:
        if path.is_file():
            yield path
            continue
        for file_path in path.rglob("*"):
            if "__pycache__" in file_path.parts:
                continue
            if file_path.suffix.lower() in {".py", ".txt"}:
                yield file_path


class NoSeleniumTest(unittest.TestCase):
    def test_source_has_no_browser_driver_references(self):
        bad_terms = (LEGACY_BROWSER, LEGACY_BROWSER_WIRE, LEGACY_DRIVER_API, LEGACY_CHROME_DRIVER)
        offenders = []
        for file_path in iter_source_files():
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for term in bad_terms:
                if term in text:
                    offenders.append(f"{file_path.relative_to(ROOT)} contains {term}")

        self.assertEqual(offenders, [])

    def test_browser_driver_folder_removed(self):
        self.assertFalse((ROOT / LEGACY_CHROME_DRIVER).exists())

    def test_no_browser_driver_style_helper_api(self):
        bad_terms = (
            "def do_",
            "driver.switch_to",
            "active_element",
            "class Keys",
            "RemoteSwitchTo",
            "RemoteActiveElement",
        )
        offenders = []
        for file_path in iter_source_files():
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for term in bad_terms:
                if term in text:
                    offenders.append(f"{file_path.relative_to(ROOT)} contains {term}")

        self.assertEqual(offenders, [])

    def test_removed_tiktok_profile_gui_stack(self):
        bad_terms = (LEGACY_PROFILE_STACK, "Thread" + "Tiktok", "Captcha" + "Solve", "Get" + "Mail", "Get" + "Proxy")
        offenders = []
        checked_paths = [
            ROOT / "gui.py",
            ROOT / "Controller",
            ROOT / "Common",
        ]
        for path in checked_paths:
            if path.is_file():
                files = [path]
            else:
                files = [
                    file_path for file_path in path.rglob("*.py")
                    if "__pycache__" not in file_path.parts
                ]
            for file_path in files:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for term in bad_terms:
                    if term in text:
                        offenders.append(f"{file_path.relative_to(ROOT)} contains {term}")

        self.assertEqual(offenders, [])

    def test_main_has_no_removed_registration_imports(self):
        main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore")
        bad_terms = ("Controller.TiktokController", "YoloCaptchaV2", "Thread" + "Tiktok", LEGACY_PROFILE_STACK)
        offenders = [term for term in bad_terms if term in main_text]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
