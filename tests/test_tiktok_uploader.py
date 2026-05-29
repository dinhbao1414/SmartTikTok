import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tiktok_uploader import TikTokUploader


class FakeElement:
    def __init__(self, text=""):
        self.sent_file = ""
        self.sent_files = []
        self.clicked = False
        self.click_count = 0
        self.text = text
        self.value = ""

    def send_file(self, file_path):
        self.sent_file = file_path
        self.sent_files.append(file_path)

    def click(self):
        self.clicked = True
        self.click_count += 1


class FakeRemote:
    def __init__(self):
        self.urls = []
        self.wrong_file_input = FakeElement()
        self.video_file_input = FakeElement()
        self.upload_button = FakeElement("Upload")
        self.post_button = FakeElement("Post")
        self.description_box = FakeElement()
        self.scripts = []
        self.sleep_calls = []
        self.sent_text = []
        self.clicked_elements = []

    def get(self, url, wait_load=False):
        self.urls.append(url)

    def find_element(self, by, value, timeout=None):
        if value == 'input[type="file"]':
            return self.wrong_file_input
        if value == 'input[type="file"][accept*="video"]':
            return self.video_file_input
        return None

    def execute_script(self, script, *args, **kwargs):
        self.scripts.append(script)
        if "UPLOAD_BUTTON_SCRIPT" in script:
            return self.upload_button
        if "POST_BUTTON_SCRIPT" in script:
            return self.post_button
        if "DESCRIPTION_ELEMENT_SCRIPT" in script:
            return self.description_box
        if "FILL_DESCRIPTION_SCRIPT" in script:
            args[0].value = args[1]
            return True
        if "FILE_INPUT_CHANGE_SCRIPT" in script:
            return True
        if "document.body.innerText" in script:
            if self.post_button.clicked:
                return "Published"
            return "Upload complete"
        return None

    def sleep(self, timeout):
        self.sleep_calls.append(timeout)
        return None

    def send_text(self, text, send_enter=False, clear_text=True):
        self.sent_text.append({
            "text": text,
            "send_enter": send_enter,
            "clear_text": clear_text,
        })
        return None

    def click_element(self, element):
        self.clicked_elements.append(element)
        element.click()
        return element

class ProcessingRemote:
    def __init__(self):
        self.sleep_count = 0

    def execute_script(self, script, *args, **kwargs):
        return "still processing"

    def sleep(self, timeout):
        self.sleep_count += 1

class ContentPageRemote:
    def __init__(self):
        self.sleep_count = 0

    def execute_script(self, script, *args, **kwargs):
        if "window.location.href" in script:
            return "https://www.tiktok.com/tiktokstudio/content"
        return "Posts 65"

    def sleep(self, timeout):
        self.sleep_count += 1


class FakeChromeProfileBrowser:
    def __init__(self, profile_path, width=1100, height=800):
        self.browser = FakeRemote()
        self.closed = False

    def open(self, url):
        self.browser.get(url, wait_load=False)
        return self

    def close(self):
        self.closed = True


class TikTokUploaderTest(unittest.TestCase):
    def test_upload_sends_file_and_clicks_post_button(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            result = uploader.upload(profile_path=tmp, video_path=video)

            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(wrapper.browser.video_file_input.sent_file, str(video.resolve()))
            self.assertEqual(wrapper.browser.wrong_file_input.sent_file, "")
            self.assertFalse(wrapper.browser.upload_button.clicked)
            self.assertTrue(wrapper.browser.post_button.clicked)
            self.assertEqual(wrapper.browser.clicked_elements, [wrapper.browser.post_button])
            self.assertEqual(wrapper.browser.sleep_calls[-1], 5)
            self.assertTrue(wrapper.closed)

    def test_upload_fills_description_before_clicking_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            uploader.upload(profile_path=tmp, video_path=video, title="My Short Title")

            self.assertTrue(wrapper.browser.description_box.clicked)
            self.assertEqual(
                wrapper.browser.sent_text[-1],
                {
                    "text": "My Short Title",
                    "send_enter": False,
                    "clear_text": True,
                },
            )
            self.assertTrue(wrapper.browser.post_button.clicked)
            self.assertTrue(wrapper.closed)

    def test_upload_rejects_missing_file(self):
        uploader = TikTokUploader(browser_factory=FakeChromeProfileBrowser, wait_seconds=0)
        with self.assertRaises(FileNotFoundError):
            uploader.upload(profile_path="profile", video_path="missing.mp4")

    def test_wait_until_finished_does_not_return_on_processing_text(self):
        remote = ProcessingRemote()
        uploader = TikTokUploader(browser_factory=FakeChromeProfileBrowser, wait_seconds=0)

        with patch("tiktok_uploader.time.time", side_effect=[0, 0, 2]):
            uploader._wait_until_finished(remote, timeout=1)

        self.assertEqual(remote.sleep_count, 1)

    def test_wait_until_finished_returns_on_tiktok_content_page(self):
        remote = ContentPageRemote()
        uploader = TikTokUploader(browser_factory=FakeChromeProfileBrowser, wait_seconds=0)

        uploader._wait_until_finished(remote, timeout=1)

        self.assertEqual(remote.sleep_count, 0)

    def test_post_button_script_targets_tiktok_data_e2e_button(self):
        from tiktok_uploader import POST_BUTTON_SCRIPT

        self.assertIn('[data-e2e="post_video_button"]', POST_BUTTON_SCRIPT)
        self.assertIn("data-disabled", POST_BUTTON_SCRIPT)

    def test_upload_many_reuses_profile_and_reloads_upload_url_for_each_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            videos = []
            for index in range(1, 4):
                video = root / f"part_{index}.mp4"
                video.write_bytes(b"video")
                videos.append(video)
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            results = uploader.upload_many(
                profile_path=tmp,
                upload_items=[
                    {"file_path": str(videos[0]), "title": "Video A Part 1"},
                    {"file_path": str(videos[1]), "title": "Video A Part 2"},
                    {"file_path": str(videos[2]), "title": "Video A Part 3"},
                ],
            )

            self.assertEqual([result["status"] for result in results], ["uploaded", "uploaded", "uploaded"])
            self.assertEqual(len(wrapper.browser.urls), 3)
            self.assertTrue(all(url == uploader.upload_url for url in wrapper.browser.urls))
            self.assertEqual(wrapper.browser.post_button.click_count, 3)
            self.assertEqual(len(wrapper.browser.clicked_elements), 3)
            self.assertEqual([entry["text"] for entry in wrapper.browser.sent_text], [
                "Video A Part 1",
                "Video A Part 2",
                "Video A Part 3",
            ])
            self.assertTrue(wrapper.closed)


if __name__ == "__main__":
    unittest.main()
