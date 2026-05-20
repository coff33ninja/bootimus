#!/usr/bin/env python3
"""
Bootimus Profile Auto-Updater
Checks for new releases of tools (tools-profiles.json) and distros (distro-profiles.json)
and opens a PR when updates are found.

Usage:
  python .github/scripts/update-profiles.py [--dry-run]

Requires: GITHUB_TOKEN env var for API calls (optional, ups rate limit)
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

UA = "Bootimus Auto-Updater/1.0 (+https://github.com/anomalyco/bootimus)"
ROOT = Path(__file__).resolve().parent.parent.parent
DRY_RUN = "--dry-run" in sys.argv
CI_MODE = "--ci" in sys.argv

TOOLS_SOURCES = {
    ROOT / "tools-profiles.json": ROOT / "internal/tools/tools-profiles.json",
}
DISTRO_SOURCES = {
    ROOT / "distro-profiles.json": ROOT / "internal/profiles/distro-profiles.json",
}

changed_files = []
_FETCH_CACHE = {}


# ── Helpers ──

def fetch(url, retries=2):
    """Fetch a URL with caching and exponential backoff retry."""
    if url in _FETCH_CACHE:
        return _FETCH_CACHE[url]

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        token = os.getenv("GITHUB_TOKEN")
        if token and "github.com" in url:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                result = r.read().decode("utf-8")
                _FETCH_CACHE[url] = result
                return result
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = 2 ** attempt
                print(f"  Rate limited ({url}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"  HTTP {e.code} fetching {url}")
            _FETCH_CACHE[url] = None
            return None
        except Exception as e:
            if attempt < retries:
                wait = 2 ** attempt
                print(f"  Transient error fetching {url}, retrying in {wait}s: {e}")
                time.sleep(wait)
                continue
            print(f"  Error fetching {url}: {e}")
            _FETCH_CACHE[url] = None
            return None
    return None


def fetch_json(url):
    data = fetch(url)
    return json.loads(data) if data else None


def natural_key(v):
    parts = re.findall(r"(\d+)", str(v))
    return tuple(int(p) for p in parts) if parts else (0,)


def save_json(path, data):
    if DRY_RUN:
        return
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def update_json_files(sources, updater):
    """Update paired JSON files (root + embedded). Returns True if changed."""
    any_changed = False
    for root_path, embed_path in sources.items():
        with open(root_path, encoding="utf-8") as f:
            data = json.load(f)
        changed = updater(data)
        if changed:
            save_json(root_path, data)
            save_json(embed_path, data)
            print(f"  Updated: {root_path.name}")
            any_changed = True
            changed_files.append(str(root_path))
    return any_changed


# ── SourceForge Version Scraper ──

def sourceforge_versions(project, subpath):
    """Get list of version directories from a SourceForge project."""
    url = f"https://sourceforge.net/projects/{project}/files/{subpath}/"
    html = fetch(url)
    if not html:
        return []
    # Parse the HTML for folder names (version directories)
    # Folders appear in table rows with class "folder"
    versions = set()
    for m in re.finditer(
        r'<tr[^>]*class="folder"[^>]*>.*?<a[^>]*href="[^"]*/([^/"]+)/?"[^>]*>',
        html,
        re.DOTALL,
    ):
        v = m.group(1).strip()
        if re.search(r"\d", v):
            versions.add(v)
    return sorted(versions, key=natural_key, reverse=True)


# ── GitHub Release Checker ──

def github_latest(owner_repo):
    """Get latest GitHub release. Returns (tag, asset_map) or (None, None)."""
    data = fetch_json(f"https://api.github.com/repos/{owner_repo}/releases/latest")
    if not data:
        return None, {}
    tag = data.get("tag_name", "").lstrip("v")
    assets = {}
    for a in data.get("assets", []):
        assets[a["name"]] = a["browser_download_url"]
    return tag, assets


# ── HTML Directory Listing Parser ──

def parse_dir_listing(html, base_url):
    """Parse Apache/NGINX directory listing for href links."""
    links = []
    for m in re.finditer(r'<a\s+href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', html, re.IGNORECASE):
        href = m.group(1).rstrip("/")
        text = m.group(2).strip()
        if href and not href.startswith("?") and not href.startswith("#"):
            if href.startswith("/"):
                links.append(href)
            else:
                links.append(base_url.rstrip("/") + "/" + href if not href.startswith("http") else href)
    return links


# ══════════════════════════════════════════════
#  TOOL UPDATERS
# ══════════════════════════════════════════════

def tool_gparted(tool):
    """GParted Live: SourceForge project gparted, subpath gparted-live-stable"""
    vers = sourceforge_versions("gparted", "gparted-live-stable")
    if not vers:
        return False
    latest = vers[0]
    current = tool.get("version", "")
    if natural_key(latest) > natural_key(current):
        print(f"  gparted: {current} -> {latest}")
        tool["version"] = latest
        tool["download_url"] = (
            f"https://downloads.sourceforge.net/project/gparted/"
            f"gparted-live-stable/{latest}/gparted-live-{latest}-amd64.zip"
        )
        return True
    return False


def tool_clonezilla(tool):
    """Clonezilla: SourceForge project clonezilla, subpath clonezilla_live_stable"""
    vers = sourceforge_versions("clonezilla", "clonezilla_live_stable")
    if not vers:
        return False
    latest = vers[0]
    current = tool.get("version", "")
    if natural_key(latest) > natural_key(current):
        print(f"  clonezilla: {current} -> {latest}")
        tool["version"] = latest
        tool["download_url"] = (
            f"https://downloads.sourceforge.net/project/clonezilla/"
            f"clonezilla_live_stable/{latest}/clonezilla-live-{latest}-amd64.zip"
        )
        return True
    return False


def tool_memtest(tool):
    """Memtest86+: GitHub memtest86plus/memtest86plus"""
    tag, assets = github_latest("memtest86plus/memtest86plus")
    if not tag:
        return False
    current = tool.get("version", "")
    if natural_key(tag) > natural_key(current):
        print(f"  memtest86plus: {current} -> {tag}")
        tool["version"] = tag
        tool["download_url"] = (
            f"https://memtest.org/download/v{tag}/mt86plus_{tag}.binaries.zip"
        )
        return True
    return False


def tool_shredos(tool):
    """ShredOS: GitHub PartialVolume/shredos.x86_64"""
    tag, assets = github_latest("PartialVolume/shredos.x86_64")
    if not tag:
        return False
    current = tool.get("version", "")
    if natural_key(tag) > natural_key(current):
        print(f"  shredos: {current} -> {tag}")
        tool["version"] = tag
        # Asset name pattern: shredos-{tag}.img
        # Expected asset: shredos-{version}.img
        expected = f"shredos-{tag}.img"
        url = assets.get(expected)
        if url:
            tool["download_url"] = url
        else:
            # Fallback: construct URL
            tool["download_url"] = (
                f"https://github.com/PartialVolume/shredos.x86_64/releases/"
                f"download/v{tag}/{expected}"
            )
        return True
    return False


def tool_netbootxyz(tool):
    """Netboot.xyz: GitHub netbootxyz/netboot.xyz"""
    tag, assets = github_latest("netbootxyz/netboot.xyz")
    if not tag:
        return False
    current = tool.get("version", "")
    if natural_key(tag) > natural_key(current):
        print(f"  netbootxyz: {current} -> {tag}")
        tool["version"] = tag
        url = assets.get("netboot.xyz.efi")
        if url:
            tool["download_url"] = url
        else:
            tool["download_url"] = (
                f"https://github.com/netbootxyz/netboot.xyz/releases/"
                f"download/v{tag}/netboot.xyz.efi"
            )
        return True
    return False


def tool_systemrescue(tool):
    """SystemRescue: probe CDN with HEAD requests for latest version"""
    current = tool.get("version", "")
    # Parse current version and try incremental bumps
    parts = current.split(".")
    major, minor = int(parts[0]), int(parts[1])
    latest = current
    for bump in [1, 2, 3, 4, 5]:
        candidate = f"{major}.{minor + bump:02d}"
        url = (
            f"https://fastly-cdn.system-rescue.org/releases/"
            f"{candidate}/systemrescue-{candidate}-amd64.iso"
        )
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=10)
            latest = candidate
        except urllib.error.HTTPError:
            break
        except Exception as e:
            print(f"  HEAD probe failed for {candidate}: {e}")
            break
    # Also check next major
    for bump in [1, 2]:
        candidate = f"{major + bump}.00"
        url = (
            f"https://fastly-cdn.system-rescue.org/releases/"
            f"{candidate}/systemrescue-{candidate}-amd64.iso"
        )
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=10)
            latest = candidate
        except Exception as e:
            print(f"  HEAD probe failed for {candidate}: {e}")
            break
    if natural_key(latest) > natural_key(current):
        print(f"  systemrescue: {current} -> {latest}")
        tool["version"] = latest
        tool["download_url"] = (
            f"https://fastly-cdn.system-rescue.org/releases/"
            f"{latest}/systemrescue-{latest}-amd64.iso"
        )
        return True
    return False


TOOL_UPDATERS = {
    "gparted": tool_gparted,
    "clonezilla": tool_clonezilla,
    "memtest86plus": tool_memtest,
    "systemrescue": tool_systemrescue,
    "shredos": tool_shredos,
    "netbootxyz": tool_netbootxyz,
}


def update_tools():
    def updater(data):
        changed = False
        for tool in data.get("tools", []):
            fn = TOOL_UPDATERS.get(tool["name"])
            if fn:
                try:
                    if fn(tool):
                        changed = True
                except Exception as e:
                    print(f"  ERROR updating {tool['name']}: {e}")
        return changed

    print("── Tools ──")
    return update_json_files(TOOLS_SOURCES, updater)


# ══════════════════════════════════════════════
#  DISTRO UPDATERS
# ══════════════════════════════════════════════

def _ubuntu_checker(data):
    """Ubuntu: check releases.ubuntu.com for the latest versions.
    Adds latest overall and latest LTS (if different), then prunes to 2 versions."""
    idx = _profile_index(data)
    prof = idx.get("ubuntu")
    if not prof:
        return False

    html = fetch("https://releases.ubuntu.com/")
    if not html:
        return False

    all_vers = set()
    for m in re.finditer(r'href="([\d.]+)/"', html):
        v = m.group(1)
        if re.match(r"^\d+\.\d+(?:\.\d+)?$", v):
            all_vers.add(v)
    if not all_vers:
        return False

    latest = sorted(all_vers, key=natural_key)[-1]

    # Also track latest LTS release separately (minor version "04")
    lts_vers = [v for v in all_vers if v.split(".")[1] == "04"]
    latest_lts = sorted(lts_vers, key=natural_key)[-1] if lts_vers else None

    versions_to_add = {latest}
    if latest_lts and latest_lts != latest:
        versions_to_add.add(latest_lts)

    existing_paths = {r.get("path", "") for r in prof.get("releases", [])}
    changed = False

    for version in sorted(versions_to_add, key=natural_key):
        is_lts = version.split(".")[1] == "04"
        lts_tag = " LTS" if is_lts else ""

        desktop_path = f"/{version}/ubuntu-{version}-desktop-amd64.iso"
        if desktop_path not in existing_paths:
            prof.setdefault("releases", []).append({
                "label": f"{version}{lts_tag} Desktop (amd64)",
                "path": desktop_path,
            })
            print(f"  ubuntu: added {version} Desktop")
            changed = True

        server_path = f"/{version}/ubuntu-{version}-live-server-amd64.iso"
        if server_path not in existing_paths:
            prof.setdefault("releases", []).append({
                "label": f"{version}{lts_tag} Server (amd64)",
                "path": server_path,
            })
            print(f"  ubuntu: added {version} Server")
            changed = True

    if changed:
        _prune_old_versions(prof, r"/([\d.]+)/")

    return changed


def _debian_checker(data):
    """Debian: check cdimage.debian.org current symlink for latest."""
    idx = _profile_index(data)
    prof = idx.get("debian")
    if not prof:
        return False
    changed = False
    for rel in prof.get("releases", []):
        m = re.search(r"debian-(\d[\d.]*\d)-amd64", rel["path"])
        if not m:
            continue
        current_ver = m.group(1)
        base = prof["mirrors"][0]["base"] if prof.get("mirrors") else "https://cdimage.debian.org/debian-cd/current/amd64"
        sha = fetch(base + "/iso-dvd/SHA256SUMS")
        if sha:
            for line in sha.splitlines():
                m2 = re.search(r"debian-([\d.]+)-amd64", line)
                if m2:
                    latest = m2.group(1)
                    if natural_key(latest) > natural_key(current_ver):
                        new_path = rel["path"].replace(current_ver, latest)
                        new_label = re.sub(r"^\d[\d.]+", latest, rel["label"])
                        print(f"  debian {rel['label']}: {current_ver} -> {latest}")
                        rel["path"] = new_path
                        rel["label"] = new_label
                        changed = True
                    break
    return changed


def _fedora_checker(data):
    """Fedora: check download.fedoraproject.org for latest release."""
    idx = _profile_index(data)
    prof = idx.get("fedora")
    if not prof:
        return False
    changed = False
    for rel in prof.get("releases", []):
        m = re.search(r"Fedora-Workstation-Live-x86_64-(\d+)-", rel["path"])
        if not m:
            continue
        current_ver = m.group(1)
        html = fetch("https://dl.fedoraproject.org/pub/fedora/linux/releases/")
        if not html:
            continue
        vers = set()
        for m2 in re.finditer(r'href="(\d+)/?"', html):
            v = m2.group(1)
            if v.isdigit() and int(v) > 30:  # Only real releases
                vers.add(v)
        if not vers:
            continue
        latest = sorted(vers, key=int)[-1]
        if natural_key(latest) > natural_key(current_ver):
            new_path = rel["path"].replace(f"{current_ver}-", f"{latest}-")
            new_path = new_path.replace(f"/{current_ver}/", f"/{latest}/")
            new_label = re.sub(r"^\d[\d.]+", latest, rel["label"])
            print(f"  fedora {rel['label']}: {current_ver} -> {latest}")
            rel["path"] = new_path
            rel["label"] = new_label
            changed = True
    return changed


def _alpine_checker(data):
    """Alpine: check dl-cdn.alpinelinux.org for latest v3.xx release.
    Adds new releases alongside existing ones."""
    idx = _profile_index(data)
    prof = idx.get("alpine")
    if not prof:
        return False

    html = fetch("https://dl-cdn.alpinelinux.org/alpine/")
    if not html:
        return False

    all_branches = set()
    for m2 in re.finditer(r'href="(v[\d.]+)/"', html):
        v = m2.group(1).lstrip("v")
        if re.match(r"^\d+\.\d+$", v):
            all_branches.add(v)
    if not all_branches:
        return False

    existing_paths = {r.get("path", "") for r in prof.get("releases", [])}
    changed = False

    for rel in prof.get("releases", []):
        m = re.search(r"alpine-([a-z]+)-([\d.]+)-", rel["path"])
        if not m:
            continue
        variant = m.group(1)
        current_ver = m.group(2)
        base_major = ".".join(current_ver.split(".")[:2])

        major = base_major.split(".")[0]
        matching = sorted(
            (v for v in all_branches if v.startswith(major + ".")),
            key=natural_key,
        )
        if not matching:
            continue

        # Find the highest branch that has releases
        latest_branch = None
        html2 = None
        for b in reversed(matching):
            html2 = fetch(f"https://dl-cdn.alpinelinux.org/alpine/v{b}/releases/x86_64/")
            if html2:
                latest_branch = b
                break
        if latest_branch is None:
            continue

        patch_vers = set()
        for m3 in re.finditer(rf"alpine-{variant}-({re.escape(latest_branch)}\.\d+)-", html2):
            patch_vers.add(m3.group(1))
        if not patch_vers:
            continue
        latest_patch = sorted(patch_vers, key=natural_key)[-1]

        if natural_key(latest_patch) <= natural_key(current_ver):
            continue

        # Build the new file path for the latest patch
        new_path = rel["path"].replace(current_ver, latest_patch)
        if latest_branch != base_major:
            new_path = new_path.replace(f"v{base_major}", f"v{latest_branch}")

        if new_path in existing_paths:
            continue

        new_label = f"{latest_patch} {variant.capitalize()} (x86_64)"
        prof.setdefault("releases", []).append({
            "label": new_label,
            "path": new_path,
        })
        existing_paths.add(new_path)
        print(f"  alpine: added {variant} {latest_patch}")
        changed = True

    if changed:
        _prune_old_versions(prof, r"alpine-([a-z]+)-([\d.]+)-", 2)

    return changed


def _mint_checker(data):
    """Linux Mint: check kernel.org mirror for latest stable version."""
    idx = _profile_index(data)
    prof = idx.get("mint")
    if not prof:
        return False
    changed = False
    for rel in prof.get("releases", []):
        m = re.search(r"linuxmint-([\d.]+)-", rel["path"])
        if not m:
            continue
        current_ver = m.group(1)
        html = fetch("https://mirrors.edge.kernel.org/linuxmint/stable/")
        if not html:
            continue
        vers = set()
        for m2 in re.finditer(r'href="([\d.]+)/?"', html):
            v = m2.group(1)
            if re.match(r"^\d+\.\d+$", v):
                vers.add(v)
        if not vers:
            continue
        latest = sorted(vers, key=natural_key)[-1]
        if natural_key(latest) > natural_key(current_ver):
            new_path = rel["path"].replace(current_ver, latest)
            # Also update ISO filename
            base_label = rel["label"].split(" (")[0] if "(" in rel["label"] else ""
            for variant in ["cinnamon", "mate", "xfce"]:
                if variant in rel["path"]:
                    old_iso = f"linuxmint-{current_ver}-{variant}-64bit.iso"
                    new_iso = f"linuxmint-{latest}-{variant}-64bit.iso"
                    if old_iso in new_path:
                        new_path = new_path.replace(old_iso, new_iso)
                    break
            new_label = re.sub(r"^\d[\d.]+", latest, rel["label"])
            print(f"  mint {rel['label']}: {current_ver} -> {latest}")
            rel["path"] = new_path
            rel["label"] = new_label
            changed = True
    return changed


def _kali_checker(data):
    """Kali: uses current/ symlink, just check if the existing links are live."""
    # Kali already uses "current/" which always points to the latest,
    # so the URL is inherently up-to-date. Just log.
    return False


def _arch_checker(data):
    """Arch: uses latest/ symlink, inherently up-to-date."""
    return False


DISTRO_CHECKERS = {
    "ubuntu": _ubuntu_checker,
    "debian": _debian_checker,
    "fedora": _fedora_checker,
    "alpine": _alpine_checker,
    "mint": _mint_checker,
    "kali": _kali_checker,
    "arch": _arch_checker,
}


def _profile_index(data):
    return {p["id"]: p for p in data.get("profiles", [])}


def _prune_old_versions(profile, version_regex, version_group=1):
    """Keep only releases for the 2 most recent versions in a profile.
    Returns True if any releases were removed."""
    releases = profile.get("releases", [])
    if len(releases) <= 2:
        return False

    vers = {}
    for rel in releases:
        m = re.search(version_regex, rel["path"])
        v = m.group(version_group) if m else None
        vers.setdefault(v, []).append(rel)

    sorted_vers = sorted(
        (v for v in vers if v is not None),
        key=natural_key,
        reverse=True,
    )
    if len(sorted_vers) <= 2:
        return False

    keep = set(sorted_vers[:2])
    new_releases = []
    removed_vers = set()
    for rel in releases:
        m = re.search(version_regex, rel["path"])
        v = m.group(version_group) if m else None
        if v is not None and v not in keep:
            removed_vers.add(v)
        else:
            new_releases.append(rel)

    profile["releases"] = new_releases
    if removed_vers:
        print(f"    pruned old versions: {', '.join(sorted(removed_vers, key=natural_key))}")
    return True


# ══════════════════════════════════════════════
#  INTERNET ARCHIVE COLLECTION UPDATERS
# ══════════════════════════════════════════════
#
# Scrapes Internet Archive items for new ISO releases and updates the profile
# entries. Designed to be extensible — add new collections to IA_COLLECTIONS.
#
# Each collection config:
#   base_url         – download URL prefix for files
#   family           – family value for auto-created profiles
#   profile_map      – maps IA product directory → profile ID(s) in the JSON
#                      (None = auto-generate; string = single profile; list = multi)
#   include_products – list of products to include (None = all non-internal)
#   skip_products    – list of products to always skip
#   file_filter      – callable(file_info) -> bool; which files become releases
#

# Maximum releases to keep per IA profile before pruning oldest entries.
MAX_IA_RELEASES_PER_PROFILE = 50

IA_COLLECTIONS = {
    "english_windows_collection": {
        "base_url": "https://archive.org/download/english_windows_collection",
        "family": "windows-archive",
        "profile_map": {
            "Windows 95": "win95-archive",
            "Windows 98": "win98-archive",
            "Windows ME": "winme-archive",
            "Windows NT 4.0": "winnt4-archive",
            "Windows 2000": "win2k-archive",
            "Windows XP": "winxp-archive",
            "Windows Vista": "winvista-archive",
            "Windows 7": "win7-archive",
            "Windows 8": "win8-archive",
            "Windows 8.1": "win8-archive",
            "Windows 10": "win10-archive",
            "Windows 11": "win11-archive",
            "Windows Neptune Build 5111": None,
            "Windows 1.0": None,
            "Windows 2.0": None,
            "Windows 3.0": None,
        },
        "skip_products": [
            "MS DOS 6.0",
            "Windows Server",
        ],
        "file_filter": lambda f: f["name"].lower().endswith(".iso"),
    },
}


def fetch_ia_metadata(collection):
    """Fetch file listing from an Internet Archive item via its metadata API.

    Returns a dict of {path: info} regardless of whether the API returns
    the files as a list or a dict.
    """
    url = f"https://archive.org/metadata/{collection}"
    data = fetch_json(url)
    if not data:
        print(f"    No data from IA API for {collection}")
        return {}

    raw = data.get("files") or []
    if isinstance(raw, list):
        # List of {"name": "path", ...}
        return {entry["name"]: entry for entry in raw if "name" in entry}
    # Already a dict keyed by path
    return raw


def group_ia_files_by_product(files_dict):
    """Group IA files by top-level product directory from their virtual path."""
    products = {}
    for path, info in files_dict.items():
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            continue
        product = parts[0]
        # Skip IA internal files
        if product.startswith("__") or product in (
            "logo.jpg", "logo_thumb.jpg",
        ):
            continue
        if product not in products:
            products[product] = []
        products[product].append({
            "path": path.strip("/"),
            "name": parts[-1],
            "size": info.get("size", 0),
            "format": info.get("format", ""),
            "md5": info.get("md5", ""),
        })
    return products


def _ia_safe_id(product):
    """Convert a product name like 'Windows 95' to a safe ID like 'win95-archive'."""
    s = product.lower().strip()
    # Map common patterns
    mapping = {
        "windows 1": "win1",
        "windows 2": "win2",
        "windows 3": "win3",
        "windows 95": "win95",
        "windows 98": "win98",
        "windows me": "winme",
        "windows nt 4.0": "winnt4",
        "windows 2000": "win2k",
        "windows xp": "winxp",
        "windows vista": "winvista",
        "windows 7": "win7",
        "windows 8": "win8",
        "windows 8.1": "win8",
        "windows 10": "win10",
        "windows 11": "win11",
        "windows server": "winserver",
        "windows neptune": "winneptune",
    }
    for key, val in mapping.items():
        if s.startswith(key):
            return f"{val}-archive"
    # Fallback: slugify
    slug = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return f"{slug}-archive"


def _ia_product_display(product):
    """Generate a human-readable display name for a product."""
    mapping = {
        "Windows Neptune Build 5111": "Windows Neptune (Internet Archive)",
        "Windows 1.0": "Windows 1.0 (Internet Archive)",
        "Windows 2.0": "Windows 2.0 (Internet Archive)",
        "Windows 3.0": "Windows 3.0 (Internet Archive)",
    }
    return mapping.get(product, f"{product} (Internet Archive)")


def _ia_release_label(product_dir, subpath, file_info):
    """Generate a human-readable label from an IA file path.

    Uses the version-detail directory (second path component) as the label
    since it typically describes the release (e.g. 'SP3', 'RTM', '22H2').
    """
    parts = subpath.split("/")
    if len(parts) >= 2:
        return parts[1]
    return file_info["name"]


def _ensure_ia_profile(data, product, config):
    """Create a new profile entry in the JSON for an IA product if it doesn't exist."""
    idx = {p["id"]: p for p in data.get("profiles", [])}
    profile_id = _ia_safe_id(product)
    if profile_id in idx:
        return idx[profile_id]

    profile = {
        "id": profile_id,
        "display_name": _ia_product_display(product),
        "family": config["family"],
        "filename_patterns": [],
        "kernel_paths": [],
        "initrd_paths": [],
        "squashfs_paths": [],
        "default_boot_params": "",
        "auto_install_type": "",
        "boot_method": "",
        "mirrors": [
            {
                "region": "Internet Archive",
                "base": config["base_url"],
            }
        ],
        "releases": [],
    }
    data.setdefault("profiles", []).append(profile)
    print(f"    Created new profile: {profile_id} ({product})")
    return profile


