import json
import tempfile
import unittest
from pathlib import Path


from app.profiles.store import (
    create_chrome_profiles,
    delete_profile_record,
    load_profiles,
    save_profiles,
)


class ChromeProfilesTest(unittest.TestCase):
    def test_create_chrome_profiles_persists_records_and_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            profiles_dir = root / "profiles"

            created = create_chrome_profiles(
                data_path=data_path,
                profiles_dir=profiles_dir,
                count=2,
                name_prefix="acc",
                note="login tay",
                group="nhom A",
            )

            self.assertEqual(len(created), 2)
            self.assertEqual(created[0]["name"], "acc 1")
            self.assertEqual(created[1]["name"], "acc 2")
            self.assertTrue(Path(created[0]["profile_path"]).is_dir())
            self.assertEqual(load_profiles(data_path), created)

    def test_delete_profile_record_removes_folder_and_json_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            profile_dir = root / "profiles" / "abc"
            profile_dir.mkdir(parents=True)
            record = {
                "id": "abc",
                "name": "acc",
                "note": "",
                "group": "",
                "type": "Chrome",
                "profile_path": str(profile_dir),
            }
            save_profiles(data_path, [record])

            deleted = delete_profile_record(data_path=data_path, profile_id="abc")

            self.assertTrue(deleted)
            self.assertFalse(profile_dir.exists())
            self.assertEqual(load_profiles(data_path), [])

    def test_load_profiles_recovers_from_missing_or_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "data" / "profiles.json"
            self.assertEqual(load_profiles(data_path), [])
            data_path.parent.mkdir(parents=True)
            data_path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_profiles(data_path), [])


if __name__ == "__main__":
    unittest.main()
