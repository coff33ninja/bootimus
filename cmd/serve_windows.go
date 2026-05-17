//go:build windows

package cmd

import (
	"golang.org/x/sys/windows"
)

func init() {
	enableAnsiConsole()
}

func enableAnsiConsole() {
	handle, err := windows.GetStdHandle(windows.STD_OUTPUT_HANDLE)
	if err != nil {
		clearColors()
		return
	}

	var mode uint32
	if err := windows.GetConsoleMode(handle, &mode); err != nil {
		// Not a console (e.g. output redirected) — disable ANSI codes
		clearColors()
		return
	}

	mode |= windows.ENABLE_VIRTUAL_TERMINAL_PROCESSING
	if err := windows.SetConsoleMode(handle, mode); err != nil {
		clearColors()
	}
}

func clearColors() {
	colorReset = ""
	colorLightGreen = ""
	colorYellow = ""
}
