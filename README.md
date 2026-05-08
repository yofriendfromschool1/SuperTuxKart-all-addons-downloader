# 🏎 SuperTuxKart-all-addons-downloader

**Bulk-install every SuperTuxKart community addon in one command.**

Two scripts — one for the **official STK repository**, one for **GameBanana** — that download and install all karts, tracks, and arenas into your game, in parallel.

## Some third-party addon sources
- https://freethewhale.ovh/packs/random_01.zip
- https://freethewhale.ovh/packs/random_02.zip
- https://freethewhale.ovh/packs/random_03.zip
- https://gamebanana.com/games/6390
- https://stk.servegame.com/
- https://stk.iluvatyr.com/all-in-one
- https://github.com/8jq9ir/test
- https://dl.kimden.online/?test&all
- https://dl.kimden.online/?m=3&c=99999 (on Windows append `#/ImposterSus` to the URL)
- https://dl.kimden.online/dl/rv.zip
- https://github.com/STK944/AO
- https://cdjief.codeberg.page/stkaddons.html
- btw for the dl you need to type /installaddon then the link here but i think max is 150 at a time

---

## ✨ Features

| Feature | `stk-addons.py` | `stk-gamebanana.py` |
|---|:---:|:---:|
| **Cross-platform** (Linux, macOS, Windows) | ✅ | ✅ |
| **Auto-detects** STK addons folder (Flatpak, Snap, native) | ✅ | ✅ |
| **Parallel downloads** (configurable threads) | ✅ | ✅ |
| **Resumable** (skips already-installed) | ✅ | ✅ |
| **Retries** with exponential backoff | ✅ | ✅ |
| **Filter** by type (kart/track/arena) | ✅ | ✅ |
| **Dry-run & list modes** | ✅ | ✅ |
| **Zip path traversal protection** | ✅ | ✅ |
| **Zero dependencies** (Python stdlib only) | ✅ | ✅ |
| Official STK XML addon database | ✅ | — |
| GameBanana REST API (319+ mods, sounds) | — | ✅ |
| Updates `addons_installed.xml` | ✅ | — |

---

## 📦 Supported Platforms

### Linux
| Installation Method | Addons Path |
|---|---|
| **Native** (apt, pacman, dnf, zypper, xbps, emerge…) | `~/.local/share/supertuxkart/addons/` |
| **Flatpak** | `~/.var/app/net.supertuxkart.SuperTuxKart/data/supertuxkart/addons/` |
| **Snap** | `~/snap/supertuxkart/current/.local/share/supertuxkart/addons/` |

### macOS
| Installation Method | Addons Path |
|---|---|
| **Native / Homebrew** | `~/Library/Application Support/SuperTuxKart/Addons/` |

### Windows
| Installation Method | Addons Path |
|---|---|
| **Installer / Portable** | `%APPDATA%\supertuxkart\addons\` |

> [!NOTE]
> If auto-detection doesn't find your install, use `--dir` to specify the path manually.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **SuperTuxKart** installed on your system

### Install from official STK repository

```bash
# One-liner
curl -LO https://raw.githubusercontent.com/yofriendfromschool1/SuperTuxKart-all-addons-downloader/main/stk-addons.py
python3 stk-addons.py
```

### Install from GameBanana

```bash
# One-liner
curl -LO https://raw.githubusercontent.com/yofriendfromschool1/SuperTuxKart-all-addons-downloader/main/stk-gamebanana.py
python3 stk-gamebanana.py
```

### Or clone the repo and run both

```bash
git clone https://github.com/yofriendfromschool1/SuperTuxKart-all-addons-downloader.git
cd SuperTuxKart-all-addons-downloader

# Official addons
python3 stk-addons.py

# GameBanana addons
python3 stk-gamebanana.py
```

---

## 📖 Usage — `stk-addons.py` (Official Repository)

```
usage: stk-addons [-h] [--type {kart,track,arena,all}] [--dir PATH]
                  [--workers N] [--force] [--dry-run] [--list] [--quiet]
```

### Options

| Flag | Short | Description |
|---|---|---|
| `--type TYPE` | `-t` | Install only `kart`, `track`, `arena`, or `all` (default) |
| `--dir PATH` | `-d` | Override the auto-detected addons directory |
| `--workers N` | `-w` | Number of parallel download threads (default: 8) |
| `--force` | `-f` | Re-download addons even if already installed |
| `--dry-run` | `-n` | Show what would be installed without downloading |
| `--list` | `-l` | List all available addons and exit |
| `--quiet` | `-q` | Suppress per-addon output, show only summary |

### Examples

```bash
python3 stk-addons.py                        # Install everything
python3 stk-addons.py --type kart             # Only karts
python3 stk-addons.py --type track --force    # Force re-download tracks
python3 stk-addons.py --workers 4             # Limit threads
python3 stk-addons.py --dry-run               # Preview
python3 stk-addons.py --list                  # Browse addons
python3 stk-addons.py --dir ~/my-stk-addons   # Custom directory
```

---

## 📖 Usage — `stk-gamebanana.py` (GameBanana)

```
usage: stk-gamebanana [-h] [--type {kart,track,arena,sound,other,all}] [--dir PATH]
                      [--workers N] [--force] [--dry-run] [--list] [--quiet]
