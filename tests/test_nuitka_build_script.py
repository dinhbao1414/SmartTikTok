import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NuitkaBuildScriptTest(unittest.TestCase):
    def test_build_script_targets_launcher_and_separate_output_folder(self):
        script = (ROOT / "scripts" / "build_nuitka_admin.bat").read_text(encoding="utf-8")

        self.assertIn("Start-Process", script)
        self.assertIn("-Verb RunAs", script)
        self.assertIn("--standalone", script)
        self.assertIn("--enable-plugin=pyqt6", script)
        self.assertIn("--include-package=app", script)
        self.assertIn("--include-package=Controller", script)
        self.assertIn("--include-package=remote_browser", script)
        self.assertIn("--jobs=16", script)
        self.assertIn("--lto=no", script)
        self.assertIn("--nofollow-import-to=yt_dlp.extractor.lazy_extractors", script)
        self.assertIn("scripts\\validate_ico.py", script)
        self.assertIn("Invalid icon file, skipping EXE icon", script)
        self.assertIn('if not "%ICON_OPTION%"=="" if exist "logo"', script)
        self.assertIn("for %%D in (app Controller remote_browser configs)", script)
        self.assertIn("robocopy \"%%D\"", script)
        self.assertIn("remote_browser missing from output", script)
        self.assertIn("Controller missing from output", script)
        self.assertIn("app package missing from output", script)
        self.assertIn("--output-filename=SmartTikTok.exe", script)
        self.assertIn("--output-dir=%BUILD_ROOT%", script)
        self.assertIn("app\\launcher.py", script)
        self.assertIn("build\\nuitka\\SmartTikTok", script)

    def test_onefile_build_script_creates_single_exe_package(self):
        script = (ROOT / "scripts" / "build_nuitka_onefile_admin.bat").read_text(encoding="utf-8")

        self.assertIn("Start-Process", script)
        self.assertIn("-Verb RunAs", script)
        self.assertIn("--onefile", script)
        self.assertIn("--standalone", script)
        self.assertIn("--enable-plugin=pyqt6", script)
        self.assertIn("--include-package=app", script)
        self.assertIn("--include-package=Controller", script)
        self.assertIn("--include-package=remote_browser", script)
        self.assertIn("--include-data-dir=logo=logo", script)
        self.assertIn("--include-data-dir=configs=configs", script)
        self.assertIn('--onefile-cache-mode=cached', script)
        self.assertIn('--onefile-tempdir-spec="SmartTikTok.runtime"', script)
        self.assertNotIn("{CACHE_DIR}\\SmartTikTok\\onefile", script)
        self.assertIn("--windows-icon-from-ico=%ICON_PATH%", script)
        self.assertIn("--output-filename=SmartTikTok.exe", script)
        self.assertIn("--output-dir=%OUTPUT_DIR%", script)
        self.assertIn("app\\launcher.py", script)
        self.assertIn("build\\nuitka-onefile", script)
        self.assertNotIn('rmdir /s /q "%OUTPUT_DIR%"', script)
        self.assertIn('if exist "%OUTPUT_DIR%\\SmartTikTok.exe" del /f /q "%OUTPUT_DIR%\\SmartTikTok.exe"', script)
        self.assertIn('if exist "%OUTPUT_DIR%\\SmartTikTok.runtime" rmdir /s /q "%OUTPUT_DIR%\\SmartTikTok.runtime"', script)
        self.assertIn('if exist "%OUTPUT_DIR%\\launcher.onefile-build" rmdir /s /q "%OUTPUT_DIR%\\launcher.onefile-build"', script)
        self.assertNotIn("xcopy", script.lower())
        self.assertNotIn("robocopy", script.lower())


if __name__ == "__main__":
    unittest.main()
