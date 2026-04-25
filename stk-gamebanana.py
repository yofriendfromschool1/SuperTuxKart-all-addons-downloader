#!/usr/bin/env python3
"""
stk-gamebanana — Cross-platform bulk installer for SuperTuxKart community addons
              from GameBanana (https://gamebanana.com/games/6390).

Supports Linux (native, Flatpak, Snap), Windows, and macOS.
Downloads karts, tracks, arenas, and sounds uploaded by the community on GameBanana.
"""

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Optional

# ──────────────────────────── Constants ────────────────────────────

GAME_ID = 6390  # SuperTuxKart on GameBanana
LIST_API = "https://api.gamebanana.com/Core/List/New"
ITEM_API = "https://api.gamebanana.com/Core/Item/Data"
USER_AGENT = "STK-GameBanana-Installer/1.0 (github.com/yofriendfromschool1/SuperTuxKart-all-addons-downloader)"
MAX_RETRIES = 3
RETRY_DELAY = 2        # seconds (doubles each retry)
PER_PAGE = 20           # GameBanana default page size
DEFAULT_WORKERS = 8
ITEM_TYPES = ["Mod", "Sound"]  # GameBanana item types to fetch

# Category name → STK addon type mapping
CATEGORY_MAP = {
    "karts":    "kart",
    "tracks":   "track",
    "arenas":   "arena",
    "maps":     "track",
    "circuits": "track",
}

# ──────────────────────────── Data Types ───────────────────────────


@dataclass
class Addon:
    """Represents a single downloadable addon from GameBanana."""
    id: int                     # GameBanana item ID
    gb_type: str                # Mod, Sound, etc.
    type: str                   # kart | track | arena | sound | other
    name: str
    author: str = ""
    description: str = ""
    file_url: str = ""          # direct download URL
    file_name: str = ""
    file_size: int = 0
    file_id: int = 0
    downloads: int = 0


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


def http_get(url: str, *, retries: int = MAX_RETRIES) -> bytes:
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
    return b""  # unreachable


def http_get_json(url: str, *, retries: int = MAX_RETRIES) -> any:
    """Download a URL and parse as JSON."""
    data = http_get(url, retries=retries)
    return json.loads(data)


# ──────────────────────── GameBanana API ───────────────────────────


def fetch_all_item_ids(item_type: str) -> list[tuple[str, int]]:
    """Fetch all item IDs for a given type from GameBanana, paginating through all pages."""
    all_items = []
    page = 1

    while True:
        url = (
            f"{LIST_API}?itemtype={item_type}&gameid={GAME_ID}"
            f"&page={page}&return_keys=1"
        )
        try:
            data = http_get_json(url)
        except Exception as exc:
            print(f"  ⚠  Failed to fetch page {page} for {item_type}: {exc}")
            break

        if not data or not isinstance(data, list):
            break

        for entry in data:
            if isinstance(entry, list) and len(entry) == 2:
                all_items.append((entry[0], entry[1]))

        # If we got fewer than PER_PAGE results, we've reached the last page
        if len(data) < PER_PAGE:
            break

        page += 1

    return all_items


def fetch_mod_details(item_type: str, item_id: int) -> Optional[Addon]:
    """Fetch detailed info for a single mod from GameBanana."""
    fields = "name,description,Category().name,Owner().name,Files().aFiles()"
    url = f"{ITEM_API}?itemtype={item_type}&itemid={item_id}&fields={fields}&return_keys=1"

    try:
        data = http_get_json(url)
    except Exception as exc:
        print(f"  ⚠  Failed to fetch details for {item_type}/{item_id}: {exc}")
        return None

    if not isinstance(data, dict) or "error" in data:
        return None

    name = data.get("name", f"Unknown-{item_id}")
    description = data.get("description", "")
    author = data.get("Owner().name", "unknown")
    category = data.get("Category().name", "") or ""

    # Determine addon type from category
    addon_type = CATEGORY_MAP.get(category.lower().strip(), "other")
    if item_type == "Sound":
        addon_type = "sound"

    # Get the first (or latest) file
    files_data = data.get("Files().aFiles()", {})
    if not files_data:
        return None

    # Pick the first file entry
    file_info = next(iter(files_data.values()))
    file_url = file_info.get("_sDownloadUrl", "").replace("\\/", "/")
    file_name = file_info.get("_sFile", "")
    file_size = int(file_info.get("_nFilesize", 0))
    file_id = int(file_info.get("_idRow", 0))
    download_count = int(file_info.get("_nDownloadCount", 0))

    if not file_url:
        return None

    return Addon(
        id=item_id,
        gb_type=item_type,
        type=addon_type,
        name=name,
        author=author,
        description=description,
        file_url=file_url,
        file_name=file_name,
        file_size=file_size,
        file_id=file_id,
        downloads=download_count,
    )


def fetch_all_addons(quiet: bool = False) -> list[Addon]:
    """Fetch all addon metadata from GameBanana for SuperTuxKart."""
    all_ids: list[tuple[str, int]] = []

    for item_type in ITEM_TYPES:
        if not quiet:
            print(f"  ⟳  Fetching {item_type} list …")
        ids = fetch_all_item_ids(item_type)
        all_ids.extend(ids)
        if not quiet:
            print(f"      Found {len(ids)} {item_type}(s)")

    if not quiet:
        print(f"\n  ⟳  Fetching details for {len(all_ids)} items …")

    addons: list[Addon] = []
    fetched = 0

    # Fetch details in parallel to speed things up
    with ThreadPoolExecutor(max_workers=DEFAULT_WORKERS) as pool:
        futures = {
            pool.submit(fetch_mod_details, itype, iid): (itype, iid)
            for itype, iid in all_ids
        }
        for future in as_completed(futures):
            fetched += 1
            result = future.result()
            if result is not None:
                addons.append(result)
            if not quiet and fetched % 50 == 0:
                print(f"      … fetched {fetched}/{len(all_ids)} details")

    if not quiet:
        print(f"      Done — {len(addons)} addons with downloadable files\n")

    return addons