```

### Options

| Flag | Short | Description |
|---|---|---|
| `--type TYPE` | `-t` | Install only `kart`, `track`, `arena`, `sound`, `other`, or `all` (default) |
| `--dir PATH` | `-d` | Override the auto-detected addons directory |
| `--workers N` | `-w` | Number of parallel download threads (default: 8) |
| `--force` | `-f` | Re-download addons even if already installed |
| `--dry-run` | `-n` | Show what would be installed without downloading |
| `--list` | `-l` | List all available addons and exit |
| `--quiet` | `-q` | Suppress per-addon output, show only summary |

### Examples

```bash
python3 stk-gamebanana.py                        # Install everything from GameBanana
python3 stk-gamebanana.py --type kart             # Only karts
python3 stk-gamebanana.py --type track --force    # Force re-download tracks
python3 stk-gamebanana.py --list                  # Browse all 319+ GameBanana addons
python3 stk-gamebanana.py --dry-run               # Preview what would be installed
python3 stk-gamebanana.py --dir ~/my-stk-addons   # Custom directory
```

---

## 🔧 How It Works

### `stk-addons.py`

```
 ┌──────────────┐    ┌───────────────┐    ┌──────────────┐
 │  Fetch XML   │ →  │  Parse & De-  │ →  │  Parallel    │
 │  database    │    │  duplicate    │    │  download    │
 └──────────────┘    └───────────────┘    └──────┬───────┘
                                                 │
                     ┌───────────────┐    ┌──────▼───────┐
                     │  Addons dir   │ ←  │  Extract     │
                     │  (auto-detect)│    │  with safety │
                     └───────────────┘    └──────────────┘
```

1. **Fetch** — Downloads `online_assets.xml` from supertuxkart.net
2. **Parse** — Deduplicates by ID (keeping highest revision)
3. **Detect** — Finds your addons folder (Flatpak / Snap / native / macOS / Windows)
4. **Download** — Parallel ZIPs with configurable thread count
5. **Extract** — Safely into `karts/` or `tracks/`

### `stk-gamebanana.py`

```
 ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
 │  Paginate     │ →  │  Fetch mod    │ →  │  Parallel     │
 │  mod list API │    │  details API  │    │  download     │
 └───────────────┘    └───────────────┘    └──────┬────────┘
                                                  │
                      ┌───────────────┐    ┌──────▼────────┐
                      │  Addons dir   │ ←  │  Extract      │
                      │  (auto-detect)│    │  with safety  │
                      └───────────────┘    └───────────────┘
```

1. **Paginate** — Walks all pages of the GameBanana `Core/List/New` API for Mod & Sound items
2. **Details** — Fetches name, category, author, and download URLs via `Core/Item/Data`
3. **Classify** — Maps GameBanana categories ("Karts", "Tracks", etc.) to STK subfolder
4. **Download** — Parallel downloads via `gamebanana.com/dl/{id}`
5. **Extract** — Safely into `karts/`, `tracks/`, or `gamebanana/` (for sounds/other)

---

## 🛡 Security

- **Zip path traversal protection** — Both scripts validate every file path inside downloaded ZIPs to ensure no file escapes the target directory.
- **No eval / exec** — No dynamic code execution.
- **No dependencies** — No supply-chain risk from third-party packages.

---

## ❓ FAQ

<details>
<summary><strong>How many addons are there?</strong></summary>

- **Official STK repo:** 1000+ community addons (karts, tracks, arenas)
- **GameBanana:** 319+ mods plus sounds
</details>

<details>
<summary><strong>Will this break my existing addons?</strong></summary>

No. Both scripts **skip** already-installed addons by default. Use `--force` to re-download.
</details>

<details>
<summary><strong>Can I run both scripts?</strong></summary>

Yes! They install to the same addons directory but use different naming. Run `stk-addons.py` first for the official addons, then `stk-gamebanana.py` for the community extras from GameBanana.
</details>

<details>
<summary><strong>Can I use this on a headless server?</strong></summary>

Yes. Both scripts are terminal-only and require no GUI. Useful for setting up a dedicated STK server with all tracks available.
</details>

<details>
<summary><strong>The script fails with SSL errors</strong></summary>

Some minimal Python installations may lack SSL certificates. Try:

```bash
# Debian/Ubuntu
sudo apt install ca-certificates python3-certifi

# Arch
sudo pacman -S ca-certificates

# macOS (if using homebrew python)
/Applications/Python\ 3.x/Install\ Certificates.command
```
</details>

---

## 📄 License

MIT License — do whatever you want with it.

---

## 🤝 Contributing

Contributions welcome! Feel free to open issues or PRs for:
- Bug fixes
- New platform support
- New addon sources
- Performance improvements
- Better error handling

---

<p align="center">
  <em>Made with 🐧 for the SuperTuxKart community</em>
</p>