def _url_encode_ia_path(path):
    """URL-encode each component of an IA file path for use in a download URL."""
    parts = path.split("/")
    encoded = "/".join(urllib.parse.quote(p, safe="") for p in parts)
    return "/" + encoded


def _existing_release_set(profile):
    """Build a set of (label, path) tuples for existing releases."""
    existing = set()
    for rel in profile.get("releases", []):
        existing.add((rel.get("label", ""), rel.get("path", "")))
    return existing


def update_ia_collection(data, collection_name, config):
    """Update distro-profiles.json with releases from an Internet Archive collection.

    Returns True if any changes were made.
    """
    print(f"  Checking IA collection: {collection_name}")
    files_dict = fetch_ia_metadata(collection_name)
    if not files_dict:
        return False

    products = group_ia_files_by_product(files_dict)
    changed = False
    idx = {p["id"]: p for p in data.get("profiles", [])}

    skip = set(config.get("skip_products", []))
    include = config.get("include_products")
    file_filter = config.get("file_filter", lambda f: True)
    profile_map = config.get("profile_map", {})

    for product, files in sorted(products.items()):
        if product in skip:
            continue
        if include is not None and product not in include:
            continue

        # Filter files
        filtered = [f for f in files if file_filter(f)]
        if not filtered:
            continue

        # Determine which profile IDs this product maps to
        mapped = profile_map.get(product)
        if mapped is None:
            profile_ids = [_ia_safe_id(product)]
        elif isinstance(mapped, str):
            profile_ids = [mapped]
        else:
            profile_ids = list(mapped)

        for pid in profile_ids:
            # Find or create the profile
            profile = idx.get(pid)
            if profile is None:
                profile = _ensure_ia_profile(data, product, config)
                idx[profile["id"]] = profile
                changed = True

            existing = _existing_release_set(profile)
            for fi in sorted(filtered, key=lambda f: f["path"]):
                path = fi["path"]
                label = _ia_release_label(product, path, fi)
                encoded_path = _url_encode_ia_path(path)
                if (label, encoded_path) in existing:
                    continue
                # Check if same path already exists (URL-encoded)
                if any(rel.get("path") == encoded_path for rel in profile.get("releases", [])):
                    continue
                profile.setdefault("releases", []).append({
                    "label": label,
                    "path": encoded_path,
                })
                print(f"    Added release: {label} -> {encoded_path}")
                changed = True

            # Sort releases by path for deterministic ordering
            if profile.get("releases"):
                profile["releases"].sort(key=lambda r: natural_key(r.get("path", "")))

            # Cap IA profile growth — prune oldest releases beyond limit
            releases = profile.get("releases", [])
            if len(releases) > MAX_IA_RELEASES_PER_PROFILE:
                pruned = len(releases) - MAX_IA_RELEASES_PER_PROFILE
                profile["releases"] = releases[-MAX_IA_RELEASES_PER_PROFILE:]
                print(f"    Pruned {pruned} oldest releases (max {MAX_IA_RELEASES_PER_PROFILE})")
                changed = True

    return changed


