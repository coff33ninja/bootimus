# Windows ISO Download Guide

Bootimus can download Windows installation ISOs directly from Microsoft's CDN — clean, untouched retail images with no modifications.

## How It Works

Unlike Linux ISOs (downloaded from community mirrors), Windows ISOs are fetched through Microsoft's official software download API:

1. **Select Version & Release** — Pick from Windows 11, 10, 8.1, 7, or Server
2. **Choose Edition** — Home/Pro/Edu, Home China, or Server variants
3. **Pick Language** — 38+ languages available
4. **Download** — Bootimus generates a fresh download link from Microsoft and saves the ISO

### Direct from Microsoft

The ISOs come directly from `software.download.prss.microsoft.com` — the same CDN that serves the official Media Creation Tool. No third-party mirrors, no repacked images.

## Accessing the Feature

1. Open the admin panel at `http://your-server:8081`
2. Click **Get Images** in the Images tab
3. Switch to the **Windows** tab
4. Select version, release, edition, and language from the dropdowns
5. Click **Download**

The ISO is downloaded in the background. Progress is shown in the same panel.

## Supported Versions

| Version | Releases | Notes |
|---------|----------|-------|
| **Windows 11** | 24H2, 25H2, 26H1 | Full API support |
| **Windows 10** | 22H2 | Full API support |
| **Windows 8.1** | Update 1 | Basic support |
| **Windows 7** | SP1 | Catalog entry only (no API download) |
| **Windows Server** | 2022, 2025, 2026 | Server Standard, Datacenter, Azure Edition |

## Supported Languages

Arabic, Brazilian Portuguese, Bulgarian, Chinese (Simplified), Chinese (Traditional), Croatian, Czech, Danish, Dutch, English (International), English (United States), Estonian, Finnish, French, French Canadian, German, Greek, Hebrew, Hungarian, Italian, Japanese, Korean, Latvian, Lithuanian, Norwegian (Bokmål), Polish, Portuguese (Brazil), Portuguese (Portugal), Romanian, Russian, Serbian Latin, Slovak, Slovenian, Spanish, Spanish (Mexico), Swedish, Thai, Turkish, Ukrainian.

## API Endpoints

### List Windows Builds

```
GET /api/windows-builds
```

Returns the known Windows versions, releases, and available editions enriched with build numbers from UUP Dump.

### Download Windows ISO

```
POST /api/images/download-windows
Content-Type: application/json

{
  "version_id": "windows11",
  "release": "25H2 (Build 26200 - 2026.03)",
  "edition": "3321",
  "lang": "en-US",
  "arch": "x64"
}
```

Starts a background ISO download. Progress can be polled via `/api/downloads/progress?filename=...`.

## Session & Anti-Abuse

Microsoft's download API employs Sentinel anti-abuse protection. Bootimus handles this transparently:

- Session whitelisting via Microsoft's vlscppe and ov-df services
- Cookie-based session state preservation
- Automatic retry on rate-limit rejection
- One session per download request

Because Microsoft generates expiring download links, each request gets a fresh link valid for ~24 hours.

## Technical Details

The download process:

1. Bootimus creates a session with Microsoft's download API
2. Queries available SKUs (product editions) for the selected version
3. Finds the matching language and architecture
4. Generates a time-limited download URL
5. Downloads the ISO in the background
6. The ISO is automatically registered in the image catalog

After download, you can extract boot.wim and PXE-boot Windows just like any other image.
