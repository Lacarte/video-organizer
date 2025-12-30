@echo off
REM ===================================
REM Video Organizer - Context Menu Uninstaller
REM Removes "Organize Videos" from Windows Explorer folder context menu
REM ===================================

REM Check for admin privileges
net session >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ===================================
echo Uninstalling Context Menu Entry
echo ===================================
echo.

REM Remove folder icon context menu
reg query "HKCR\Directory\shell\OrganizeVideos" >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    reg delete "HKCR\Directory\shell\OrganizeVideos" /f
    echo Removed folder icon context menu.
) ELSE (
    echo Folder icon context menu not found.
)

REM Remove folder background context menu
reg query "HKCR\Directory\Background\shell\OrganizeVideos" >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    reg delete "HKCR\Directory\Background\shell\OrganizeVideos" /f
    echo Removed folder background context menu.
) ELSE (
    echo Folder background context menu not found.
)

echo.
echo ===================================
echo SUCCESS!
echo ===================================
echo Context menu entries removed.
echo.

pause
