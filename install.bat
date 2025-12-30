@echo off
REM ===================================
REM Video Organizer - Context Menu Installer
REM Adds "Organize Videos" to Windows Explorer folder context menu
REM ===================================

REM Check for admin privileges
net session >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM Get absolute script directory (remove trailing backslash)
SET "SCRIPT_DIR=%~dp0"
SET "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo.
echo ===================================
echo Installing Context Menu Entry
echo ===================================
echo Location: %SCRIPT_DIR%
echo.

REM Add registry entries for folder icon context menu
reg add "HKCR\Directory\shell\OrganizeVideos" /ve /d "Organize Videos" /f
reg add "HKCR\Directory\shell\OrganizeVideos" /v "Icon" /d "%SystemRoot%\System32\shell32.dll,167" /f
reg add "HKCR\Directory\shell\OrganizeVideos\command" /ve /d "cmd.exe /c \"\"%SCRIPT_DIR%\runner.bat\" \"%%V\"\"" /f

REM Add registry entries for folder background context menu
reg add "HKCR\Directory\Background\shell\OrganizeVideos" /ve /d "Organize Videos" /f
reg add "HKCR\Directory\Background\shell\OrganizeVideos" /v "Icon" /d "%SystemRoot%\System32\shell32.dll,167" /f
reg add "HKCR\Directory\Background\shell\OrganizeVideos\command" /ve /d "cmd.exe /c \"\"%SCRIPT_DIR%\runner.bat\" \"%%V\"\"" /f

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================
    echo SUCCESS!
    echo ===================================
    echo Context menu installed successfully.
    echo.
    echo Right-click any folder and select "Organize Videos"
    echo to launch the Video Organizer for that folder.
    echo.
) ELSE (
    echo.
    echo ERROR: Failed to install context menu.
    echo Error code: %ERRORLEVEL%
    echo.
)

pause
