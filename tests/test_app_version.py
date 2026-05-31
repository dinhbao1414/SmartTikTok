import json
import tempfile
import unittest
from pathlib import Path

from app.version import DEFAULT_APP_VERSION, read_app_version, write_app_version


class AppVersionTest(unittest.TestCase):
    def test_reads_version_json_from_app_state_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            version_file = Path(tmp) / "version.json"
            version_file.write_text(json.dumps({"version": "1.0.9"}), encoding="utf-8")

            self.assertEqual(read_app_version(base_dir=tmp), "1.0.9")

    def test_falls_back_to_default_when_version_json_missing_or_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_app_version(base_dir=tmp), DEFAULT_APP_VERSION)
            (Path(tmp) / "version.json").write_text("{}", encoding="utf-8")

            self.assertEqual(read_app_version(base_dir=tmp), DEFAULT_APP_VERSION)

    def test_writes_version_json_to_app_state_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_app_version("1.0.9", base_dir=tmp, updated_at="2026-05-31T18:15:39")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], "1.0.9")
            self.assertEqual(data["updated_at"], "2026-05-31T18:15:39")


if __name__ == "__main__":
    unittest.main()