def update_ia_profiles(data):
    """Run all Internet Archive collection updaters."""
    print("── Internet Archive Collections ──")
    changed = False
    for collection, config in IA_COLLECTIONS.items():
        if update_ia_collection(data, collection, config):
            changed = True
            changed_files.append(f"ia:{collection}")
    return changed


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main():
    print(f"Bootimus Profile Updater{' (DRY RUN)' if DRY_RUN else ''}")
    print()

    tools_changed = update_tools()
    print()

    def distro_updater(data):
        d = update_distros_inner(data)
        i = update_ia_profiles(data)
        return d or i

    distros_changed = update_json_files(DISTRO_SOURCES, distro_updater)
    print()

    any_changed = tools_changed or distros_changed
    if CI_MODE:
        gh_out = os.environ.get("GITHUB_OUTPUT", "")
        if gh_out:
            with open(gh_out, "a") as f:
                f.write(f"changed={'true' if any_changed else 'false'}\n")

    if any_changed:
        print(f"Changes detected in: {', '.join(changed_files)}")
        if DRY_RUN:
            print("DRY RUN — no files written.")
        else:
            print("Files updated.")
        sys.exit(0)
    else:
        print("All up to date.")
        sys.exit(0)


def update_distros_inner(data):
    """Run all distro checkers on a single data dict. Returns True if changed."""
    changed = False
    for profile_id, fn in DISTRO_CHECKERS.items():
        try:
            if fn(data):
                changed = True
        except Exception as e:
            print(f"  ERROR updating {profile_id}: {e}")
    return changed


if __name__ == "__main__":
    main()
