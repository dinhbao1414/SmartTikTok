import time
from datetime import datetime
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

SCHEDULE_RADIO_SCRIPT = """
/* SCHEDULE_RADIO_SCRIPT */
const radio = document.querySelector('input[name="postSchedule"][value="schedule"]');
if (radio) {
    return radio;
}
return Array.from(document.querySelectorAll('button, [role="button"], label, input[type="radio"]')).find((element) => {
    const text = (element.innerText || element.textContent || element.value || '')
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .toLowerCase();
    return text.includes('schedule') || text.includes('len lich');
}) || null;
"""

TIME_DROPDOWN_SCRIPT = """
/* TIME_DROPDOWN_SCRIPT */
const isVisible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0';
};
const boxes = Array.from(document.querySelectorAll('.TUXInputBox')).filter(isVisible);
const timeBox = boxes.find((box) => {
    const input = box.querySelector('input[readonly], input');
    const value = (input?.value || '').trim();
    return /^\\d{1,2}:\\d{2}$/.test(value);
});
return timeBox?.querySelector('.TUXTextInputCore-trailingIconWrapper') ||
    timeBox?.querySelector('[data-testid="ArrowDown"]') ||
    null;
"""

DATE_DROPDOWN_SCRIPT = """
/* DATE_DROPDOWN_SCRIPT */
const isVisible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0';
};
const boxes = Array.from(document.querySelectorAll('.TUXInputBox')).filter(isVisible);
const dateBox = boxes.find((box) => {
    const input = box.querySelector('input[readonly], input');
    const value = (input?.value || '').trim();
    return value && !/^\\d{1,2}:\\d{2}$/.test(value);
});
return dateBox?.querySelector('.TUXTextInputCore-trailingIconWrapper') ||
    dateBox?.querySelector('[data-testid="ArrowDown"]') ||
    null;
"""

TIME_OPTION_SCRIPT = """
/* TIME_OPTION_SCRIPT */
const value = String(arguments[0]).padStart(2, '0');
const side = arguments[1] || 'left';
const selector = side === 'right'
    ? '.tiktok-timepicker-option-text.tiktok-timepicker-right'
    : '.tiktok-timepicker-option-text.tiktok-timepicker-left';
const isVisible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0';
};
const text = (element) => (element.innerText || element.textContent || '').trim().padStart(2, '0');
const optionText = Array.from(document.querySelectorAll(selector)).find((element) => {
    return isVisible(element) && text(element) === value;
});
if (!optionText) {
    return null;
}
const option = optionText.closest('.tiktok-timepicker-option-item') || optionText;
const container = optionText.closest('.tiktok-timepicker-time-scroll-container');
if (container) {
    const rect = container.getBoundingClientRect();
    container.dispatchEvent(new MouseEvent('mousemove', {
        bubbles: true,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2,
    }));
    const optionRect = option.getBoundingClientRect();
    container.scrollTop += optionRect.top - rect.top - (rect.height / 2) + (optionRect.height / 2);
}
return option;
"""

DATE_OPTION_SCRIPT = """
/* DATE_OPTION_SCRIPT */
const value = String(arguments[0]).trim();
const targetMonth = Number(arguments[1]);
const targetYear = Number(arguments[2]);
const isVisible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0';
};
const wrapper = Array.from(document.querySelectorAll('.calendar-wrapper')).find(isVisible);
if (wrapper && targetMonth && targetYear) {
    const monthText = (wrapper.querySelector('.month-title')?.innerText || '').trim();
    const yearText = (wrapper.querySelector('.year-title')?.innerText || '').trim();
    const visibleMonth = Number((monthText.match(/\\d+/) || [])[0]);
    const visibleYear = Number((yearText.match(/\\d+/) || [])[0]);
    if (visibleMonth === targetMonth && visibleYear === targetYear) {
        const days = Array.from(wrapper.querySelectorAll('.days-wrapper .day'));
        const monthStart = days.findIndex((element) => (element.innerText || element.textContent || '').trim() === '1');
        const monthEndDay = new Date(targetYear, targetMonth, 0).getDate();
        if (monthStart >= 0) {
            const currentMonthDays = days.slice(monthStart, monthStart + monthEndDay);
            const currentMonthMatch = currentMonthDays.find((element) => {
                const text = (element.innerText || element.textContent || '').trim();
                return isVisible(element) && text === value && element.classList.contains('valid');
            });
            if (currentMonthMatch) {
                return currentMonthMatch;
            }
        }
    }
}
const candidates = Array.from(document.querySelectorAll('.calendar-wrapper .day.valid'));
return candidates.find((element) => {
    const text = (element.innerText || element.textContent || '').trim();
    return isVisible(element) && text === value;
}) || null;
"""

