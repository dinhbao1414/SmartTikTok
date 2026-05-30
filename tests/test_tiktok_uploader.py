import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.tiktok.uploader import TikTokUploader


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
        self.schedule_radio = FakeElement("Schedule")
        self.time_dropdown = FakeElement("Time")
        self.date_dropdown = FakeElement("Date")
        self.hour_option = FakeElement("9")
        self.minute_option = FakeElement("00")
        self.day_option = FakeElement("30")
        self.cancel_button = FakeElement("Huy")
        self.got_it_button = FakeElement("Da hieu")
        self.post_button = FakeElement("Post")
        self.description_box = FakeElement()
        self.scripts = []
        self.script_calls = []
        self.sleep_calls = []
        self.sent_text = []
        self.clicked_elements = []
        self.moved_elements = []
        self.js_clicked_elements = []
        self.fail_click_elements = set()

    def get(self, url, wait_load=False):
        self.urls.append(url)
        self.post_button.clicked = False

    def find_element(self, by, value, timeout=None):
        if value == 'input[type="file"]':
            return self.wrong_file_input
        if value == 'input[type="file"][accept*="video"]':
            return self.video_file_input
        return None

    def execute_script(self, script, *args, **kwargs):
        self.scripts.append(script)
        self.script_calls.append({"script": script, "args": args})
        if "UPLOAD_BUTTON_SCRIPT" in script:
            return self.upload_button
        if "SCHEDULE_RADIO_SCRIPT" in script:
            return self.schedule_radio
        if "TIME_DROPDOWN_SCRIPT" in script:
            return self.time_dropdown
        if "DATE_DROPDOWN_SCRIPT" in script:
            return self.date_dropdown
        if "TIME_OPTION_SCRIPT" in script:
            if args[0] in {"9", "22"}:
                return self.hour_option
            if args[0] in {"0", "00", "10"}:
                return self.minute_option
        if "DATE_OPTION_SCRIPT" in script:
            return self.day_option if args[0] == "30" and len(args) >= 3 else None
        if "OPTIONAL_CANCEL_BUTTON_SCRIPT" in script:
            return self.cancel_button
        if "OPTIONAL_GOT_IT_BUTTON_SCRIPT" in script:
            return self.got_it_button
        if "POST_BUTTON_SCRIPT" in script:
            return self.post_button
        if "DESCRIPTION_ELEMENT_SCRIPT" in script:
            return self.description_box
        if "FILL_DESCRIPTION_SCRIPT" in script:
            args[0].value = args[1]
            return True
        if "CLICK_ELEMENT_FALLBACK_SCRIPT" in script:
            self.js_clicked_elements.append(args[0])
            args[0].click()
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
        if element in self.fail_click_elements:
            raise ValueError("Box qua nho")
        self.clicked_elements.append(element)
        element.click()
        return element

    def move_to_element(self, element):
        self.moved_elements.append(element)
        return element

class ProcessingRemote:
    def __init__(self):
        self.sleep_count = 0

    def execute_script(self, script, *args, **kwargs):
        return "still processing"

    def sleep(self, timeout):
        self.sleep_count += 1

