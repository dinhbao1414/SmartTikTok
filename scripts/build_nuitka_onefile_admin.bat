@echo off
setlocal EnableExtensions

set "SCRIPT_PATH=%~f0"
set "ROOT_DIR=%~dp0.."
set "APP_NAME=SmartTikTok"
set "ENTRYPOINT=app\launcher.py"
set "OUTPUT_DIR=build\nuitka-onefile"
set "ICON_PATH=logo\output.ico"

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Requesting administrator permission...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%SCRIPT_PATH%' -Verb RunAs -WorkingDirectory '%ROOT_DIR%'"
    exit /b
)

pushd "%ROOT_DIR%" || exit /b 1

if not exist "%ENTRYPOINT%" (
    echo Entry point not found: %ENTRYPOINT%
    popd
    exit /b 1
)

python -c "import nuitka" >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Nuitka is not installed in this Python environment.
    echo Install it first:
    echo python -m pip install nuitka ordered-set zstandard
    popd
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%" >nul 2>&1
echo Preserving writable app data in: %OUTPUT_DIR%
if exist "%OUTPUT_DIR%\SmartTikTok.exe" del /f /q "%OUTPUT_DIR%\SmartTikTok.exe"
if exist "%OUTPUT_DIR%\SmartTikTok.runtime" rmdir /s /q "%OUTPUT_DIR%\SmartTikTok.runtime"
if exist "%OUTPUT_DIR%\launcher.build" rmdir /s /q "%OUTPUT_DIR%\launcher.build"
if exist "%OUTPUT_DIR%\launcher.dist" rmdir /s /q "%OUTPUT_DIR%\launcher.dist"
if exist "%OUTPUT_DIR%\launcher.onefile-build" rmdir /s /q "%OUTPUT_DIR%\launcher.onefile-build"

set "ICON_OPTION="
if exist "%ICON_PATH%" (
    python scripts\validate_ico.py "%ICON_PATH%" >nul 2>&1
    if errorlevel 1 (
        echo Invalid icon file, skipping EXE icon: %ICON_PATH%
    ) else (
        set "ICON_OPTION=--windows-icon-from-ico=%ICON_PATH%"
    )
)

echo Building onefile %APP_NAME%.exe with Nuitka...
echo Nuitka jobs: 16
echo Cached runtime files and writable app data will be kept next to SmartTikTok.exe.
echo Skipping yt-dlp lazy extractor compile to avoid MSVC C1002 heap errors.
python -m nuitka ^
    --onefile ^
    --standalone ^
    --enable-plugin=pyqt6 ^
    --include-package=app ^
    --include-package=Controller ^
    --include-package=remote_browser ^
    --include-package=websockets ^
    --include-package=pyee ^
    --include-package=psutil ^
    --include-package=numpy ^
    --include-data-dir=logo=logo ^
    --include-data-dir=configs=configs ^
    --jobs=16 ^
    --lto=no ^
    --nofollow-import-to=yt_dlp.extractor.lazy_extractors ^
    --onefile-cache-mode=cached ^
    --onefile-tempdir-spec="SmartTikTok.runtime" ^
    --windows-console-mode=disable ^
    --output-filename=SmartTikTok.exe ^
    --output-dir=%OUTPUT_DIR% ^
    %ICON_OPTION% ^
    "%ENTRYPOINT%"

if not "%errorlevel%"=="0" (
    echo Nuitka onefile build failed.
    popd
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%\SmartTikTok.exe" (
    echo Expected EXE not found: %OUTPUT_DIR%\SmartTikTok.exe
    popd
    pause
    exit /b 1
)

if exist "%OUTPUT_DIR%\launcher.build" rmdir /s /q "%OUTPUT_DIR%\launcher.build"
if exist "%OUTPUT_DIR%\launcher.dist" rmdir /s /q "%OUTPUT_DIR%\launcher.dist"
if exist "%OUTPUT_DIR%\launcher.onefile-build" rmdir /s /q "%OUTPUT_DIR%\launcher.onefile-build"

echo Build completed.
echo Output file: %CD%\%OUTPUT_DIR%\SmartTikTok.exe
popd
pause
