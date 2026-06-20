# Tux Wallpaper

Video wallpaper player for Linux (GNOME on Wayland) with cloud wallpaper service.

## Features

- **Video Wallpaper**: Play MP4/WebM videos as desktop wallpaper using mpv
- **Cloud Service**: Browse, search, and download wallpapers from a remote server
- **System Tray**: Control playback from a system tray icon
- **Cross-platform Backend**: FastAPI server with SQLite local cache
- **Extensible**: Support for additional wallpaper sources and effects

## Requirements

- Python 3.12+
- mpv
- GNOME Shell (Wayland session)
- System dependencies:
  ```bash
  # Ubuntu/Debian
  sudo apt install mpv libmpv-dev libgl1-mesa-glx libwebkit2gtk-4.1-dev
  ```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tux-wallpaper.git
cd tux-wallpaper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run the application
tux-wallpaper
```

## Project Structure

```
tux-wallpaper/
├── tux_wallpaper/       # Main Python package
│   ├── player/          # mpv wallpaper player engine
│   └── service/         # Local REST API service
├── server/              # Remote server (FastAPI)
├── web/                 # Frontend UI (HTML/JS/CSS)
├── tests/               # Test suite
├── config/              # Configuration files
└── data/                # Downloaded wallpapers
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tux Wallpaper                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌────────────┐ │
│  │   Web UI    │◄──►│ Local API   │◄──►│   Player   │ │
│  │  (PyWebView)│    │ (FastAPI)   │    │   (mpv)    │ │
│  └─────────────┘    └──────┬──────┘    └────────────┘ │
│                            │                             │
│                            ▼                             │
│                   ┌───────────────┐                     │
│                   │  Remote API   │                      │
│                   │  (Optional)   │                      │
│                   └───────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linters
ruff check .
mypy tux_wallpaper/

# Format code
ruff format .
isort .
```

### Testing

```bash
# Run all tests with coverage
pytest --cov=tux_wallpaper --cov-report=term-missing

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
```

## License

MIT
