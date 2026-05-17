package smb

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
)

type Manager struct {
	dataDir string
	port    int

	mu     sync.RWMutex
	shares map[string]string

	cmd *exec.Cmd
}

func NewManager(dataDir string, port int) *Manager {
	return &Manager{
		dataDir: dataDir,
		port:    port,
		shares:  make(map[string]string),
	}
}

func (m *Manager) AddShare(name, path string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.shares[name] = path
}

func (m *Manager) RemoveShare(name string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.shares, name)
}

func (m *Manager) HasShare(name string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	_, ok := m.shares[name]
	return ok
}

func (m *Manager) ShareCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.shares)
}

func (m *Manager) Port() int {
	return m.port
}

func SanitizeShareName(isoBase string) string {
	var sb strings.Builder
	for _, r := range isoBase {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9', r == '-', r == '_':
			sb.WriteRune(r)
		default:
			sb.WriteRune('_')
		}
	}
	result := sb.String()
	if len(result) > 80 {
		result = result[:80]
	}
	return result
}

func (m *Manager) smbDir() string    { return filepath.Join(m.dataDir, "smb") }
func (m *Manager) configPath() string { return filepath.Join(m.smbDir(), "smb.conf") }

func (m *Manager) ensureStateDirs() error {
	for _, sub := range []string{"locks", "state", "cache", "pid", "log", "ncalrpc", "private", "usershares"} {
		if err := os.MkdirAll(filepath.Join(m.smbDir(), sub), 0755); err != nil {
			return err
		}
	}
	return nil
}

func (m *Manager) writeConfig() error {
	m.mu.RLock()
	defer m.mu.RUnlock()

	dir := m.smbDir()
	var sb strings.Builder
	fmt.Fprintf(&sb, `[global]
   workgroup = WORKGROUP
   server role = standalone server
   log level = 1
   log file = %s/log/smbd.log
   smb ports = %d
   server min protocol = SMB2
   map to guest = bad user
   guest account = nobody
   load printers = no
   disable spoolss = yes
   # Install clients (WinPE) reboot mid-session and reconnect with the same
   # IP. Without these, smbd hangs onto the prior tree connect/oplocks and
   # the next net use fails. Locks aren't meaningful for a read-only share.
   oplocks = no
   kernel oplocks = no
   level2 oplocks = no
   strict locking = no
   deadtime = 1
   # Windows sends VC=0 on session setup after a reboot. Without this, smbd
   # keeps the prior session from the same client IP alive and refuses the
   # new one. This is the specific fix for "net use fails after VM reboot".
   reset on zero vc = yes
   lock directory = %s/locks
   state directory = %s/state
   cache directory = %s/cache
   pid directory = %s/pid
   ncalrpc dir = %s/ncalrpc
   private dir = %s/private
   usershare path = %s/usershares
   acl allow execute always = yes

`, dir, m.port, dir, dir, dir, dir, dir, dir, dir)

	for name, path := range m.shares {
		fmt.Fprintf(&sb, `[%s]
   path = %s
   read only = yes
   guest ok = yes
   browseable = yes

`, name, path)
	}

	return os.WriteFile(m.configPath(), []byte(sb.String()), 0644)
}