class PostVisibleBeforeUploadCompleteRemote:
    def __init__(self):
        self.body_texts = ["Post", "Upload complete"]
        self.sleep_count = 0

    def execute_script(self, script, *args, **kwargs):
        if "document.body.innerText" in script:
            return self.body_texts.pop(0)
        return None

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
            self.assertEqual(wrapper.browser.moved_elements, [wrapper.browser.upload_button])
            self.assertTrue(wrapper.browser.cancel_button.clicked)
            self.assertTrue(wrapper.browser.got_it_button.clicked)
            self.assertTrue(wrapper.browser.post_button.clicked)
            self.assertEqual(wrapper.browser.clicked_elements[-1], wrapper.browser.post_button)
            self.assertEqual(wrapper.browser.sleep_calls[-1], 5)
            self.assertTrue(wrapper.closed)

    def test_upload_scheduled_selects_schedule_time_and_day_before_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            result = uploader.upload_scheduled(
                profile_path=tmp,
                video_path=video,
                schedule_day=30,
                schedule_hour=9,
                schedule_minute=0,
            )

            self.assertEqual(result["status"], "uploaded")
            self.assertTrue(wrapper.browser.schedule_radio.clicked)
            self.assertTrue(wrapper.browser.time_dropdown.clicked)
            self.assertTrue(wrapper.browser.hour_option.clicked)
            self.assertTrue(wrapper.browser.minute_option.clicked)
            self.assertTrue(wrapper.browser.date_dropdown.clicked)
            self.assertTrue(wrapper.browser.day_option.clicked)
            self.assertEqual(wrapper.browser.clicked_elements[-1], wrapper.browser.post_button)

    def test_upload_scheduled_passes_month_and_year_to_date_picker(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            uploader.upload_scheduled(
                profile_path=tmp,
                video_path=video,
                schedule_day=30,
                schedule_hour=22,
                schedule_minute=10,
                schedule_month=5,
                schedule_year=2026,
            )

            date_calls = [
                call for call in wrapper.browser.script_calls
                if "DATE_OPTION_SCRIPT" in call["script"]
            ]
            self.assertEqual(date_calls[-1]["args"], ("30", "5", "2026"))

    def test_schedule_picker_options_use_js_fallback_when_mouse_click_box_is_too_small(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            wrapper = FakeChromeProfileBrowser(tmp)
            wrapper.browser.fail_click_elements.update({
                wrapper.browser.hour_option,
                wrapper.browser.minute_option,
                wrapper.browser.day_option,
            })
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            uploader.upload_scheduled(
                profile_path=tmp,
                video_path=video,
                schedule_day=30,
                schedule_hour=9,
                schedule_minute=0,
            )

            self.assertEqual(wrapper.browser.js_clicked_elements, [
                wrapper.browser.hour_option,
                wrapper.browser.minute_option,
                wrapper.browser.day_option,
            ])
            self.assertTrue(wrapper.browser.post_button.clicked)

    def test_picker_fallback_does_not_scroll_popup_closed(self):
        from app.tiktok.uploader import CLICK_ELEMENT_FALLBACK_SCRIPT

        self.assertNotIn("scrollIntoView", CLICK_ELEMENT_FALLBACK_SCRIPT)
        self.assertIn("getBoundingClientRect", CLICK_ELEMENT_FALLBACK_SCRIPT)

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

        with patch("app.tiktok.uploader.time.time", side_effect=[0, 0, 2]):
            uploader._wait_until_finished(remote, timeout=1)

        self.assertEqual(remote.sleep_count, 1)

    def test_wait_after_file_ignores_post_text_until_upload_complete(self):
        remote = PostVisibleBeforeUploadCompleteRemote()
        uploader = TikTokUploader(browser_factory=FakeChromeProfileBrowser, wait_seconds=0)

        uploader._wait_after_file(remote, timeout=1)

        self.assertEqual(remote.sleep_count, 1)

    def test_wait_until_finished_returns_on_tiktok_content_page(self):
        remote = ContentPageRemote()
        uploader = TikTokUploader(browser_factory=FakeChromeProfileBrowser, wait_seconds=0)

        uploader._wait_until_finished(remote, timeout=1)

        self.assertEqual(remote.sleep_count, 0)

    def test_post_button_script_targets_tiktok_data_e2e_button(self):
        from app.tiktok.uploader import DATE_OPTION_SCRIPT, POST_BUTTON_SCRIPT

        self.assertIn('[data-e2e="post_video_button"]', POST_BUTTON_SCRIPT)
        self.assertIn("data-disabled", POST_BUTTON_SCRIPT)
        self.assertIn("len lich", POST_BUTTON_SCRIPT)
        self.assertIn(".calendar-wrapper .day.valid", DATE_OPTION_SCRIPT)

    def test_time_dropdown_script_targets_time_input_box(self):
        from app.tiktok.uploader import TIME_DROPDOWN_SCRIPT, TIME_OPTION_SCRIPT

        self.assertIn(".TUXInputBox", TIME_DROPDOWN_SCRIPT)
        self.assertIn(r"^\d{1,2}:\d{2}$", TIME_DROPDOWN_SCRIPT)
        self.assertIn(".TUXTextInputCore-trailingIconWrapper", TIME_DROPDOWN_SCRIPT)
        self.assertIn(".tiktok-timepicker-time-scroll-container", TIME_OPTION_SCRIPT)
        self.assertIn("scrollTop", TIME_OPTION_SCRIPT)
        self.assertIn("mousemove", TIME_OPTION_SCRIPT)

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
            self.assertEqual(
                [element for element in wrapper.browser.clicked_elements if element is wrapper.browser.post_button],
                [wrapper.browser.post_button, wrapper.browser.post_button, wrapper.browser.post_button],
            )
            self.assertEqual([entry["text"] for entry in wrapper.browser.sent_text], [
                "Video A Part 1",
                "Video A Part 2",
                "Video A Part 3",
            ])
            self.assertTrue(wrapper.closed)

    def test_upload_many_applies_schedule_per_item_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            videos = []
            for index in range(1, 4):
                video = root / f"part_{index}.mp4"
                video.write_bytes(b"video")
                videos.append(video)
            wrapper = FakeChromeProfileBrowser(tmp)
            uploader = TikTokUploader(browser_factory=lambda profile_path: wrapper, wait_seconds=0)

            uploader.upload_many(
                profile_path=tmp,
                upload_items=[
                    {"file_path": str(videos[0]), "title": "Video A Part 1"},
                    {
                        "file_path": str(videos[1]),
                        "title": "Video A Part 2",
                        "schedule": {"day": 30, "month": 5, "year": 2026, "hour": 22, "minute": 10},
                    },
                ],
            )

            self.assertEqual(wrapper.browser.schedule_radio.click_count, 1)
            self.assertEqual(wrapper.browser.date_dropdown.click_count, 1)
            self.assertEqual(wrapper.browser.post_button.click_count, 2)


if __name__ == "__main__":
    unittest.main()
