# Completed

## 2026-05-16 — Windows Compilation Fixes

### Problem
The project had Linux-only `syscall` usage in two packages that prevented compilation on Windows:
1. `internal/sysstats/stats.go` — `syscall.Statfs_t` / `syscall.Statfs()` (Linux filesystem stats)
2. `internal/proxydhcp/proxydhcp.go` — `syscall.SetsockoptInt(int(fd), ...)` (type mismatch on Windows)

### Changes

**`internal/sysstats/stats.go`**
- Removed `syscall` import and `getDiskStatsManual` function body (moved to platform files)
- `GetMonitoredPaths()` now uses `SystemDrive` on Windows vs `/` on Linux

**`internal/sysstats/stats_linux.go`** (new)
- `//go:build linux`
- `getDiskStatsManual` using `syscall.Statfs_t` (original implementation)

**`internal/sysstats/stats_windows.go`** (new)
- `//go:build windows`
- `getDiskStatsManual` using `windows.GetDiskFreeSpaceEx` from `golang.org/x/sys/windows`

**`internal/proxydhcp/proxydhcp.go`**
- Removed `syscall` import and `enableBroadcast` function (moved to platform files)

**`internal/proxydhcp/proxydhcp_unix.go`** (new)
- `//go:build !windows`
- `enableBroadcast` using `syscall.SetsockoptInt(int(fd), ...)`

**`internal/proxydhcp/proxydhcp_windows.go`** (new)
- `//go:build windows`
- `enableBroadcast` using `windows.SetsockoptInt(windows.Handle(fd), ...)`

**`scripts/build-windows.bat`** (new)
- Windows build script using zig cc for CGO/SQLite
- Versioned output to `dist/` folder (e.g. `bootimus-v0.1.67-windows-amd64.exe`)
- Auto-falls back to default CC if zig not found

**`dist/`**
- First Windows binary: `bootimus-v0.1.67-windows-amd64.exe` (30.5 MB)

### Verification
- `go build ./...` — passes on Windows
- `go vet ./...` — passes on Windows
- Binary runs and shows `--help` output correctly

---

## 2026-05-16 — Windows Runtime Fixes + Serve Test

### Config Path (`cmd/root.go`)
- Added `%ProgramData%\bootimus\` as a config path on Windows (falls back to `/etc/bootimus/` on Linux)
- Added `"runtime"` and `"path/filepath"` imports

### ANSI Colors (`cmd/serve.go`)
- Changed color constants to vars cleared at init on Windows
- Banner displays cleanly without escape code garbage

### SMB Manager (`internal/smb/manager.go`)
- Added explicit error on Windows: "SMB server is not supported on Windows"
- Prevents confusing "smbd not found in PATH" message

### Serve Test
Ran `bootimus serve --http-port 9090 --admin-port 9091` on Windows — **all clean, zero errors:**
- Banner renders correctly (no ANSI garbage)
- SQLite database initializes and migrations run
- Admin auth enabled, password generated
- 29 distro profiles seeded
- 6 tools seeded
- HTTP server (9090), TFTP server (69), Admin server (9091), NBD server (10809) all start
- Scheduler loads with 0 active tasks

---

## 2026-05-16 — Windows External Tool Path Resolution

### Problem
`wimlib-imagex`, `7z`, and `bsdtar` are not in PATH by default on Windows, causing features like WIM manipulation, driver injection, and bsdtar-based ISO extraction to silently fail.

### Changes

**`internal/toolpath/toolpath.go`** (new)
- Cross-platform `LookPath` that checks PATH first, then searches common Windows install directories
- 7z: `%ProgramFiles%\7-Zip\`, `%ProgramFiles(x86)%\7-Zip\`, `%SystemRoot%\System32\`
- wimlib-imagex: `%ProgramFiles%\wimlib\`, `%ProgramFiles(x86)%\wimlib\`
- bsdtar: `%ProgramFiles%\bsdtar\`, `%ProgramFiles(x86)%\bsdtar\`, `%ProgramFiles%\libarchive\`, `%SystemRoot%\System32\`

**`internal/wim/wim.go`**
- `IsAvailable()`, `NewManager()`, and `7z` command now use `toolpath.LookPath` instead of `exec.LookPath`

**`internal/extractor/extractor.go`**
- bsdtar lookup now uses `toolpath.LookPath` instead of `exec.LookPath`

### Verification
- `go build ./...` — passes on Windows
- `go vet ./...` — passes on Windows

---

## 2026-05-16 — Helpful Port Binding Error Messages

### Changes
All port binding failures now include which port failed and how to change it:

| File | Before | After |
|------|--------|-------|
| `internal/server/server.go:825` | `TFTP server failed: ...` | `TFTP server failed on port 69: ... (use --tftp-port to change)` |
| `internal/server/server.go:1018` | `HTTP server failed: ...` | `HTTP server failed on port 8080: ... (use --http-port to change)` |
| `internal/server/server.go:1041` | `Admin server failed: ...` | `Admin server failed on port 8081: ... (use --admin-port to change)` |
| `internal/nbd/server.go:59` | `failed to start NBD server: ...` | `failed to start NBD server on port 10809: ... (use --nbd-port to change)` |
| `internal/proxydhcp/proxydhcp.go:55` | `needs root or CAP_NET_BIND_SERVICE` | `needs admin or --proxy-dhcp disabled` |

---

## 2026-05-16 — SMB Manager Platform Split + WIM Review

### SMB Manager (`internal/smb/`)
Split into platform-specific files with `//go:build` tags:

**`manager.go`** (common)
- Struct, NewManager, share management, SanitizeShareName, config/smbDir helpers, ensureStateDirs, writeConfig

**`manager_unix.go`** (`//go:build !windows`)
- Start(), Reload(), Stop() — spawns/manages smbd subprocess

**`manager_windows.go`** (`//go:build windows`)
- Start() returns clear error ("not supported on Windows")
- Reload() and Stop() are no-ops

### WIM (`internal/wim/`)
- Reviewed: fully cross-platform already. All imports are standard Go, `toolpath.LookPath` handles both OSes, `wimlib-imagex` works on Windows. No build tags needed.

---

## 2026-05-16 — Windows Portable Packaging

### `scripts/package-windows.bat` (new)
Creates a portable zip archive in `dist/` containing:
- `bootimus.exe` — built binary (30 MB)
- `build-windows.bat` — build/run script
- `README.md` — usage docs
- `LICENSE` — project license
- `VERSION` — version file

Output: `dist/bootimus-v0.1.67-windows-amd64.zip` (12 MB)

---

## 2026-05-16 — GitHub Actions CI for Windows

### `.github/workflows/ci-windows.yml` (new)
Windows CI workflow that runs on push/PR to `main` and manually:

| Step | What |
|------|------|
| Setup Go 1.24 | `actions/setup-go@v5` |
| Setup Zig | `goto-bus-stop/setup-zig@v2` — C compiler for CGO/SQLite |
| Cache | Go module cache via `actions/cache@v4` |
| Build | `go build` with `CC: zig cc`, version injected from `VERSION` |
| Vet | `go vet ./...` |
| Test | `go test ./... -v -count=1` with `CC: zig cc` |
| Upload | Binary uploaded as `bootimus-windows-amd64` artifact |

Note: untested (requires push to GitHub to validate).

---

## 2026-05-16 — Win32 Console API for ANSI Colors

### `cmd/serve_windows.go` (new)
Replaced the old `runtime.GOOS == "windows"` color-stripping approach with proper Win32 console API:

- Calls `GetStdHandle(STD_OUTPUT_HANDLE)` → `GetConsoleMode` → `SetConsoleMode` with `ENABLE_VIRTUAL_TERMINAL_PROCESSING` flag
- Falls back gracefully: if stdout is redirected (no console handle) or API fails, colors are cleared as before
- Unix systems unaffected (ANSI works natively)

### `cmd/serve.go`
- Removed `"runtime"` import and the Windows `init()` that cleared color vars

---

## 2026-05-16 — Disk-Full Error Detection + Frontend Alerts

### Problem
During the ISO upload + extraction workflow on a nearly-full disk:
1. `extractDirectory()` swallowed all errors including ENOSPC — extraction seemed to succeed
2. SQLite DB write then failed with "database or disk is full; cannot rollback - no transaction is active"
3. Frontend showed the confusing raw SQLite error

