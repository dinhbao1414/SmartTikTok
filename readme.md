# YouTube To TikTok Upload Flow

1. Run `python gui.py`.
2. Create Chrome profiles.
3. Open each profile and log in to TikTok manually.
4. Assign one YouTube channel URL to each profile.
5. Choose mode `shorts` or `videos`.
6. Set poll interval, download folder, and Telegram bot settings.
7. Press `Run`.
8. Watch `Logs` tab for scan, download, upload, and Telegram report status.

The app uses Chrome through `remote_browser`. It does not use Selenium,
ChromeDriver, Go Login, or GPM Login in this stage.
