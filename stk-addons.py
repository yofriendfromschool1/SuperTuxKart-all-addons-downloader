#!/usr/bin/env python3
"""
stk-addons — Cross-platform bulk installer for SuperTuxKart community addons.

Supports Linux (native, Flatpak, Snap), Windows, and macOS.
Downloads karts, tracks, and arenas from the official STK addon repository.
"""

import argparse
import os
import platform
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Optional

# ──────────────────────────── Constants ────────────────────────────

XML_URL = "https://online.supertuxkart.net/dl/xml/online_assets.xml"
USER_AGENT = "STK-Addons-Installer/2.0 (github.com/artyx/stk-addons)"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds (doubles each retry)
CHUNK_SIZE = 1024 * 64  # 64 KiB download chunks
DEFAULT_WORKERS = 8

# ──────────────────────────── Data Types ───────────────────────────


@dataclass
class Addon:
    """Represents a single downloadable addon."""
    id: str
    type: str          # kart | track | arena
    url: str
    name: str = ""
    designer: str = ""
    revision: int = 0
    rating: float = 0.0
    size: int = 0
    status: int = 0


@dataclass
class Stats:
    """Thread-safe download statistics."""
    total: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def tick(self, *, skipped: bool = False, failed: bool = False):
        with self._lock:
            if skipped:
                self.skipped += 1
            elif failed:
                self.failed += 1
            self.completed += 1

    @property
    def progress(self) -> str:
        with self._lock:
            pct = (self.completed / self.total * 100) if self.total else 0
            bar_len = 30
            filled = int(bar_len * self.completed / self.total) if self.total else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            return f"  {bar} {self.completed}/{self.total} ({pct:.0f}%)"


# ──────────────────────── Platform Detection ───────────────────────


def detect_addons_dir(override: Optional[str] = None) -> Path:
    """Detect the correct SuperTuxKart addons directory for the current platform."""
    if override:
        return Path(override).expanduser().resolve()

    system = platform.system()

    if system == "Linux":
        # Check Flatpak first
        flatpak = Path.home() / ".var/app/net.supertuxkart.SuperTuxKart/data/supertuxkart/addons"
        if flatpak.exists():
            return flatpak

        # Check Snap
        snap = Path.home() / "snap/supertuxkart/current/.local/share/supertuxkart/addons"
        if snap.exists():
            return snap

        # Native (works for apt, pacman, dnf, zypper, xbps, emerge — all use XDG)
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
        return Path(xdg) / "supertuxkart" / "addons"

    elif system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/SuperTuxKart/Addons"

    elif system == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))
        return Path(appdata) / "supertuxkart" / "addons"

    else:
        print(f"⚠  Unknown OS '{system}'. Falling back to current directory ./stk-addons/")
        return Path.cwd() / "stk-addons"


# ─────────────────────────── Networking ────────────────────────────


def http_get(url: str, *, binary: bool = True, retries: int = MAX_RETRIES) -> bytes:
    """Download a URL with retries and exponential backoff."""
    headers = {"User-Agent": USER_AGENT}
    delay = RETRY_DELAY

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as exc:
            if attempt == retries:
                raise
            print(f"  ↻ Retry {attempt}/{retries} for {url.split('/')[-1]} ({exc})")
            time.sleep(delay)
            delay *= 2
    return b""  # unreachable, but keeps type checkers happy


# ──────────────────────────── XML Parsing ──────────────────────────


def parse_addons(xml_bytes: bytes) -> list[Addon]:
    """Parse the online_assets.xml and return a deduplicated addon list."""
    root = ET.fromstring(xml_bytes)
    seen: dict[str, Addon] = {}

    for elem in root:
        tag = elem.tag.lower()
        if tag not in ("kart", "track", "arena"):
            continue

        addon_id = elem.attrib.get("id", "").strip()
        url = elem.attrib.get("file", "").strip()
        if not addon_id or not url:
            continue

        revision = int(elem.attrib.get("revision", "0") or "0")

        # Keep the highest revision for each addon ID
        if addon_id in seen and seen[addon_id].revision >= revision:
            continue

        seen[addon_id] = Addon(
            id=addon_id,
            type=tag,
            url=url,
            name=elem.attrib.get("name", addon_id),
            designer=elem.attrib.get("designer", "unknown"),
            revision=revision,
            rating=float(elem.attrib.get("rating", "0") or "0"),
            size=int(elem.attrib.get("size", "0") or "0"),
            status=int(elem.attrib.get("status", "0") or "0"),
        )

    return list(seen.values())


# ──────────────────────── Install Logic ────────────────────────────


