# Automation Rules

Read this before editing any browser automation, TikTok upload, profile launch,
or file-upload workflow.

## Required Browser Stack

- Always use the local `remote_browser` library for browser automation.
- Use `Controller/BrowserController.py` and `ChromeProfileBrowser` for Chrome
  profile launch/ownership.
- Use `remote_browser` APIs such as `find_element`, `execute_script`, CDP calls,
  and `WebElement.send_file(file_path)` for browser control and file upload.

## Forbidden Stack

- Do not use Selenium.
- Do not use chromedriver.
- Do not use Selenium Wire.
- Do not use GoLogin or GPM Login for this stage.

## Current Upload Rule

TikTok Studio upload must keep using `remote_browser` only. If a selector or
upload flow changes, update `tiktok_uploader.py` using `remote_browser` APIs and
add or update tests in `tests/test_tiktok_uploader.py`.

For visible TikTok buttons such as Post/Publish, prefer
`browser.click_element(element)` so the click path goes through `remote_browser`
mouse movement. Do not click those buttons with direct JavaScript unless it is a
documented fallback.

For video file selection, keep using `WebElement.send_file(file_path)` because
clicking the file picker opens an OS dialog that automation cannot control
reliably.
