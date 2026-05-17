# Issues

## Open

### SMB Manager (`internal/smb/manager.go`)
- Spawns `smbd` subprocess — Linux-only
- On Windows, SMB is provided by the OS; can't use `smbd`
- **Fix**: Create no-op stub on Windows, or integrate with Windows SMB via PowerShell (e.g. `New-SmbShare`)

### WIM Operations (`internal/wim/wim.go`)
- Uses `exec.Command("wimlib-imagex", ...)` — available on Windows via Cygwin/MSYS2 or standalone builds
- Uses `exec.Command("7z", ...)` — 7-Zip is available on Windows but path may differ
- **Fix**: Add path lookup for Windows equivalents; add build tags if needed

### bsdtar Extraction (`internal/extractor/extractor.go`)
- Uses `exec.Command("bsdtar", ...)` — part of libarchive, not on Windows by default
- **Fix**: Use pure-Go tar extraction as fallback on Windows, or check for `bsdtar.exe`

### ANSI Color Codes (`cmd/serve.go`)
- Banner uses `\033[92m` / `\033[33m` escape codes
- Works in modern Windows Terminal but not in classic cmd.exe / PowerShell ISE
- **Fix**: Use `golang.org/x/term` to detect terminal, strip ANSI if needed

### Config Path (`cmd/root.go`)
- Hardcoded `/etc/bootimus/` — Unix-only
- **Fix**: Add `%ProgramData%\bootimus\` fallback on Windows

## Resolved
- `syscall.Statfs_t` compilation — fixed by platform-specific files (2026-05-16)
- `syscall.SetsockoptInt` type mismatch — fixed by platform-specific files (2026-05-16)
- Running bootimus processes not being cleaned up between test runs — must kill orphaned processes before re-running `serve`
- SMB on Windows — resolved via `net share` native implementation in `manager_windows.go` (2026-05-16)
- WIM path lookup — resolved via `toolpath.LookPath` and `toolpath.AddToolsDir` (2026-05-16)
- bsdtar path lookup — resolved via `toolpath.LookPath` (2026-05-16)
- ANSI color codes — resolved via Win32 `SetConsoleMode` in `serve_windows.go` (2026-05-16)
- Config path — resolved via `%ProgramData%\bootimus\` in `cmd/root.go` (2026-05-16)
- wimlib version hardcoded — resolved via dynamic version detection from wimlib.net downloads page (2026-05-16)
- wimlib download only in bat script — resolved via auto-download in `ensureWimlib()` at Go runtime (2026-05-16)
