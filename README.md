# 🏎 SuperTuxKart-all-addons-downloader

**Bulk-install every SuperTuxKart community addon in one command.**
## Some third party addons
https://freethewhale.ovh/packs/random_01.zip
https://freethewhale.ovh/packs/random_02.zip
https://freethewhale.ovh/packs/random_03.zip
https://gamebanana.com/games/6390
https://dl.kimden.online/?test&all
https://dl.kimden.online/?m=3&c=99999
for dl if on windows you need #/ImposterSus at end of url
https://gamebanana.com/games/6390

A cross-platform Python script that downloads and installs all karts, tracks, and arenas from the official [SuperTuxKart](https://supertuxkart.net) addon repository — in parallel.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Cross-platform** | Linux (all distros), macOS, and Windows |
| **Auto-detection** | Finds your STK addons folder automatically — including Flatpak & Snap |
| **Parallel downloads** | Configurable thread pool (default: 8 threads) |
| **Resumable** | Skips already-installed addons by default |
| **Retries** | Exponential backoff on network failures (3 retries) |
| **Filtering** | Install only karts, tracks, or arenas |
| **Dry-run mode** | Preview what would be installed |
| **List mode** | Browse all available addons without installing |
| **Zip safety** | Rejects zip files with path traversal attacks |
| **Zero dependencies** | Uses only Python standard library |

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
- **Python 3.10+** (uses `list[Addon]` syntax and `match`-style features)
- **SuperTuxKart** installed on your system

### One-liner

```bash
# Download and run
curl -LO https://raw.githubusercontent.com/yofriendfromschool1/SuperTuxKart-all-addons-downloader/main/stk-addons.py
python3 stk-addons.py
```

### Or clone the repo

```bash
git clone https://github.com/yofriendfromschool1/SuperTuxKart-all-addons-downloader.git
cd SuperTuxKart-all-addons-downloader
python3 stk-addons.py
```

---

## 📖 Usage

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
# Install everything (skips already-installed)
python3 stk-addons.py

# Install only karts
python3 stk-addons.py --type kart

# Force re-download all tracks
python3 stk-addons.py --type track --force

# Limit to 4 threads (slower connection)
python3 stk-addons.py --workers 4

# Preview what would be installed
python3 stk-addons.py --dry-run

# List all available addons
python3 stk-addons.py --list

# Install to a custom directory
python3 stk-addons.py --dir ~/my-stk-addons
```

---

## 🔧 How It Works

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

1. **Fetch** — Downloads the official `online_assets.xml` from supertuxkart.net
2. **Parse** — Extracts addon metadata and deduplicates by ID (keeping highest revision)
3. **Detect** — Automatically finds your STK addons folder based on OS and install method
4. **Download** — Fetches addon ZIPs in parallel with configurable thread count
5. **Extract** — Safely extracts each addon to the correct subfolder (`karts/` or `tracks/`)

---

## 🛡 Security

- **Zip path traversal protection** — The script validates every file path inside downloaded ZIPs to ensure no file can be extracted outside the target directory.
- **No eval / exec** — No dynamic code execution.
- **No dependencies** — No supply-chain risk from third-party packages.

---

## ❓ FAQ

<details>
<summary><strong>How many addons are there?</strong></summary>

As of 2026, there are **1000+** community addons including karts, tracks, and arenas.
</details>

<details>
<summary><strong>Will this break my existing addons?</strong></summary>

No. By default, the script **skips** any addon that is already installed. Use `--force` to re-download.
</details>

<details>
<summary><strong>Can I use this on a headless server?</strong></summary>

Yes. The script is terminal-only and requires no GUI. Useful for setting up a dedicated STK server with all tracks available.
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
- Performance improvements
- Better error handling

---

<p align="center">
  <em>Made with 🐧 for the SuperTuxKart community</em>
</p>