def install_addon(addon: Addon, base_dir: Path, *, skip_existing: bool = True) -> str:
    """Download and extract a single addon. Returns a status message."""
    subfolder = "karts" if addon.type == "kart" else "tracks"
    target_dir = base_dir / subfolder
    addon_dir = target_dir / addon.id

    # Skip if already installed
    if skip_existing and addon_dir.exists() and any(addon_dir.iterdir()):
        return f"⏭  {addon.id} (already installed)"

    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        data = http_get(addon.url)
    except Exception as exc:
        return f"✗  {addon.id} — download failed: {exc}"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, f"{addon.id}.zip")
            with open(zip_path, "wb") as f:
                f.write(data)

            with zipfile.ZipFile(zip_path, "r") as zf:
                # Security: reject paths that escape the target directory
                for member in zf.namelist():
                    resolved = (target_dir / member).resolve()
                    if not str(resolved).startswith(str(target_dir.resolve())):
                        return f"✗  {addon.id} — zip contains unsafe path: {member}"
                zf.extractall(target_dir)

        return f"✓  {addon.id}"
    except zipfile.BadZipFile:
        return f"✗  {addon.id} — corrupt zip"
    except Exception as exc:
        return f"✗  {addon.id} — extract failed: {exc}"


# ────────────────────────── CLI & Main ─────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stk-addons",
        description="Bulk-install SuperTuxKart community addons (karts, tracks, arenas).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                        Install everything (skip already-installed)
  %(prog)s --type kart             Install only karts
  %(prog)s --type track --force    Force re-download of all tracks
  %(prog)s --workers 4             Limit to 4 parallel downloads
  %(prog)s --dir ~/my-stk-addons   Use a custom install directory
  %(prog)s --dry-run               Preview what would be installed
  %(prog)s --list                  List available addons without installing
""",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["kart", "track", "arena", "all"],
        default="all",
        help="Type of addons to install (default: all)",
    )
    parser.add_argument(
        "--dir", "-d",
        metavar="PATH",
        default=None,
        help="Override the auto-detected addons directory",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="N",
        help=f"Number of parallel download threads (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-download addons even if already installed",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be installed without downloading",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available addons and exit",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress per-addon output, show only summary",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    addons_dir = detect_addons_dir(args.dir)

    # ── Header ──
    banner = f"""
╔══════════════════════════════════════════════════╗
║          🏎  STK Addons Installer  🏎            ║
║      Cross-platform · Parallel · Resumable       ║
╚══════════════════════════════════════════════════╝
  Platform   : {platform.system()} ({platform.machine()})
  Addons dir : {addons_dir}
"""
    print(banner)

    # ── Fetch XML ──
    print("⟳  Fetching addon database …")
    try:
        xml_data = http_get(XML_URL)
    except Exception as exc:
        print(f"\n✗  Failed to fetch addon database: {exc}")
        sys.exit(1)

    addons = parse_addons(xml_data)
    if not addons:
        print("✗  No addons found in the database. The server may be down.")
        sys.exit(1)

    # ── Filter ──
    if args.type != "all":
        addons = [a for a in addons if a.type == args.type]

    karts  = sum(1 for a in addons if a.type == "kart")
    tracks = sum(1 for a in addons if a.type == "track")
    arenas = sum(1 for a in addons if a.type == "arena")
    print(f"   Found {len(addons)} addons  ({karts} karts · {tracks} tracks · {arenas} arenas)\n")

    # ── List mode ──
    if args.list:
        fmt = "{:<30}  {:<7}  {:<25}  rev {}"
        print(fmt.format("ID", "TYPE", "DESIGNER", "REV"))
        print("─" * 80)
        for a in sorted(addons, key=lambda x: (x.type, x.id)):
            print(fmt.format(a.id[:30], a.type, (a.designer or "—")[:25], a.revision))
        sys.exit(0)

    # ── Dry run ──
    if args.dry_run:
        subfolder_map = {"kart": "karts", "track": "tracks", "arena": "tracks"}
        would_install = 0
        would_skip = 0
        for a in addons:
            existing = addons_dir / subfolder_map[a.type] / a.id
            if not args.force and existing.exists() and any(existing.iterdir()):
                would_skip += 1
            else:
                would_install += 1
                if not args.quiet:
                    print(f"  → would install: {a.id} ({a.type})")
        print(f"\n  Would install {would_install}, skip {would_skip} already-installed.")
        sys.exit(0)

    # ── Install ──
    addons_dir.mkdir(parents=True, exist_ok=True)
    stats = Stats(total=len(addons))
    start = time.monotonic()

    print(f"⬇  Downloading with {args.workers} threads …\n")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(install_addon, a, addons_dir, skip_existing=not args.force): a
            for a in addons
        }
        for future in as_completed(futures):
            result = future.result()
            is_skip = "already installed" in result
            is_fail = result.startswith("✗")
            stats.tick(skipped=is_skip, failed=is_fail)
            if not args.quiet:
                print(f"  {stats.progress}  {result}")

    elapsed = time.monotonic() - start
    installed = stats.completed - stats.skipped - stats.failed

    print(f"""
╔══════════════════════════════════════════════════╗
║                    ✓  Done!                      ║
╠══════════════════════════════════════════════════╣
║  Installed : {installed:<5}                                ║
║  Skipped   : {stats.skipped:<5}  (already present)              ║
║  Failed    : {stats.failed:<5}                                ║
║  Time      : {elapsed:>5.1f}s                                ║
╚══════════════════════════════════════════════════╝
""")

    if stats.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
