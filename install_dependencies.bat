@echo off
echo ==========================================
echo LinkedIn Scraper - Dependency Installer
echo ==========================================
echo.
echo 1. Installing Python libraries...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error installing requirements. Please check your Python installation.
    pause
    exit /b
)

echo.
echo 2. Installing Pandas and Excel support...
pip install pandas openpyxl
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error installing pandas.
    pause
    exit /b
)

echo.
echo 3. Installing Browser (Playwright Chromium)...
playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error installing browser.
    pause
    exit /b
)

echo.
echo ==========================================
echo ✅ Installation Complete!
echo ==========================================
echo.
echo You can now proceed with Step 1 in README.md (Create Session).
echo.
pause
