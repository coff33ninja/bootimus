//go:build windows

package smb

import (
	"fmt"
	"log"
	"os/exec"
	"strings"
)

func (m *Manager) Start() error {
	m.mu.RLock()
	shares := make(map[string]string, len(m.shares))
	for k, v := range m.shares {
		shares[k] = v
	}
	m.mu.RUnlock()

	if len(shares) == 0 {
		return nil
	}

	// Ensure the Server service is running
	exec.Command("net", "start", "Server").Run()

	for name, path := range shares {
		shareName := "Bootimus_" + SanitizeShareName(name)
		cmd := exec.Command("net", "share", shareName+"="+path, "/GRANT:Everyone,READ")
		out, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("failed to create SMB share %s: %w\n%s", shareName, err, strings.TrimSpace(string(out)))
		}
		log.Printf("Windows SMB: created share %s -> %s", shareName, path)
	}

	return nil
}

func (m *Manager) Reload() error {
	m.Stop()
	return m.Start()
}

func (m *Manager) Stop() {
	m.mu.RLock()
	names := make([]string, 0, len(m.shares))
	for name := range m.shares {
		names = append(names, name)
	}
	m.mu.RUnlock()

	for _, name := range names {
		shareName := "Bootimus_" + SanitizeShareName(name)
		out, _ := exec.Command("net", "share", shareName, "/DELETE").CombinedOutput()
		log.Printf("Windows SMB: removed share %s", shareName)
		if len(out) > 0 {
			log.Printf("Windows SMB: net share output: %s", strings.TrimSpace(string(out)))
		}
	}
}
