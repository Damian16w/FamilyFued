@echo off
title Family Feud Launcher
cd /d "%~dp0"
echo Starting Family Feud Game System...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python and add to PATH.
    pause
    exit /b 1
)

REM Install backend dependencies if needed
echo Installing backend requirements...
cd backend
pip install -r requirements.txt >nul 2>&1
cd ..

REM Check for .env file
if not exist "discord_bot\.env" (
    echo WARNING: discord_bot\.env not found. Create it with DISCORD_BOT_TOKEN=your_token
    echo.
)

REM Launch Flask backend from its folder
echo Starting Flask backend...
start "Family Feud Backend" cmd /k "cd /d "%~dp0backend" && python app.py"

timeout /t 2 /nobreak >nul

REM Launch Discord bot from its folder
echo Starting Discord bot...
start "Family Feud Bot" cmd /k "cd /d "%~dp0discord_bot" && python bot.py"

echo.
echo Both services launched.
echo Host panel: http://localhost:5000/host
echo Player screen: http://localhost:5000/player
echo.
echo Close the two windows to stop the game.
pause