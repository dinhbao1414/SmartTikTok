import time
from pathlib import Path

from app.paths import TIKTOK_UPLOAD_URL

UPLOAD_BUTTON_SCRIPT = """
/* UPLOAD_BUTTON_SCRIPT */
const isVisible = (button) => {
    const rect = button.getBoundingClientRect();
    const style = window.getComputedStyle(button);
    return rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0';
};
return Array.from(document.querySelectorAll('button, [role="button"], label')).find((button) => {
    const text = (button.innerText || button.textContent || '')
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .toLowerCase();
    return isVisible(button) && (
        text.includes('upload') ||
        text.includes('select video') ||
        text.includes('tai len') ||
        text.includes('chon video')
    );
}) || null;
"""

POST_BUTTON_SCRIPT = """
/* POST_BUTTON_SCRIPT */
const isEnabled = (button) => {
    return !button.disabled &&
        button.getAttribute('aria-disabled') !== 'true' &&
        button.getAttribute('data-disabled') !== 'true' &&
        button.getAttribute('data-loading') !== 'true';
};
const exactPostButton = document.querySelector('button[data-e2e="post_video_button"], [role="button"][data-e2e="post_video_button"]');
if (exactPostButton && isEnabled(exactPostButton)) {
    return exactPostButton;
}
return Array.from(document.querySelectorAll('button, [role="button"]')).find((button) => {
    const text = (button.innerText || button.textContent || '')
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .toLowerCase();
    return isEnabled(button) && (
        text.includes('post') ||
        text.includes('publish') ||
        text.includes('dang')
    );
});
"""

DESCRIPTION_ELEMENT_SCRIPT = """
/* DESCRIPTION_ELEMENT_SCRIPT */
const isVisible = (field) => {
    const rect = field.getBoundingClientRect();
    const style = window.getComputedStyle(field);
    return rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0';
};
const selectors = [
    '.caption-editor [contenteditable="true"][role="combobox"]',
    '.caption-editor .public-DraftEditor-content[contenteditable="true"]',
    '.DraftEditor-root .public-DraftEditor-content[contenteditable="true"]',
    '[contenteditable="true"][role="combobox"]',
];
for (const selector of selectors) {
    const field = Array.from(document.querySelectorAll(selector)).find(isVisible);
    if (field) {
        return field;
    }
}
const normalize = (value) => (value || '')
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .trim()
    .toLowerCase();
const fields = Array.from(document.querySelectorAll(
    '[contenteditable="true"], textarea, input[type="text"]'
)).filter(isVisible);
return fields.find((field) => {
    const text = normalize([
        field.getAttribute('aria-label'),
        field.getAttribute('placeholder'),
        field.getAttribute('data-placeholder'),
        field.closest('[aria-label]')?.getAttribute('aria-label'),
        field.parentElement?.innerText,
    ].filter(Boolean).join(' '));
    return text.includes('description') ||
        text.includes('caption') ||
        text.includes('mo ta') ||
        text.includes('describe');
}) || fields.find((field) => field.getAttribute('contenteditable') === 'true') || null;
"""

FILL_DESCRIPTION_SCRIPT = """
/* FILL_DESCRIPTION_SCRIPT */
const field = arguments[0];
const value = arguments[1] || '';
field.focus();
if (field.getAttribute && field.getAttribute('contenteditable') === 'true') {
    field.innerText = value;
} else {
    field.value = value;
}
field.dispatchEvent(new Event('input', { bubbles: true }));
field.dispatchEvent(new Event('change', { bubbles: true }));
return true;
"""

FILE_INPUT_CHANGE_SCRIPT = """
/* FILE_INPUT_CHANGE_SCRIPT */
const field = arguments[0];
field.dispatchEvent(new Event('input', { bubbles: true }));
field.dispatchEvent(new Event('change', { bubbles: true }));
return true;
"""

def default_browser_factory(profile_path):
    from Controller.BrowserController import ChromeProfileBrowser

    return ChromeProfileBrowser(profile_path)

