@echo off
SETLOCAL EnableDelayedExpansion

REM ===================================
REM Video Organizer Runner
REM Supports both manual and context menu execution
REM ===================================

REM Configuration
SET "SCRIPT_DIR=%~dp0"
SET "LOCK_FILE=%TEMP%\video-organizer.lock"
SET "PID_FILE=%TEMP%\video-organizer.pid"

REM ===================================
REM Detect Execution Mode
REM ===================================
SET "TARGET_DIR="
IF NOT "%~1"=="" (
    IF EXIST "%~1\." (
        REM Context menu mode - %1 is the folder path
        SET "TARGET_DIR=%~1"
    )
)

IF NOT DEFINED TARGET_DIR (
    REM Manual mode - use parent directory (backward compatible)
    PUSHD "%SCRIPT_DIR%"
    CD ..
    SET "TARGET_DIR=%CD%"
    POPD
)

REM ===================================
REM Single Instance Check
REM ===================================
IF EXIST "%LOCK_FILE%" (
    REM Read PID from lock file
    SET /P LOCK_PID=<"%PID_FILE%" 2>NUL

    REM Check if process still running
    tasklist /FI "PID eq !LOCK_PID!" 2>NUL | find "!LOCK_PID!" >NUL
    IF !ERRORLEVEL! EQU 0 (
        REM Process still running - show message and exit
        powershell -WindowStyle Hidden -command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Video Organizer is already running.^n^nPlease wait until the current session finishes before starting a new one.','Video Organizer Already Running','OK','Warning') | Out-Null"
        EXIT /B 1
    ) ELSE (
        REM Stale lock - clean up
        DEL "%LOCK_FILE%" "%PID_FILE%" 2>NUL
    )
)

REM ===================================
REM Create Lock with PID
REM ===================================
REM Get current process PID using temporary PowerShell
FOR /F %%I IN ('powershell -command "$pid"') DO SET MY_PID=%%I
IF NOT DEFINED MY_PID SET MY_PID=%RANDOM%
ECHO %MY_PID% > "%PID_FILE%"
ECHO 1 > "%LOCK_FILE%"

REM ===================================
REM Change to Target Directory
REM ===================================
PUSHD "%TARGET_DIR%"

REM ===================================
REM Start Server
REM ===================================
echo.
echo ===================================
echo Video Organizer Starting
echo ===================================
echo Serving from: %CD%
echo.

REM Commented out gallery update (as in original)
echo Updating gallery...
:: python video_gallery.py

echo Starting local server...
start "" "http://localhost:8001/video-organizer.html"
python "%SCRIPT_DIR%server.py"

REM ===================================
REM Cleanup on Exit
REM ===================================
POPD
DEL "%LOCK_FILE%" "%PID_FILE%" 2>NUL

EXIT /B 0