### Backend Changes

**`internal/extractor/extractor.go`** — `isDiskFull()` helper + error propagation
- Added `isDiskFull(err)` that unwraps through error chains and checks for "no space left on device" (Linux) or "not enough space on the disk" (Windows)
- `extractDirectory()`: disk-full errors now **abort** extraction immediately instead of logging and continuing
- `extractUDFContents()` / `extractUDFFile()`: same treatment
- Other non-disk errors are still gracefully skipped (corrupt file shouldn't abort)

**`internal/admin/handlers.go`** — Clear disk-full error messages
- `ExtractImage()` (line 1225-1228): DB write failures with disk-full keywords return clear user message
- Upload handler: same treatment for upload-save failures

### Frontend Changes

**`web/static/app.js`** — `showAlert()` + disk-full detection
- `showAlert()` now accepts optional 3rd arg `persistent` — notification doesn't auto-dismiss; shows × close button
- `extractImage()`: detects disk-full error, appends persistent ⚠ warning
- Upload handler: same disk-full detection + persistent warning

**`web/static/styles.css`** — `.notification-persistent` + `.notification-close` styles

### Scripts
- `build-windows.bat`: success hints use `.\` prefix (works in cmd.exe AND PowerShell)
- `README.md`: all examples use `.\build-windows.bat`; PowerShell note at top

---

## 2026-05-16 — Feature Flags: Proxy DHCP + Windows SMB + WIM Patcher

### Problem
The admin UI showed "Proxy DHCP Disabled", "Windows SMB Disabled", and "Windows SMB Patcher Unavailable" with no indication of how to enable them.

### Root Causes
1. **Proxy DHCP**: `--proxy-dhcp` flag exists but defaults to `false`. Bat script had no way to pass it.
2. **Windows SMB**: Bat script passed `--windows-smb-port` when `--smb` was given, but **never** passed `--windows-smb` (the enable flag).
3. **WIM Patcher**: Needs `wimlib-imagex.exe` in PATH or under `%ProgramFiles%\wimlib\`.

### Changes

**`scripts/build-windows.bat`** — Fixed flag passthrough
- `--smb PORT` now passes `--windows-smb --windows-smb-port PORT` (was just `--windows-smb-port`)
- Added `--proxy-dhcp` flag (passes `--proxy-dhcp` to the binary)

**`scripts/README.md`** — Updated documentation
- Added `--proxy-dhcp` to usage and examples
- New "Feature Prerequisites" table showing flags and dependencies

**`internal/server/server.go`** — Startup log visibility
- Added clear log messages at startup showing status of each feature:
  - "Proxy DHCP: disabled (use --proxy-dhcp to enable)"
  - "Windows SMB: disabled (use --windows-smb to enable)"
  - "Proxy DHCP: enabled (will bind UDP/67)"
  - "Windows SMB: enabled (port N, requires smbd in PATH)"

**`cmd/serve_windows.go`** — Silenced console init noise
- Removed `log.Printf` calls from `enableAnsiConsole()` fallback (silent fallback when stdout is redirected)

---

## 2026-05-16 — Native Windows SMB Share Implementation

### `internal/smb/manager_windows.go` — Rewritten
Replaced the stub that returned "not supported on Windows" with a real implementation using Windows native SMB:

- **Start()**: Creates SMB shares via `net share ShareName=Path /GRANT:Everyone,READ`
- **Reload()**: Stops then restarts all shares
- **Stop()**: Removes shares via `net share ShareName /DELETE`
- Also starts the `Server` service if not already running

### `internal/admin/handlers.go` — Platform-specific messages
- Windows SMB status: now shows "Unavailable (requires admin privileges)" when manager is nil
- wimlib not found message: Windows shows "download from https://wimlib.net/" or "run the build script"

### How it works
On Windows, `--windows-smb` flag triggers:
1. `smb.NewManager()` creates the manager (stores share name/path mappings)
2. `preloadSMBShares()` adds pre-existing extracted ISOs as shares
3. `mgr.Start()` calls `net share` for each registered share
4. When an image is patched for SMB install, `AddShare()` + `Reload()` adds the new share
5. On shutdown, `Stop()` calls `net share /DELETE` for each share

---

## 2026-05-16 — Wimlib Auto-Download from Go (Removed from Bat Script)

### Problem
The Go code was uploading wimlib from a hardcoded URL (`wimlib-1.14.4`) in the bat script. Users running bootimus without the bat script (e.g., directly or via `go run`) had no wimlib auto-install. The version was also hardcoded rather than auto-detected.

### Changes

**`internal/toolpath/toolpath.go`** — Added `AddToolsDir()`
- Thread-safe function to register additional directories for `LookPath` to search
- Uses `sync.RWMutex` for concurrent access

**`internal/server/server.go`** — Added `ensureWimlib()` + `latestWimlibURL()`
- `ensureWimlib()` called during `Server.Start()` after ISO scan
1. Checks if `wimlib-imagex` is already available (PATH, standard install dirs, or cached)
2. On Windows only, if not found: fetches `https://wimlib.net/downloads/index.html`
3. Uses regex to find the latest `wimlib-X.Y.Z-windows-x86_64-bin.zip` URL
4. Downloads zip, extracts `wimlib-imagex.exe` to `{dataDir}/tools/`
5. Registers `{dataDir}/tools/` with `toolpath.AddToolsDir()` so future lookups find it
- `latestWimlibURL()` parses the downloads page with `regexp.MustCompile` to find the latest x86_64 Windows binary (no hardcoded version)

**`scripts/build-windows.bat`** — Cleaned up
- Removed the wimlib download block (lines 139-157: version check, powershell download, zip extraction)
- Kept `TOOLS_DIR` creation and PATH addition for other potential tools

**`internal/admin/handlers.go`** — Updated messages
- SMB patcher status: `"Unavailable (auto-downloads on server startup if internet is available)"`
- Boot.wim patch error: `"wimlib-imagex not installed. It will be auto-downloaded on server restart if internet is available"`

### Why
- Works regardless of how bootimus is started (bat script, `go run`, direct binary)
- Always fetches the latest version; no hardcoded version number to go stale
- Single source of truth for tool installation — the Go binary
- Bat script no longer needs to duplicate this logic

### Verification
- `go build ./...` — passes
- `go vet ./...` — passes

---

## 2026-05-16 — Boot Menu Redesign (Modern Layout + Platform Badge)

### Problem
The iPXE boot menu was plain and didn't indicate whether the client booted via BIOS or UEFI, making it hard to debug or confirm the boot mode.

### Changes

**`internal/server/server.go`**
- `handleInventoryReport()`: Now passes `platform` and `buildarch` query params to `/menu.ipxe` redirect
- `handleIPXEMenu()`: Parses `platform` and `arch` params from query string

**`internal/server/menu.go`**
- `MenuBuilder`: Added `platform` and `buildArch` fields
- `generateIPXEMenuWithGroups()`: Accepts `platform` and `buildArch` params
- `platformBadge()` / `platformIcon()`: Returns `"UEFI"` / `"BIOS"` or `"[UEFI]"` / `"[BIOS]"`
- `headerInfo()`: Renders a top info bar with server address, client MAC, and `Mode: UEFI/BIOS` with architecture
- `formatToolItem()`: Shows `[BIOS+UEFI]` for tools with both variants, or `[UEFI]`/`[BIOS]` for platform-specific ones
- All section headers now use `== Section ==` format (compatible with all iPXE builds — no `---` which triggers option parsing)
- Removed empty `item --gap` lines (not supported by this iPXE build)
- Removed `--key` shortcuts (not supported reliably)
- Removed `colour` commands (not available in the `g988d2` build)

### Limitations (noted for future)
- `colour`/`cpair` commands unavailable — requires iPXE rebuild with `COLOUR_CMD`/`CPAIR_CMD`
- Background images not possible — requires `CONSOLE_FRAMEBUFFER` + `IMAGE_PNG`
- See `.github/workflows/build-ipxe.yml` for rebuild workflow

### Verification
- `go build ./...` — passes
- `go vet ./...` — passes
