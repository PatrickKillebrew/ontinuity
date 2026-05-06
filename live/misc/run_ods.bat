@echo off
REM ============================================================
REM  ONTINUITY DRIVING SYSTEM - Session Runner
REM  Double-click this instead of typing the python command.
REM  Logs everything to sessions\ and syncs to GitHub after run.
REM ============================================================

REM Create sessions folder if it doesn't exist
if not exist C:\donkeycar\sessions mkdir C:\donkeycar\sessions

REM Generate timestamp using PowerShell (works on all Windows 11 builds)
for /f "tokens=*" %%I in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set timestamp=%%I
set logfile=C:\donkeycar\sessions\session_%timestamp%.txt

echo.
echo [RUN] Ontinuity Driving System
echo [RUN] Session log: %logfile%
echo [RUN] Make sure simulator is running with track loaded
echo [RUN] Press Ctrl+C to end session
echo.

REM Run the brainstem - unbuffered (-u) so output streams in real time
REM Tee-Object writes to terminal AND log file simultaneously
powershell -Command "python -u C:\donkeycar\ods_phase1_v5.py 2>&1 | Tee-Object -FilePath '%logfile%'" -OutputFormat UTF8

echo.
echo [RUN] Session ended.
echo [RUN] Syncing session log to GitHub...
python C:\donkeycar\push_to_github.py "%logfile%"
echo.
echo [RUN] Done. Log available at:
echo [RUN] https://github.com/PatrickKillebrew/ontinuity/blob/main/live/sessions/session_%timestamp%.txt
echo.
pause
