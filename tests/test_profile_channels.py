import tempfile
import unittest
from pathlib import Path

from app.profiles.store import (
    create_chrome_profiles,
    load_profiles,
    update_profile_channel,
    update_profile_fields,
    get_assigned_profiles,
)


class ProfileChannelTest(unittest.TestCase):
    def test_created_profiles_have_empty_channel_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles = create_chrome_profiles(
                data_path=root / "data" / "profiles.json",
                profiles_dir=root / "profiles",
                count=1,
                name_prefix="acc",
                note="",
                group="YTB",
            )

            self.assertEqual(profiles[0]["channel_url"], "")
            self.assertEqual(profiles[0]["channel_mode"], "shorts")
            self.assertEqual(profiles[0]["last_status"], "Idle")

    def test_update_profile_channel_normalizes_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            create_chrome_profiles(data_path, root / "profiles", 1, "acc", "", "")
            profile_id = load_profiles(data_path)[0]["id"]

            updated = update_profile_channel(
                data_path=data_path,
                profile_id=profile_id,
                channel_url=" https://www.youtube.com/@hoangacc/videos ",
                channel_mode="videos",
            )

            self.assertTrue(updated)
            profile = load_profiles(data_path)[0]
            self.assertEqual(profile["channel_url"], "https://www.youtube.com/@hoangacc/videos")
            self.assertEqual(profile["channel_mode"], "videos")

    def test_update_profile_channel_preserves_one_url_per_line_and_removes_blanks(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "profiles.json"
            profiles = create_chrome_profiles(data_path, Path(tmp) / "profiles", 1, "acc", "", "")
            profile_id = profiles[0]["id"]

            update_profile_channel(
                data_path,
                profile_id,
                " https://www.youtube.com/@a/videos \n\n https://www.youtube.com/@b/shorts ",
                "videos",
            )

            profile = load_profiles(data_path)[0]
            self.assertEqual(
                profile["channel_url"],
                "https://www.youtube.com/@a/videos\nhttps://www.youtube.com/@b/shorts",
            )

    def test_get_assigned_profiles_returns_only_profiles_with_channel_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            create_chrome_profiles(data_path, root / "profiles", 2, "acc", "", "")
            profiles = load_profiles(data_path)
            update_profile_channel(data_path, profiles[1]["id"], "https://www.youtube.com/@hoangacc/shorts", "shorts")

            assigned = get_assigned_profiles(data_path)

            self.assertEqual([profile["id"] for profile in assigned], [profiles[1]["id"]])

    def test_update_profile_channel_rejects_invalid_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "data" / "profiles.json"
            create_chrome_profiles(data_path, root / "profiles", 1, "acc", "", "")
            profile_id = load_profiles(data_path)[0]["id"]

            with self.assertRaises(ValueError):
                update_profile_channel(data_path, profile_id, "https://www.youtube.com/@hoangacc/shorts", "live")

    def test_update_profile_fields_persists_note_group_channel_and_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "profiles.json"
            profiles = create_chrome_profiles(data_path, Path(tmp) / "profiles", 1, "acc", "", "")
            profile_id = profiles[0]["id"]

            updated = update_profile_fields(
                data_path,
                profile_id,
                note="new note",
                group="new group",
                channel_url="https://www.youtube.com/@a\nhttps://www.youtube.com/@b",
                channel_mode="videos",
            )

            self.assertTrue(updated)
            profile = load_profiles(data_path)[0]
            self.assertEqual(profile["note"], "new note")
            self.assertEqual(profile["group"], "new group")
            self.assertEqual(profile["channel_mode"], "videos")
            self.assertEqual(profile["channel_url"], "https://www.youtube.com/@a\nhttps://www.youtube.com/@b")


if __name__ == "__main__":
    unittest.main()
