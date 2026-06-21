# TODO — Tux Wallpaper

## P0 — Must Fix Before Demo

### 1. ~~daemon.py → WallpaperEngine integration~~
~~`daemon.py` calls local API which now uses `WallpaperEngine` — no direct integration needed.~~ ✅ Done (2026-06-20)

### 2. Real video playback test
- Need a real `.mp4` / `.webm` test file
- Must be run on a real GNOME Wayland desktop (not SSH)
- Verify wallpaper appears on correct monitor
- GTK3 window must be below desktop icons
- **Platform limitation**: GNOME Shell does not support Layer Shell protocol → `gtk-layer-shell` crashes the process. On GNOME Wayland, wallpaper requires a GNOME Shell extension (Gjs). X11 sessions work fine with the X11 fallback path.

## P1 — Before First Release

### 3. Remote server DB integration
- `server/` is scaffolded with `server/models.py` and API routes
- `server/main.py` needs to import and use `tux_wallpaper/service/db.py`
- Wire up the remote server to a real database (separate from local SQLite)

### 4. Settings UI
- Web UI currently has placeholder settings section
- Implement: playback speed slider, loop toggle, volume, monitor selector
- Call local API endpoints: `PATCH /api/settings`, `GET /api/settings`

### 5. Playlist support
- `wallpapers.json` for local playlist (shuffle, repeat, ordering)
- API endpoints: `POST /api/playlist`, `PATCH /api/playlist/{id}/reorder`
- Next/prev wallpaper commands in `playback_command`

## P2 — Nice to Have

### 6. Stripe paid downloads
- `POST /api/wallpapers/{id}/purchase` endpoint
- Stripe Webhook handler for `payment_intent.succeeded`
- Premium wallpapers marked `is_premium=True` in DB

### 7. Wallpaper store UI
- Browse/search/filter wallpapers in web UI
- Category tags, search bar, pagination
- Preview thumbnails (generate on upload)

### 8. Performance
- Pre-load next wallpaper in playlist
- Memory management: cap open mpv instances
- Lazy-load thumbnails in browse view

## Known Issues

- **SSH session**: Can't create GTK windows from SSH — real desktop test needed
- **mpv options**: Some mpv builds don't support all options — fallback to bare `MPV()` is implemented
- **Wayland**: `gtk-layer-shell` requires root; using GTK3 borderless window as fallback
- **X11 auth**: `xauth list` empty in SSH session; on real desktop it works fine

---

*Last updated: 2026-06-20*