OPTIONAL_CANCEL_BUTTON_SCRIPT = """
/* OPTIONAL_CANCEL_BUTTON_SCRIPT */
const normalize = (value) => (value || '')
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .replace(/[đĐ]/g, 'd')
    .trim()
    .toLowerCase();
const isEnabled = (button) => {
    return !button.disabled &&
        button.getAttribute('aria-disabled') !== 'true' &&
        button.getAttribute('data-disabled') !== 'true' &&
        button.getAttribute('data-loading') !== 'true';
};
return Array.from(document.querySelectorAll('button, [role="button"]')).find((button) => {
    const text = normalize(button.innerText || button.textContent || '');
    return isEnabled(button) && (text === 'huy' || text === 'cancel');
}) || null;
"""

OPTIONAL_GOT_IT_BUTTON_SCRIPT = """
/* OPTIONAL_GOT_IT_BUTTON_SCRIPT */
const normalize = (value) => (value || '')
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .replace(/[đĐ]/g, 'd')
    .trim()
    .toLowerCase();
const isEnabled = (button) => {
    return !button.disabled &&
        button.getAttribute('aria-disabled') !== 'true' &&
        button.getAttribute('data-disabled') !== 'true' &&
        button.getAttribute('data-loading') !== 'true';
};
return Array.from(document.querySelectorAll('button, [role="button"]')).find((button) => {
    const text = normalize(button.innerText || button.textContent || '');
    return isEnabled(button) && (
        text === 'da hieu' ||
        text === 'got it' ||
        text === 'ok'
    );
}) || null;
"""

