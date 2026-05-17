package toolpath

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sync"
)

var (
	extraDirs   []string
	extraDirsMu sync.RWMutex
)

func AddToolsDir(dir string) {
	extraDirsMu.Lock()
	extraDirs = append(extraDirs, dir)
	extraDirsMu.Unlock()
}

func LookPath(name string) (string, error) {
	path, err := exec.LookPath(name)
	if err == nil {
		return path, nil
	}

	extraDirsMu.RLock()
	dirs := append([]string{}, extraDirs...)
	extraDirsMu.RUnlock()

	for _, dir := range dirs {
		if candidate, _ := findExe(dir, name); candidate != "" {
			return candidate, nil
		}
	}

	if runtime.GOOS == "windows" {
		ext := filepath.Ext(name)
		if ext == "" {
			name += ".exe"
		}

		switch name {
		case "7z.exe":
			for _, dir := range []string{
				filepath.Join(os.Getenv("ProgramFiles"), "7-Zip"),
				filepath.Join(os.Getenv("ProgramFiles(x86)"), "7-Zip"),
				os.Getenv("SystemRoot") + "\\System32",
			} {
				if candidate, _ := findExe(dir, "7z.exe"); candidate != "" {
					return candidate, nil
				}
			}
		case "wimlib-imagex.exe":
			for _, dir := range []string{
				filepath.Join(os.Getenv("ProgramFiles"), "wimlib"),
				filepath.Join(os.Getenv("ProgramFiles(x86)"), "wimlib"),
			} {
				if candidate, _ := findExe(dir, "wimlib-imagex.exe"); candidate != "" {
					return candidate, nil
				}
			}
		case "bsdtar.exe":
			for _, dir := range []string{
				filepath.Join(os.Getenv("ProgramFiles"), "bsdtar"),
				filepath.Join(os.Getenv("ProgramFiles(x86)"), "bsdtar"),
				filepath.Join(os.Getenv("ProgramFiles"), "libarchive"),
				os.Getenv("SystemRoot") + "\\System32",
			} {
				if candidate, _ := findExe(dir, "bsdtar.exe"); candidate != "" {
					return candidate, nil
				}
			}
		}
	}

	return "", err
}

func findExe(dir, name string) (string, error) {
	candidate := filepath.Join(dir, name)
	_, err := os.Stat(candidate)
	if err != nil {
		return "", err
	}
	return candidate, nil
}
