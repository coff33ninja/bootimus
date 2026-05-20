package profiles

import (
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

type ISOCatalog struct {
	Version string     `json:"version"`
	Distros []ISOEntry `json:"distros"`
}

type ISOEntry struct {
	ID            string         `json:"id"`
	Name          string         `json:"name"`
	Family        string         `json:"family"`
	Mirrors       []ISOMirror    `json:"mirrors"`
	Releases      []ISORelease   `json:"releases"`
	VersionGroups []VersionGroup `json:"version_groups,omitempty"`
}

type ISOMirror struct {
	Region string `json:"region"`
	Base   string `json:"base"`
}

type ISORelease struct {
	Label    string `json:"label"`
	Path     string `json:"path"`
	SizeHint string `json:"size_hint,omitempty"`
}

type VersionGroup struct {
	Version  string       `json:"version"`
	IsLatest bool         `json:"is_latest"`
	Releases []ISORelease `json:"releases"`
}

var versionPrefixRe = regexp.MustCompile(`^(\d[\d.]*)`)

func extractVersion(label string) string {
	m := versionPrefixRe.FindStringSubmatch(label)
	if m == nil {
		return ""
	}
	return m[1]
}

func versionCompare(a, b string) int {
	pa := strings.Split(a, ".")
	pb := strings.Split(b, ".")
	for i := 0; i < len(pa) && i < len(pb); i++ {
		ia, erra := strconv.Atoi(pa[i])
		ib, errb := strconv.Atoi(pb[i])
		if erra != nil || errb != nil {
			return strings.Compare(a, b)
		}
		if ia != ib {
			return ia - ib
		}
	}
	return len(pa) - len(pb)
}

func groupReleasesByVersion(releases []ISORelease) []VersionGroup {
	groups := make(map[string][]ISORelease)
	var versions []string
	var unversioned []ISORelease
	for _, r := range releases {
		v := extractVersion(r.Label)
		if v == "" {
			unversioned = append(unversioned, r)
			continue
		}
		if _, ok := groups[v]; !ok {
			versions = append(versions, v)
		}
		groups[v] = append(groups[v], r)
	}
	if len(versions) == 0 {
		if len(unversioned) == 0 {
			return nil
		}
		return []VersionGroup{{
			Version:  "Other",
			IsLatest: false,
			Releases: unversioned,
		}}
	}

	sort.Slice(versions, func(i, j int) bool {
		return versionCompare(versions[i], versions[j]) > 0
	})

	var result []VersionGroup
	for i, v := range versions {
		result = append(result, VersionGroup{
			Version:  v,
			IsLatest: i == 0,
			Releases: groups[v],
		})
	}
	if len(unversioned) > 0 {
		result = append(result, VersionGroup{
			Version:  "Other",
			IsLatest: false,
			Releases: unversioned,
		})
	}
	return result
}

func LoadISOCatalog() (*ISOCatalog, error) {
	data, err := embeddedProfiles.ReadFile("distro-profiles.json")
	if err != nil {
		return nil, fmt.Errorf("read distro-profiles: %w", err)
	}
	var pf ProfileFile
	if err := json.Unmarshal(data, &pf); err != nil {
		return nil, fmt.Errorf("parse distro-profiles: %w", err)
	}
	var distros []ISOEntry
	for _, p := range pf.Profiles {
		if len(p.Releases) == 0 {
			continue
		}
		entry := ISOEntry{
			ID:       p.ID,
			Name:     p.DisplayName,
			Family:   p.Family,
			Mirrors:  p.Mirrors,
			Releases: p.Releases,
		}
		if p.Family != "windows-archive" {
			entry.VersionGroups = groupReleasesByVersion(p.Releases)
		}
		distros = append(distros, entry)
	}
	return &ISOCatalog{Version: pf.Version, Distros: distros}, nil
}