CLICK_ELEMENT_FALLBACK_SCRIPT = """
/* CLICK_ELEMENT_FALLBACK_SCRIPT */
const element = arguments[0];
const rect = element.getBoundingClientRect();
const eventInit = {
    bubbles: true,
    cancelable: true,
    clientX: rect.left + rect.width / 2,
    clientY: rect.top + rect.height / 2,
};
element.dispatchEvent(new MouseEvent('mousemove', eventInit));
element.dispatchEvent(new MouseEvent('mousedown', eventInit));
element.dispatchEvent(new MouseEvent('mouseup', eventInit));
element.click();
element.dispatchEvent(new MouseEvent('click', eventInit));
return true;
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
        .replace(/[\\u0111\\u0110]/g, 'd')
        .trim()
        .toLowerCase();
    return isEnabled(button) && (
        text.includes('post') ||
        text.includes('publish') ||
        text.includes('dang') ||
        text.includes('schedule') ||
        text.includes('len lich')
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

    def upload_scheduled(
        self,
        profile_path,
        video_path,
        schedule_day,
        schedule_hour,
        schedule_minute=0,
        schedule_month=None,
        schedule_year=None,
        title="",
        timeout=180,
    ):
        file_path = Path(video_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        today = datetime.now().date()
        month = int(schedule_month) if schedule_month is not None else today.month
        year = int(schedule_year) if schedule_year is not None else today.year
        if schedule_month is None and int(schedule_day) < today.day:
            month += 1
            if month > 12:
                month = 1
                year += 1

        return self.upload_many(
            profile_path,
            [{
                "file_path": str(file_path),
                "title": title or file_path.stem,
                "schedule": {
                    "day": int(schedule_day),
                    "month": month,
                    "year": year,
                    "hour": int(schedule_hour),
                    "minute": int(schedule_minute),
                },
            }],
            timeout=timeout,
        )[0]

    def upload_many(self, profile_path, upload_items, timeout=180, schedule=None):
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
                item_schedule = item.get("schedule") or schedule
                results.append(
                    self._upload_current_page(browser, item["file_path"], item["title"], timeout, item_schedule)
                )
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
                **({"schedule": item["schedule"]} if item.get("schedule") else {}),
            })
        return normalized

    def _upload_current_page(self, browser, file_path, title, timeout, schedule=None):
        self._hover_upload_button(browser)
        file_input = self._find_video_file_input(browser, timeout=30)
        if not file_input:
            raise RuntimeError("TikTok upload input not found. Profile may not be logged in.")

        file_input.send_file(str(file_path))
        browser.execute_script(FILE_INPUT_CHANGE_SCRIPT, file_input)
        self._dismiss_optional_upload_dialogs(browser)
        self._wait_after_file(browser, timeout)
        self._fill_description(browser, title)
        if schedule:
            self._apply_schedule(browser, schedule)

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

    def _dismiss_optional_upload_dialogs(self, browser):
        for script in (OPTIONAL_CANCEL_BUTTON_SCRIPT, OPTIONAL_GOT_IT_BUTTON_SCRIPT):
            button = browser.execute_script(script)
            if button:
                self._click_visible(browser, button)
                browser.sleep(0.3)

    def _apply_schedule(self, browser, schedule):
        schedule_radio = browser.execute_script(SCHEDULE_RADIO_SCRIPT)
        if not schedule_radio:
            raise RuntimeError("TikTok schedule option not found.")
        self._click_visible(browser, schedule_radio)
        browser.sleep(0.5)

        time_dropdown = browser.execute_script(TIME_DROPDOWN_SCRIPT)
        if not time_dropdown:
            raise RuntimeError("TikTok schedule time dropdown not found.")
        self._click_visible(browser, time_dropdown)
        browser.sleep(0.3)

        hour = browser.execute_script(TIME_OPTION_SCRIPT, str(int(schedule["hour"])), "left")
        if not hour:
            raise RuntimeError("TikTok schedule hour option not found.")
        self._click_picker_option(browser, hour)
        browser.sleep(0.2)

        minute = browser.execute_script(TIME_OPTION_SCRIPT, str(int(schedule["minute"])), "right")
        if not minute:
            raise RuntimeError("TikTok schedule minute option not found.")
        self._click_picker_option(browser, minute)
        browser.sleep(0.3)

        date_dropdown = browser.execute_script(DATE_DROPDOWN_SCRIPT)
        if not date_dropdown:
            raise RuntimeError("TikTok schedule date dropdown not found.")
        self._click_visible(browser, date_dropdown)
        browser.sleep(0.3)

        day = browser.execute_script(
            DATE_OPTION_SCRIPT,
            str(int(schedule["day"])),
            str(int(schedule["month"])),
            str(int(schedule["year"])),
        )
        if not day:
            raise RuntimeError("TikTok schedule day option not found.")
        self._click_picker_option(browser, day)
        browser.sleep(0.5)
        return True

    def _click_picker_option(self, browser, element):
        try:
            return self._click_visible(browser, element)
        except ValueError as error:
            if "Box" not in str(error) and "box" not in str(error):
                raise
            return browser.execute_script(CLICK_ELEMENT_FALLBACK_SCRIPT, element)

    def _click_visible(self, browser, element):
        if hasattr(browser, "click_element"):
            clicked = browser.click_element(element)
            if clicked:
                return clicked
        return element.click()

    def _wait_after_file(self, browser, timeout):
        end_at = time.time() + timeout
        ready_terms = (
            "upload complete",
            "uploaded",
            "successfully uploaded",
            "processing complete",
            "ready to post",
            "video uploaded",
            "tai len hoan tat",
            "tải lên hoàn tất",
        )
        while time.time() < end_at:
            body_text = browser.execute_script("return document.body.innerText || ''") or ""
            lowered = body_text.lower()
            if any(term in lowered for term in ready_terms):
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
