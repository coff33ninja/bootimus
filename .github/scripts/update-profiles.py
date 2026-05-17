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


# ── Helpers ──

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    token = os.getenv("GITHUB_TOKEN")
    if token and "github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} fetching {url}")
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
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
    if latest > current:
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
    if latest > current:
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
    if tag > current:
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
    if tag > current:
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
    if tag > current:
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
        req = urllib.request.Request(url, method="HEAD")
        try:
            urllib.request.urlopen(req, timeout=10)
            latest = candidate
        except urllib.error.HTTPError:
            break
        except Exception:
            break
    # Also check next major
    for bump in [1, 2]:
        candidate = f"{major + bump}.00"
        url = (
            f"https://fastly-cdn.system-rescue.org/releases/"
            f"{candidate}/systemrescue-{candidate}-amd64.iso"
        )
        req = urllib.request.Request(url, method="HEAD")
        try:
            urllib.request.urlopen(req, timeout=10)
            latest = candidate
        except Exception:
            break
    if latest > current:
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
    """Ubuntu: check releases.ubuntu.com for new point releases."""
    idx = _profile_index(data)
    prof = idx.get("ubuntu")
    if not prof:
        return False
    changed = False
    for rel in prof.get("releases", []):
        m = re.search(r"/(\d+\.\d+(?:\.\d+)?)/", rel["path"])
        if not m:
            continue
        current_ver = m.group(1)
        # Extract base version (e.g. "24.04" from "24.04.3")
        base = ".".join(current_ver.split(".")[:2])
        # Check releases.ubuntu.com for this base
        html = fetch(f"https://releases.ubuntu.com/")
        if not html:
            continue
        vers = set()
        for m2 in re.finditer(rf'href="({re.escape(base)}\.\d+)/?"', html):
            vers.add(m2.group(1))
        if not vers:
            continue
        latest = sorted(vers, key=natural_key)[-1]
        if latest > current_ver:
            new_path = rel["path"].replace(current_ver, latest)
            print(f"  ubuntu {rel['label']}: {current_ver} -> {latest}")
            rel["path"] = new_path
            changed = True
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
                    if latest > current_ver:
                        new_path = rel["path"].replace(current_ver, latest)
                        print(f"  debian {rel['label']}: {current_ver} -> {latest}")
                        rel["path"] = new_path
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
        if latest > current_ver:
            new_path = rel["path"].replace(f"{current_ver}-", f"{latest}-")
            new_path = new_path.replace(f"/{current_ver}/", f"/{latest}/")
            print(f"  fedora {rel['label']}: {current_ver} -> {latest}")
            rel["path"] = new_path
            changed = True
    return changed


def _alpine_checker(data):
    """Alpine: check dl-cdn.alpinelinux.org for latest v3.xx release."""
    idx = _profile_index(data)
    prof = idx.get("alpine")
    if not prof:
        return False
    changed = False
    for rel in prof.get("releases", []):
        m = re.search(r"alpine-standard-([\d.]+)-", rel["path"])
        if not m:
            continue
        current_ver = m.group(1)
        base_major = ".".join(current_ver.split(".")[:2])  # e.g. "3.20"
        html = fetch("https://dl-cdn.alpinelinux.org/alpine/")
        if not html:
            continue
        vers = set()
        for m2 in re.finditer(r'href="(v[\d.]+)/"', html):
            v = m2.group(1).lstrip("v")
            if v.startswith(base_major.split(".")[0] + "."):
                vers.add(v)
        if not vers:
            # Fallback: use the latest-stable symlink
            latest_branch = base_major
        else:
            latest_branch = sorted(vers, key=natural_key)[-1]
        # Now check the actual patch version within this branch
        html2 = fetch(f"https://dl-cdn.alpinelinux.org/alpine/v{latest_branch}/releases/x86_64/")
        if not html2:
            # Branch exists but no releases yet — try previous branch
            prev = ".".join(str(int(x) - 1) if i == 1 else x for i, x in enumerate(latest_branch.split(".")))
            html2 = fetch(f"https://dl-cdn.alpinelinux.org/alpine/v{prev}/releases/x86_64/")
            if html2:
                latest_branch = prev
            else:
                continue
        patch_vers = set()
        for m3 in re.finditer(rf"alpine-standard-({re.escape(latest_branch)}\.\d+)-", html2):
            patch_vers.add(m3.group(1))
        if not patch_vers:
            continue
        latest_patch = sorted(patch_vers, key=natural_key)[-1]
        if latest_patch > current_ver:
            new_path = rel["path"].replace(current_ver, latest_patch)
            if latest_branch != base_major:
                new_path = new_path.replace(f"v{base_major}", f"v{latest_branch}")
            print(f"  alpine {rel['label']}: {current_ver} -> {latest_patch}")
            rel["path"] = new_path
            changed = True
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
        if latest > current_ver:
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
            print(f"  mint {rel['label']}: {current_ver} -> {latest}")
            rel["path"] = new_path
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


def update_distros():
    def updater(data):
        changed = False
        for profile in data.get("profiles", []):
            fn = DISTRO_CHECKERS.get(profile["id"])
            if fn:
                try:
                    if fn(data):
                        changed = True
                except Exception as e:
                    print(f"  ERROR updating {profile['id']}: {e}")
        return changed

    print("── Distros ──")
    return update_json_files(DISTRO_SOURCES, updater)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main():
    print(f"Bootimus Profile Updater{' (DRY RUN)' if DRY_RUN else ''}")
    print()

    tools_changed = update_tools()
    print()
    distros_changed = update_distros()
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


if __name__ == "__main__":
    main()
