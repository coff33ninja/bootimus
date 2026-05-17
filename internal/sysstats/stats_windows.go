//go:build windows

package sysstats

import "golang.org/x/sys/windows"

func getDiskStatsManual(path string) (DiskStats, error) {
	pathPtr, err := windows.UTF16PtrFromString(path)
	if err != nil {
		return DiskStats{}, err
	}

	var freeBytesAvailable, totalBytes, totalFreeBytes uint64
	err = windows.GetDiskFreeSpaceEx(pathPtr, &freeBytesAvailable, &totalBytes, &totalFreeBytes)
	if err != nil {
		return DiskStats{}, err
	}

	used := totalBytes - totalFreeBytes
	usedPercent := 0.0
	if totalBytes > 0 {
		usedPercent = float64(used) / float64(totalBytes) * 100
	}

	return DiskStats{
		Path:        path,
		Total:       totalBytes,
		Used:        used,
		Free:        totalFreeBytes,
		UsedPercent: usedPercent,
	}, nil
}
