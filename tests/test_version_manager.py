import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VersionManagerSourceTest(unittest.TestCase):
    def test_update_manager_uses_smart_tiktok_branding(self):
        source = (ROOT / "version_manager.py").read_text(encoding="utf-8")

        self.assertIn("SmartTikTok_Update.zip", source)
        self.assertIn("SmartTikTok.exe", source)
        self.assertNotIn("CapcutAuto", source)


if __name__ == "__main__":
    unittest.main()
