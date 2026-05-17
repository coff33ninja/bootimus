
# Scripts

This directory contains build and setup scripts for various platforms and components of Bootimus.

## Quick Reference

| Script | Platform | Purpose |
|--------|----------|---------|
| `build-windows.bat` | Windows | Build and run Bootimus on Windows |
| `package-windows.bat` | Windows | Package Bootimus for Windows distribution |
| `build-bootloaders.sh` | Unix/Linux | Build bootloader images |
| `build-alpine-nbd.sh` | Unix/Linux | Build Alpine Linux NBD server |
| `build-alpine-nbd-docker.sh` | Docker | Build Alpine NBD server in Docker |
| `build-arch-nbd.sh` | Unix/Linux | Build Arch Linux NBD server |
| `build-custom-alpine.sh` | Unix/Linux | Build custom Alpine Linux image |
| `build-secureboot-set.sh` | Unix/Linux | Build Secure Boot certificate set |
| `download-alpine.sh` | Unix/Linux | Download Alpine Linux ISO |
| `generate-signing-key.sh` | Unix/Linux | Generate signing keys for secure boot |
| `Dockerfile.alpine-nbd` | Docker | Docker configuration for Alpine NBD build |

## Windows Scripts

### `build-windows.bat`

Build and optionally run Bootimus on Windows.

> **PowerShell users:** run `.\build-windows.bat` (PowerShell does not execute `.bat` files from the current directory by default).

---
```
Usage: .\build-windows.bat [run] [options]

Commands:
  run              Build then start the server

Options:
  --http PORT      HTTP server port (default: 9090)
  --admin PORT     Admin UI port   (default: 9091)
  --tftp PORT      TFTP port       (default: app default 69)
  --nbd PORT       NBD port        (default: app default 10809)
  --proxy-dhcp     Enable built-in proxyDHCP (enabled by default;
                   requires admin privileges to bind UDP/67)
  --smb PORT       Enable SMB share for Windows installs (enabled by default,
                   port 445; requires smbd.exe in PATH)
  --reset-admin    Reset admin password on startup
```
---
#### Examples

---
```bat
:: Build and run with all defaults (proxy DHCP + SMB enabled)
.\build-windows.bat run

:: With custom HTTP port only
.\build-windows.bat run --http 9090

:: Build and run with custom ports
.\build-windows.bat run --http 9090 --admin 9091 --tftp 69 --nbd 10809

:: Build, run, and reset admin password on first run
.\build-windows.bat run --http 9090 --reset-admin
```
---
#### Requirements

- Go 1.24+
- Zig (for CGO/SQLite) — optional, skips to default CC if not found

#### Feature Prerequisites

| Feature | Enabling flag | Prerequisites |
|---------|---------------|---------------|
| Proxy DHCP | `--proxy-dhcp` | Admin/root privileges (binds UDP port 67) |
| Windows SMB | `--smb [PORT]` | `smbd.exe` in PATH ([Samba for Windows](https://wiki.samba.org/index.php/Installing_Samba_on_Windows)) |
| WIM patching | automatic detection | `wimlib-imagex.exe` in PATH or under `%ProgramFiles%\wimlib\` ([wimlib](https://wimlib.net/)) |

If a feature shows as "Disabled" or "Unavailable" in the admin UI, check the prerequisites above and restart with the appropriate flag.

### `package-windows.bat`

Package Bootimus for Windows distribution. Prepares the built artifacts for deployment or release.

## Unix/Linux Build Scripts

### `build-bootloaders.sh`

Builds bootloader images for network boot scenarios. Creates UEFI and BIOS compatible bootloaders.

### `build-alpine-nbd.sh`

Builds an Alpine Linux-based NBD (Network Block Device) server. The NBD server provides network-accessible block device functionality for remote disk operations.

### `build-arch-nbd.sh`

Builds an Arch Linux-based NBD (Network Block Device) server, similar to the Alpine variant but based on Arch Linux distribution.

### `build-custom-alpine.sh`

Creates a custom Alpine Linux image with specific configurations and packages for Bootimus requirements.

### `build-secureboot-set.sh`

Generates Secure Boot certificate and key sets required for secure boot functionality.

### `download-alpine.sh`

Downloads the Alpine Linux ISO image(s) needed for building NBD servers and custom Alpine images.

### `generate-signing-key.sh`

Generates cryptographic signing keys used for secure operations and code signing within Bootimus.

## Docker Scripts

### `build-alpine-nbd-docker.sh`

Builds the Alpine NBD server within a Docker container. Useful for containerized builds or CI/CD pipelines.

### `Dockerfile.alpine-nbd`

Docker configuration file that defines the build process and runtime environment for the Alpine NBD server container.

## General Notes

- Shell scripts (`.sh`) require a Unix/Linux environment or WSL on Windows
- Batch files (`.bat`) are Windows-specific
- Docker scripts can run on any system with Docker installed