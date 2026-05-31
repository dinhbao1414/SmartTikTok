@echo off
setlocal EnableExtensions

set "SCRIPT_PATH=%~f0"
set "ROOT_DIR=%~dp0.."
set "APP_NAME=SmartTikTok"
set "ENTRYPOINT=app\launcher.py"
set "BUILD_ROOT=build\nuitka"
set "OUTPUT_DIR=build\nuitka\SmartTikTok"
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

if exist "%OUTPUT_DIR%" (
    echo Removing old output folder: %OUTPUT_DIR%
    rmdir /s /q "%OUTPUT_DIR%"
)
if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%" >nul 2>&1

set "ICON_OPTION="
if exist "%ICON_PATH%" (
    python scripts\validate_ico.py "%ICON_PATH%" >nul 2>&1
    if errorlevel 1 (
        echo Invalid icon file, skipping EXE icon: %ICON_PATH%
    ) else (
        set "ICON_OPTION=--windows-icon-from-ico=%ICON_PATH%"
    )
)

echo Building %APP_NAME%.exe with Nuitka...
echo Nuitka jobs: 16
echo Skipping yt-dlp lazy extractor compile to avoid MSVC C1002 heap errors.
python -m nuitka ^
    --standalone ^
    --enable-plugin=pyqt6 ^
    --include-package=app ^
    --include-package=Controller ^
    --include-package=remote_browser ^
    --include-package=websockets ^
    --include-package=pyee ^
    --include-package=psutil ^
    --include-package=numpy ^
    --jobs=16 ^
    --lto=no ^
    --nofollow-import-to=yt_dlp.extractor.lazy_extractors ^
    --windows-console-mode=disable ^
    --output-filename=SmartTikTok.exe ^
    --output-dir=%BUILD_ROOT% ^
    %ICON_OPTION% ^
    "%ENTRYPOINT%"

if not "%errorlevel%"=="0" (
    echo Nuitka build failed.
    popd
    pause
    exit /b 1
)

if exist "%BUILD_ROOT%\launcher.dist" (
    move /y "%BUILD_ROOT%\launcher.dist" "%OUTPUT_DIR%" >nul
)

if not exist "%OUTPUT_DIR%\SmartTikTok.exe" (
    echo Expected EXE not found: %OUTPUT_DIR%\SmartTikTok.exe
    popd
    pause
    exit /b 1
)

if not "%ICON_OPTION%"=="" if exist "logo" robocopy "logo" "%OUTPUT_DIR%\logo" /E >nul
for %%D in (app Controller remote_browser configs) do (
    if exist "%%D" robocopy "%%D" "%OUTPUT_DIR%\%%D" /E >nul
)

if not exist "%OUTPUT_DIR%\remote_browser" (
    echo remote_browser missing from output.
    popd
    pause
    exit /b 1
)
if not exist "%OUTPUT_DIR%\Controller" (
    echo Controller missing from output.
    popd
    pause
    exit /b 1
)
if not exist "%OUTPUT_DIR%\app" (
    echo app package missing from output.
    popd
    pause
    exit /b 1
)

if exist "%BUILD_ROOT%\launcher.build" rmdir /s /q "%BUILD_ROOT%\launcher.build"

echo Build completed.
echo Output folder: %CD%\%OUTPUT_DIR%
popd
pause
