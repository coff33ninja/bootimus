@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || exit /b 1
set "PROJECT_DIR=%CD%"
popd

cd /d "%PROJECT_DIR%" || exit /b 1

if not exist VERSION (
    echo ERROR: VERSION file not found
    exit /b 1
)

set /p VERSION=<VERSION
if "%VERSION%"=="" set VERSION=dev

set "DIST_DIR=%PROJECT_DIR%\dist"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

set "CC=zig cc"
set "CGO_ENABLED=1"
set "LDFLAGS=-w -s -X bootimus/internal/server.Version=%VERSION%"
set "OUTFILE=%DIST_DIR%\bootimus-v%VERSION%-windows-amd64.exe"

set "DO_RUN="
set "RESET_ADMIN="
set "HTTP_PORT=9090"
set "ADMIN_PORT=9091"
set "TFTP_PORT="
set "NBD_PORT="
set "SMB_PORT=445"
set "PROXY_DHCP=1"

:parse_args
if "%~1"=="run" (
    set "DO_RUN=1"
    shift
    goto parse_args
)
if "%~1"=="--http" (
    set "HTTP_PORT=%~2"
    shift & shift
    goto parse_args
)
if "%~1"=="--admin" (
    set "ADMIN_PORT=%~2"
    shift & shift
    goto parse_args
)
if "%~1"=="--tftp" (
    set "TFTP_PORT=%~2"
    shift & shift
    goto parse_args
)
if "%~1"=="--nbd" (
    set "NBD_PORT=%~2"
    shift & shift
    goto parse_args
)
if "%~1"=="--proxy-dhcp" (
    set "PROXY_DHCP=1"
    shift
    goto parse_args
)
if "%~1"=="--smb" (
    set "SMB_PORT=%~2"
    shift & shift
    goto parse_args
)
if "%~1"=="--reset-admin" (
    set "RESET_ADMIN=1"
    shift
    goto parse_args
)
if not "%~1"=="" (
    echo Unknown argument: %~1
    echo Usage: %~nx0 [run] [--http PORT] [--admin PORT] [--tftp PORT] [--nbd PORT] [--proxy-dhcp] [--smb PORT] [--reset-admin]
    exit /b 1
)

echo ============================================
echo Bootimus Build Script for Windows
echo ============================================
echo Version:  %VERSION%
echo Output:   %OUTFILE%
echo -----------------------------------------------------------
where zig >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Compiler:  zig cc
) else (
    echo Compiler:  default CC (zig not found)
    set "CC="
)
echo -----------------------------------------------------------
if defined DO_RUN (
    if defined HTTP_PORT set "CUSTOM_PORTS=1" & echo   HTTP:  !HTTP_PORT!
    if defined ADMIN_PORT set "CUSTOM_PORTS=1" & echo   Admin: !ADMIN_PORT!
    if defined TFTP_PORT set "CUSTOM_PORTS=1" & echo   TFTP:  !TFTP_PORT!
    if defined NBD_PORT set "CUSTOM_PORTS=1" & echo   NBD:   !NBD_PORT!
    if defined SMB_PORT set "CUSTOM_PORTS=1" & echo   SMB:   !SMB_PORT!
    if not defined CUSTOM_PORTS echo   Ports: All defaults (use flags to override)
    if defined RESET_ADMIN echo   Admin password will be reset
    echo -----------------------------------------------------------
)
echo.

echo [1/4] Syncing distro profiles...
if exist distro-profiles.json (
    copy /y distro-profiles.json internal\profiles\distro-profiles.json >nul
)
if exist tools-profiles.json (
    copy /y tools-profiles.json internal\tools\tools-profiles.json >nul
)

echo [2/4] Building binary...
go build -ldflags="%LDFLAGS%" -o "%OUTFILE%" .
if %ERRORLEVEL% neq 0 (
    echo.
    echo BUILD FAILED
    exit /b 1
)

for %%F in ("%OUTFILE%") do set "FILESIZE=%%~zF"
set /a "FILESIZE_MB=!FILESIZE! / (1024*1024)"

echo.
echo Build successful!
echo   File: %OUTFILE%
echo   Size: !FILESIZE_MB! MB

echo.
echo [3/4] Checking tools...

set "TOOLS_DIR=%PROJECT_DIR%\tools"
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

set "PATH=%TOOLS_DIR%;%PATH%"

if not defined DO_RUN (
    echo.
    echo To build and run: .\%~nx0 run
    echo To customize ports: .\%~nx0 run --http 9090 --admin 9091
    goto :eof
)
echo.
echo [4/4] Starting server...
echo.
echo ============================================
echo  BOOTIMUS v%VERSION%
echo ============================================
if defined HTTP_PORT echo  Ports:   HTTP=!HTTP_PORT!
if defined ADMIN_PORT echo           Admin=!ADMIN_PORT!
if defined TFTP_PORT echo           TFTP=!TFTP_PORT!
if defined NBD_PORT echo           NBD=!NBD_PORT!
if defined SMB_PORT echo           SMB=!SMB_PORT!
if defined PROXY_DHCP echo  Features: Proxy DHCP, SMB
if defined ADMIN_PORT echo  Admin:   http://localhost:!ADMIN_PORT!
if not defined ADMIN_PORT echo  Admin:   http://localhost:8081
echo ============================================
echo.

set "SERVE_ARGS="
if defined HTTP_PORT set "SERVE_ARGS=!SERVE_ARGS! --http-port !HTTP_PORT!"
if defined ADMIN_PORT set "SERVE_ARGS=!SERVE_ARGS! --admin-port !ADMIN_PORT!"
if defined TFTP_PORT set "SERVE_ARGS=!SERVE_ARGS! --tftp-port !TFTP_PORT!"
if defined NBD_PORT set "SERVE_ARGS=!SERVE_ARGS! --nbd-port !NBD_PORT!"
if defined PROXY_DHCP set "SERVE_ARGS=!SERVE_ARGS! --proxy-dhcp"
if defined SMB_PORT set "SERVE_ARGS=!SERVE_ARGS! --windows-smb --windows-smb-port !SMB_PORT!"
if defined RESET_ADMIN set "SERVE_ARGS=!SERVE_ARGS! --reset-admin-password"

"%OUTFILE%" serve !SERVE_ARGS!

endlocal
