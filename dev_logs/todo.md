# Todo

## Completed
- [x] `syscall.Statfs_t` compilation — split into `stats_linux.go` / `stats_windows.go`
- [x] `syscall.SetsockoptInt` type mismatch — split into `proxydhcp_unix.go` / `proxydhcp_windows.go`
- [x] Build script `scripts/build-windows.bat` (zig cc, `run`, `--http`, `--admin`, `--tftp`, `--nbd`, `--smb`, `--reset-admin`)
- [x] Config path — added `%ProgramData%\bootimus\` on Windows
- [x] ANSI colors — disabled on Windows
- [x] SMB manager — split into `manager_unix.go` / `manager_windows.go`
- [x] WIM — reviewed, already cross-platform
- [x] External tool paths — `internal/toolpath` helper for wimlib-imagex, 7z, bsdtar on Windows
- [x] Port binding errors — now include flag suggestions (e.g. "use --http-port to change")
- [x] ANSI colors — now uses Win32 `SetConsoleMode` with `ENABLE_VIRTUAL_TERMINAL_PROCESSING` instead of stripping colors
- [x] Config path — `%ProgramData%\bootimus\` on Windows (already done in root.go)
- [x] `serve` test on Windows ✅
- [x] Windows portable packaging — `scripts/package-windows.bat` + zip in `dist/`
- [x] GitHub Actions CI for Windows — `.github/workflows/ci-windows.yml`
- [x] Disk-full error detection — `isDiskFull` helper in extractor + frontend persistent alerts
- [x] Feature flags — `--proxy-dhcp` default, `--windows-smb` passthrough in bat script
- [x] Native Windows SMB — `net share` implementation in `manager_windows.go`
- [x] Bat script wimlib-download step removed (now auto-downloaded from Go at runtime)
- [x] wimlib auto-download — `ensureWimlib()` fetches latest version from wimlib.net, caches to `{data-dir}/tools/wimlib-imagex.exe`
- [x] `toolpath.AddToolsDir()` — register custom tool dirs at runtime (used for auto-downloaded wimlib)
- [x] Admin UI messages — updated wimlib/SMB patcher status to reflect auto-download

## Remaining

- [ ] Test with actual PXE clients from Windows host
- [ ] Rebuild iPXE binaries with `CONSOLE_FRAMEBUFFER`, `IMAGE_PNG`, `COLOUR_CMD`, `CPAIR_CMD` via GitHub Actions workflow (`.github/workflows/build-ipxe.yml`), then:
  - Enable `colour`/`cpair` commands for menu color customization
  - Add background image support via `console --picture <url>.png`
  - Replace `bootloaders/default/` binaries with custom build
