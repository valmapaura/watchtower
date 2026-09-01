@echo off
REM ============================================================
REM  Watchtower - one-click launcher
REM  Double-click this file to start the server.
REM  A window will open; leave it open while you use Watchtower.
REM  Close the window (or press Ctrl+C) to stop the server.
REM ============================================================
setlocal
cd /d "%~dp0"

title Watchtower

echo.
echo  ============================================
echo    Watchtower - starting your camera server
echo  ============================================
echo.
echo  Once it's ready, open this in your browser:
echo      http://localhost:3000
echo.
echo  Keep this window open while you use Watchtower.
echo  Close it (or press Ctrl+C) to stop the server.
echo.

REM Start the backend + frontend together.
REM The npm script lives in client/web and starts both processes.
REM We use dev mode so it works without a prior build step.
pushd "%~dp0client\web"
call npm run dev:all
popd

echo.
echo  Watchtower has stopped.
echo  You can close this window now.
echo.
pause