class TikTokUploader:
    def __init__(self, browser_factory=None, upload_url=TIKTOK_UPLOAD_URL, wait_seconds=2, close_delay_seconds=5):
        self.browser_factory = browser_factory or default_browser_factory
        self.upload_url = upload_url
        self.wait_seconds = wait_seconds
        self.close_delay_seconds = close_delay_seconds

    def upload(self, profile_path, video_path, title="", timeout=180):
        file_path = Path(video_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        return self.upload_many(
            profile_path,
            [{"file_path": str(file_path), "title": title or file_path.stem}],
            timeout=timeout,
        )[0]

    def upload_many(self, profile_path, upload_items, timeout=180):
        normalized_items = self._normalize_upload_items(upload_items)
        if not normalized_items:
            return []

        wrapper = self.browser_factory(profile_path)
        browser = None
        uploaded_any = False
        try:
            results = []
            for item in normalized_items:
                wrapper.open(self.upload_url)
                browser = wrapper.browser
                if hasattr(browser, "show_mouse"):
                    browser.show_mouse()
                results.append(self._upload_current_page(browser, item["file_path"], item["title"], timeout))
                uploaded_any = True
            return results
        finally:
            if uploaded_any and browser and self.close_delay_seconds > 0:
                browser.sleep(self.close_delay_seconds)
            wrapper.close()

    def _normalize_upload_items(self, upload_items):
        normalized = []
        for item in upload_items:
            file_path = Path(item["file_path"]).resolve()
            if not file_path.exists():
                raise FileNotFoundError(str(file_path))
            normalized.append({
                "file_path": str(file_path),
                "title": item.get("title") or file_path.stem,
            })
        return normalized

    def _upload_current_page(self, browser, file_path, title, timeout):
        self._hover_upload_button(browser)
        file_input = self._find_video_file_input(browser, timeout=30)
        if not file_input:
            raise RuntimeError("TikTok upload input not found. Profile may not be logged in.")

        file_input.send_file(str(file_path))
        browser.execute_script(FILE_INPUT_CHANGE_SCRIPT, file_input)
        self._wait_after_file(browser, timeout)
        self._fill_description(browser, title)

        post_button = self._find_post_button(browser, timeout)
        if not post_button:
            raise RuntimeError("TikTok post button not found or disabled.")

        self._click_visible(browser, post_button)
        self._wait_until_finished(browser, timeout)
        return {"status": "uploaded", "file_path": str(file_path)}

    def _find_video_file_input(self, browser, timeout):
        selectors = [
            'input[type="file"][accept*="video"]',
            'input[type="file"][accept*="mp4"]',
            'input[type="file"]',
        ]
        for selector in selectors:
            file_input = browser.find_element("css selector", selector, timeout=timeout)
            if file_input:
                return file_input
        return None

    def _hover_upload_button(self, browser):
        upload_button = browser.execute_script(UPLOAD_BUTTON_SCRIPT)
        if upload_button and hasattr(browser, "move_to_element"):
            browser.move_to_element(upload_button)
        return upload_button

    def _fill_description(self, browser, title):
        if not title:
            return False
        description = browser.execute_script(DESCRIPTION_ELEMENT_SCRIPT)
        if not description:
            return False
        description.click()
        browser.sleep(0.3)
        if hasattr(browser, "send_text"):
            browser.send_text(str(title), send_enter=False, clear_text=True)
            return True
        return bool(browser.execute_script(FILL_DESCRIPTION_SCRIPT, description, title))

    def _click_visible(self, browser, element):
        if hasattr(browser, "click_element"):
            clicked = browser.click_element(element)
            if clicked:
                return clicked
        return element.click()

    def _wait_after_file(self, browser, timeout):
        end_at = time.time() + timeout
        while time.time() < end_at:
            body_text = browser.execute_script("return document.body.innerText || ''") or ""
            lowered = body_text.lower()
            if "upload complete" in lowered or "post" in lowered or "publish" in lowered or "dang" in lowered:
                return
            browser.sleep(self.wait_seconds)
        raise TimeoutError("TikTok upload did not become ready before timeout.")

    def _find_post_button(self, browser, timeout):
        end_at = time.time() + timeout
        while time.time() < end_at:
            button = browser.execute_script(POST_BUTTON_SCRIPT)
            if button:
                return button
            browser.sleep(self.wait_seconds)
        return None

    def _wait_until_finished(self, browser, timeout):
        end_at = time.time() + timeout
        while time.time() < end_at:
            current_url = browser.execute_script("return window.location.href || ''") or ""
            if "/tiktokstudio/content" in current_url:
                return
            body_text = browser.execute_script("return document.body.innerText || ''") or ""
            lowered = body_text.lower()
            if (
                "uploaded" in lowered
                or "published" in lowered
                or "video has been posted" in lowered
                or "your video is being uploaded" in lowered
            ):
                return
            browser.sleep(self.wait_seconds)
        return
