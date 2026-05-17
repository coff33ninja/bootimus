@echo off
setlocal enabledelayedexpansion

set ROOT=%~dp0..
set VERSION_FILE=%ROOT%\VERSION
set /p VERSION=<%VERSION_FILE%
set BINARY=%ROOT%\dist\bootimus-v%VERSION%-windows-amd64.exe
set STAGING=%TEMP%\bootimus-v%VERSION%-windows-amd64
set ZIPFILE=%ROOT%\dist\bootimus-v%VERSION%-windows-amd64.zip

echo ============================================
echo Bootimus Windows Package v%VERSION%
echo ============================================

if not exist "%BINARY%" (
    echo ERROR: Binary not found at %BINARY%
    echo Run build-windows.bat first.
    exit /b 1
)

echo [1/4] Creating staging directory...
if exist "%STAGING%" rmdir /s /q "%STAGING%"
mkdir "%STAGING%" >nul 2>&1

echo [2/4] Copying files...
copy "%BINARY%" "%STAGING%\bootimus.exe" >nul
copy "%ROOT%\VERSION" "%STAGING%\" >nul
copy "%ROOT%\LICENSE" "%STAGING%\" >nul
copy "%ROOT%\scripts\build-windows.bat" "%STAGING%\" >nul
copy "%ROOT%\scripts\README.md" "%STAGING%\README.md" >nul

echo [3/4] Creating zip archive...
powershell -NoProfile -Command "Compress-Archive -Path '%STAGING%\*' -DestinationPath '%ZIPFILE%' -Force"
if !errorlevel! neq 0 (
    echo ERROR: Failed to create zip archive.
    exit /b 1
)

echo [4/4] Cleaning up...
rmdir /s /q "%STAGING%"

echo.
echo Package created: %ZIPFILE%
for %%f in ("%ZIPFILE%") do echo Size: %%~zf bytes
echo.
echo Contents:
echo   bootimus.exe  - Windows binary
echo   VERSION       - version file
echo   LICENSE       - license
echo   build-windows.bat - build script
echo   README.md     - build script docs
echo.
echo To extract: 7z x "%ZIPFILE%"
