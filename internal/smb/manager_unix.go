//go:build !windows

package smb

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

func (m *Manager) Start() error {
	smbdPath, err := exec.LookPath("smbd")
	if err != nil {
		return fmt.Errorf("smbd not found in PATH (install the samba package): %w", err)
	}

	if err := m.ensureStateDirs(); err != nil {
		return fmt.Errorf("failed to create smbd state directories: %w", err)
	}

	if err := m.writeConfig(); err != nil {
		return fmt.Errorf("failed to write smb.conf: %w", err)
	}

	m.cmd = exec.Command(smbdPath, "--no-process-group", "--foreground", "--configfile", m.configPath())
	m.cmd.Stdout = os.Stdout
	m.cmd.Stderr = os.Stderr

	if err := m.cmd.Start(); err != nil {
		return fmt.Errorf("failed to start smbd: %w", err)
	}

	log.Printf("SMB: smbd started (PID %d, port %d)", m.cmd.Process.Pid, m.port)

	go func(cmd *exec.Cmd) {
		err := cmd.Wait()
		if err != nil {
			log.Printf("SMB: smbd exited: %v (check %s/log/smbd.log)", err, m.smbDir())
		} else {
			log.Printf("SMB: smbd exited cleanly")
		}
	}(m.cmd)

	return nil
}

func (m *Manager) Reload() error {
	if err := m.writeConfig(); err != nil {
		return fmt.Errorf("failed to write smb.conf: %w", err)
	}
	if m.cmd == nil || m.cmd.Process == nil {
		return nil
	}
	ctrlPath, err := exec.LookPath("smbcontrol")
	if err != nil {
		log.Printf("SMB: warning - smbcontrol not found, cannot reload smbd: %v", err)
		return nil
	}
	out, cErr := exec.Command(ctrlPath, "--configfile", m.configPath(), "smbd", "reload-config").CombinedOutput()
	if cErr != nil {
		log.Printf("SMB: warning - smbcontrol reload-config failed: %v (%s)", cErr, strings.TrimSpace(string(out)))
	}
	return nil
}

func (m *Manager) Stop() {
	if m.cmd != nil && m.cmd.Process != nil {
		if err := m.cmd.Process.Kill(); err != nil {
			log.Printf("SMB: warning - could not kill smbd: %v", err)
		}
	}
}