# ──────────────────────── Install Logic ────────────────────────────


def addon_subfolder(addon: Addon) -> str:
    """Return the STK subfolder name for an addon type."""
    if addon.type == "kart":
        return "karts"
    elif addon.type in ("track", "arena"):
        return "tracks"
    else:
        # sounds and other types go into a gamebanana-specific folder
        return "gamebanana"


def addon_dirname(addon: Addon) -> str:
    """Generate a safe directory name for an addon."""
    # Use a slug based on the addon name + GB ID for uniqueness
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in addon.name)
    return f"gb_{safe_name}_{addon.id}"


def install_addon(addon: Addon, base_dir: Path, *, skip_existing: bool = True) -> str:
    """Download and extract a single addon. Returns a status message."""
    subfolder = addon_subfolder(addon)
    target_dir = base_dir / subfolder
    dir_name = addon_dirname(addon)
    addon_dir = target_dir / dir_name

    # Skip if already installed
    if skip_existing and addon_dir.exists() and any(addon_dir.iterdir()):
        return f"⏭  {addon.name} (already installed)"

    addon_dir.mkdir(parents=True, exist_ok=True)

    try:
        data = http_get(addon.file_url)
    except Exception as exc:
        return f"✗  {addon.name} — download failed: {exc}"

    # Determine if it's a zip or other archive
    is_zip = addon.file_name.lower().endswith(".zip") or data[:4] == b"PK\x03\x04"

    if is_zip:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, addon.file_name or f"{addon.id}.zip")
                with open(zip_path, "wb") as f:
                    f.write(data)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    # Security: reject paths that escape the addon directory
                    for member in zf.namelist():
                        resolved = (addon_dir / member).resolve()
                        if not str(resolved).startswith(str(addon_dir.resolve())):
                            return f"✗  {addon.name} — zip contains unsafe path: {member}"
                    zf.extractall(addon_dir)

            return f"✓  {addon.name}"
        except zipfile.BadZipFile:
            if addon_dir.exists() and not any(addon_dir.iterdir()):
                addon_dir.rmdir()
            return f"✗  {addon.name} — corrupt zip"
        except Exception as exc:
            if addon_dir.exists() and not any(addon_dir.iterdir()):
                addon_dir.rmdir()
            return f"✗  {addon.name} — extract failed: {exc}"
    else:
        # Not a zip — save the raw file directly
        try:
            dest = addon_dir / (addon.file_name or f"{addon.id}.dat")
            with open(dest, "wb") as f:
                f.write(data)
            return f"✓  {addon.name} (raw file)"
        except Exception as exc:
            if addon_dir.exists() and not any(addon_dir.iterdir()):
                addon_dir.rmdir()
            return f"✗  {addon.name} — save failed: {exc}"


# ────────────────────────── CLI & Main ─────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stk-gamebanana",
        description="Bulk-install SuperTuxKart community addons from GameBanana (karts, tracks, arenas, sounds).",
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
        choices=["kart", "track", "arena", "sound", "other", "all"],
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
║     🍌  STK GameBanana Installer  🍌            ║
║      Cross-platform · Parallel · Resumable       ║
╚══════════════════════════════════════════════════╝
  Platform   : {platform.system()} ({platform.machine()})
  Addons dir : {addons_dir}
  Source     : https://gamebanana.com/games/6390
"""
    print(banner)

    # ── Fetch addon database ──
    print("⟳  Fetching GameBanana addon database …\n")
    try:
        addons = fetch_all_addons(quiet=args.quiet)
    except Exception as exc:
        print(f"\n✗  Failed to fetch addon database: {exc}")
        sys.exit(1)

    if not addons:
        print("✗  No addons found. GameBanana may be down.")
        sys.exit(1)

    # ── Filter ──
    if args.type != "all":
        addons = [a for a in addons if a.type == args.type]

    karts  = sum(1 for a in addons if a.type == "kart")
    tracks = sum(1 for a in addons if a.type == "track")
    arenas = sum(1 for a in addons if a.type == "arena")
    sounds = sum(1 for a in addons if a.type == "sound")
    other  = sum(1 for a in addons if a.type == "other")
    print(f"   Found {len(addons)} addons  ({karts} karts · {tracks} tracks · {arenas} arenas · {sounds} sounds · {other} other)\n")

    # ── List mode ──
    if args.list:
        fmt = "{:<40}  {:<7}  {:<20}  {:>8}  {:>6}"
        print(fmt.format("NAME", "TYPE", "AUTHOR", "SIZE", "DLs"))
        print("─" * 95)
        for a in sorted(addons, key=lambda x: (x.type, x.name.lower())):
            size_str = f"{a.file_size / 1024:.0f}K" if a.file_size else "—"
            print(fmt.format(
                a.name[:40],
                a.type,
                (a.author or "—")[:20],
                size_str,
                str(a.downloads),
            ))
        sys.exit(0)

    # ── Dry run ──
    if args.dry_run:
        would_install = 0
        would_skip = 0
        for a in addons:
            existing = addons_dir / addon_subfolder(a) / addon_dirname(a)
            if not args.force and existing.exists() and any(existing.iterdir()):
                would_skip += 1
            else:
                would_install += 1
                if not args.quiet:
                    print(f"  → would install: {a.name} ({a.type})")
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
