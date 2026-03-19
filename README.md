# JAV Lib Manager 🎀

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

[English](#english) | [简体中文](README_zh.md) | [日本語](README_ja.md)

*A modern desktop application for personal video collection management*

</div>

---

## English

### Introduction

🎀 **JAV Lib Manager** is a powerful desktop application for personal video collection management. It intelligently organizes your local video files, automatically fetches metadata from online sources, and provides advanced search and filtering capabilities — all stored locally, never uploaded.

### Key Features

- 🔍 **Smart Scanning** — Automatically scan directories and extract video IDs from filenames
- 🌐 **Metadata Fetching** — Fetch cover images, actress info, and tags from JavDB
- 🏷️ **Multi-dimensional Search** — Filter by video ID, actress, tag, or studio
- 📺 **Modern UI** — Beautiful PyQt6-based interface with 18 Material Design themes
- 💾 **Local Database** — SQLite storage supporting large collections
- 📷 **Cover Caching** — Automatic cover image download and local caching
- ⚡ **High Performance** — Multi-threaded processing for a smooth experience

### Interface Preview

```
┌─────────────────────────────────────────────────────┐
│  🎀 JAV Lib Manager                                  │
├─────────────────────────────────────────────────────┤
│  [Scan] [Refresh] [Stats] [Logs] [Settings]          │
│  Search: [________________] [Filter ▼]               │
├──────────────────────┬──────────────────────────────┤
│  ┌────┐ ┌────┐      │ Cover Image                   │
│  │    │ │    │      │ ┌─────────────────────────┐   │
│  └────┘ └────┘      │ │                         │   │
│  ┌────┐ ┌────┐      │ │   [High Quality Cover]  │   │
│  │    │ │    │      │ │                         │   │
│  └────┘ └────┘      │ └─────────────────────────┘   │
│  ... more videos    │ Title: Video Title             │
│                     │ Actresses: Name1, Name2        │
│                     │ Tags: Tag1, Tag2, Tag3         │
│                     │ Studio: Studio Name            │
│                     │ File: /path/to/video.mp4       │
└──────────────────────┴──────────────────────────────┘
```

---

## 📖 Complete User Guide

### Prerequisites

- **Python**: 3.9 or higher — [Download here](https://www.python.org/downloads/) *(check "Add Python to PATH" during install)*
- **Operating System**: Windows 10/11
- **Disk Space**: 500MB+ for dependencies (including Playwright Chromium ~300MB)
- **Network**: Required for metadata fetching

### Installation

#### Method 1: Using Git (Recommended)

```bash
# Clone the repository
git clone https://github.com/ShadyDon/jav-lib-manager.git
cd jav-lib-manager

# (Optional) Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser engine
playwright install chromium

# Launch the application
python run_app.py
```

#### Method 2: Download ZIP

1. Go to [Releases](https://github.com/ShadyDon/jav-lib-manager/releases) and download the latest ZIP
2. Extract to any folder
3. Open a terminal in that folder and run:
```bash
pip install -r requirements.txt
playwright install chromium
python run_app.py
```

---

### First Time Setup

#### Step 1: Launch the Application

```bash
python run_app.py
```

The 🎀 logo will appear in the window title and interface.

#### Step 2: Scan Your Video Directory

1. Click **[Scan]** in the toolbar
2. Select the folder containing your video files (subdirectories are scanned automatically)
3. Wait for scanning to complete — a summary will show how many videos were detected
4. When prompted, click **"Yes"** to automatically fetch metadata for all detected videos

#### Step 3: Browse Your Library

Once metadata is fetched, your videos will appear as cards with covers. Click any card to view full details on the right panel.

---

### Daily Usage

#### Searching & Filtering

| Method | How To |
|--------|--------|
| Search by ID | Type e.g. `SSIS-123` in the search box |
| Search by title/actress | Type any keyword in the search box |
| Filter by actress | Use the actress dropdown |
| Filter by tag | Use the tag dropdown |
| Filter by studio | Use the studio dropdown |

#### Viewing Details

Click any video card to open the detail panel:
- **Cover image** — click it to view full-size
- **Actress list**, **Tags**, **Studio**, **Label**, **Series**
- **File path** and file size

#### Changing Theme

1. Click **[Settings]** in the toolbar
2. Go to the **Appearance** tab
3. Select from 18 Material Design themes
4. Click **Save**

#### Refreshing Metadata

To re-fetch metadata for videos missing covers or info:
1. Click **[Refresh]** or use the right-click menu on a video card
2. The app will attempt to fetch from JavDB again

---

### Configuration

Config file location: `data/config.json`

```json
{
  "database_path": "data/library.db",
  "covers_dir": "data/images/covers",
  "theme": "dark_amber",
  "window_width": 1600,
  "window_height": 900,
  "scraper_delay": 2,
  "scraper_timeout": 30
}
```

---

### Project Structure

```
jav-lib-manager/
├── README.md                 # English documentation
├── README_zh.md              # Chinese documentation
├── README_ja.md              # Japanese documentation
├── LICENSE                   # MIT License
├── CONTRIBUTING.md           # Contributing guidelines
├── CODE_OF_CONDUCT.md        # Community guidelines
├── CHANGELOG.md              # Version history
├── requirements.txt          # Python dependencies
├── run_app.py                # Application entry point
├── src/                      # Source code
│   ├── gui/                  # PyQt6 UI layer
│   │   ├── main_window.py
│   │   ├── themes/
│   │   └── dialogs/
│   ├── core/                 # Core logic
│   │   ├── parser.py         # Video ID parser
│   │   ├── scanner.py        # Directory scanner
│   │   ├── scraper.py        # Metadata scraper
│   │   ├── javdb_scraper.py  # JavDB Playwright scraper
│   │   ├── database.py       # SQLite database
│   │   └── cover_downloader.py
│   └── utils/
│       ├── config.py
│       └── logger.py
├── tests/                    # Test suite
└── data/                     # Runtime data (gitignored)
    ├── library.db
    └── images/covers/
```

---

### Tech Stack

| Component | Technology |
|-----------|-----------|
| GUI Framework | PyQt6 |
| Theme Engine | qt-material |
| Database | SQLite |
| Web Scraping | Playwright + requests + lxml |
| Image Processing | Pillow |
| Icons | qtawesome (FontAwesome 5) |

### Supported Video Formats

`MP4` `MKV` `AVI` `WMV` `MOV` `FLV` `M4V` `TS` `WebM`

### Supported Filename Formats

The parser handles many common naming conventions:

| Filename | Parsed ID |
|----------|-----------|
| `SSIS-123.mp4` | `SSIS-123` |
| `SSIS123.mp4` | `SSIS-123` |
| `[SSIS-123] Title.mp4` | `SSIS-123` |
| `SSIS-123.H265.mp4` | `SSIS-123` |
| `SSIS-123.FHD.mp4` | `SSIS-123` |

---

### ❓ FAQ

**Q: Is my data uploaded anywhere?**

No. Everything is stored locally. The database is at `data/library.db` and covers at `data/images/covers/`.

**Q: Can I use this on Linux or Mac?**

Currently Windows 10/11 is officially supported. Linux/Mac support is planned for a future release.

**Q: How do I back up my library?**

Copy the entire `data/` folder to a safe location. It contains your database and all cached cover images.

**Q: Scanner finds 0 videos — what's wrong?**

| Symptom | Cause | Fix |
|---------|-------|-----|
| 0 results | Filename has no recognizable ID | Rename files to include the video ID |
| Missing videos | Subdirectories not scanned | Check "Scan subdirectories" in Settings |
| Specific files skipped | Unsupported format | Verify file extension is in the supported list |

**Q: Metadata fetching fails / mirror site is down**

Try these steps in order:

1. Check your internet connection and confirm you can reach JavDB in a browser
2. In **[Settings]** → **Scraper**, increase the request delay (e.g. 5 seconds) and retry count (e.g. 5)
3. Wait a while and try again — mirror sites sometimes have temporary outages

If the problem persists and the mirror is permanently down, the scraper URLs need to be updated. **Contact the author for the latest version:**

- 📧 Email: **1840630471@qq.com**
- 🐛 GitHub Issues: [github.com/ShadyDon/jav-lib-manager/issues](https://github.com/ShadyDon/jav-lib-manager/issues)

**Q: Covers are not showing up**

1. Check that `data/images/covers/` exists and has files
2. Select a video and use **Refresh** to re-download its cover
3. Verify your network connection

---

### Roadmap

- [ ] Video player integration
- [ ] Linux and Mac support
- [ ] Batch file renaming tool
- [ ] Export to CSV/JSON
- [ ] Advanced statistics and reports
- [ ] Custom metadata sources

### Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### License

MIT License — see [LICENSE](LICENSE) for details.

### Acknowledgments

- **PyQt6 Team** — For the excellent GUI framework
- **Playwright Team** — For reliable browser automation
- **qt-material** — For the beautiful Material Design themes

---

<div align="center">

**⭐ If you find this project useful, please give it a star! ⭐**

Made with ❤️ and 🎀

</div>
