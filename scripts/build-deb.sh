#!/bin/bash
set -e

# Build Debian package for tux-wallpaper
# Usage: ./scripts/build-deb.sh

set -x

DEB_PKG=debian-pkg
DIST=dist

mkdir -p "$DEB_PKG/DEBIAN"
mkdir -p "$DEB_PKG/usr/lib/python3/dist-packages"
mkdir -p "$DEB_PKG/usr/bin"
mkdir -p "$DEB_PKG/usr/share/applications"
mkdir -p "$DEB_PKG/usr/share/doc/tux-wallpaper"
mkdir -p "$DEB_PKG/usr/share/icons/hicolor/16x16/apps"
mkdir -p "$DEB_PKG/usr/share/icons/hicolor/32x32/apps"
mkdir -p "$DEB_PKG/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$DEB_PKG/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$DEB_PKG/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$DEB_PKG/usr/share/icons/hicolor/512x512/apps"

# Install wheel into temp dir
pip3 install --target="$DEB_PKG/usr/lib/python3/dist-packages" \
    --no-deps --no-build-isolation dist/tux_wallpaper-*.whl || \
pip3 install --target="$DEB_PKG/usr/lib/python3/dist-packages" \
    --no-deps --no-build-isolation --find-links dist/ tux_wallpaper

# Fix bin path
if [ -f "$DEB_PKG/usr/lib/python3/dist-packages/bin/tux-wallpaper" ]; then
    mv "$DEB_PKG/usr/lib/python3/dist-packages/bin/tux-wallpaper" \
       "$DEB_PKG/usr/bin/tux-wallpaper"
    rmdir "$DEB_PKG/usr/lib/python3/dist-packages/bin" 2>/dev/null || true
fi

# Copy pre-written debian control file
cp debian/control "$DEB_PKG/DEBIAN/control"

# Write desktop file
cat > "$DEB_PKG/usr/share/applications/tux-wallpaper.desktop" << 'EOF'
[Desktop Entry]
Name=Tux Wallpaper
Comment=Video wallpaper player for Linux
Exec=tux-wallpaper
Icon=tux-wallpaper
Terminal=false
Type=Application
Categories=Utility;Video;
EOF

# Copy icons
cp tux_wallpaper/data/icons/hicolor/16x16/apps/tux-wallpaper.png "$DEB_PKG/usr/share/icons/hicolor/16x16/apps/"
cp tux_wallpaper/data/icons/hicolor/32x32/apps/tux-wallpaper.png "$DEB_PKG/usr/share/icons/hicolor/32x32/apps/"
cp tux_wallpaper/data/icons/hicolor/64x64/apps/tux-wallpaper.png "$DEB_PKG/usr/share/icons/hicolor/64x64/apps/"
cp tux_wallpaper/data/icons/hicolor/128x128/apps/tux-wallpaper.png "$DEB_PKG/usr/share/icons/hicolor/128x128/apps/"
cp tux_wallpaper/data/icons/hicolor/256x256/apps/tux-wallpaper.png "$DEB_PKG/usr/share/icons/hicolor/256x256/apps/"
cp tux_wallpaper/data/icons/hicolor/512x512/apps/tux-wallpaper.png "$DEB_PKG/usr/share/icons/hicolor/512x512/apps/"

# Write copyright
cat > "$DEB_PKG/usr/share/doc/tux-wallpaper/copyright" << 'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Source: https://github.com/tux-dot-fan/tux-wallpaper

Files: *
Copyright: 2025 Dean
License: MIT
EOF

# Write changelog (required by Debian policy)
cat > "$DEB_PKG/usr/share/doc/tux-wallpaper/changelog" << 'EOF'
tux-wallpaper (0.1.4) stable; urgency=low

  * Initial release

 -- Dean  Tue, 07 Jul 2026 00:00:00 +0000
EOF
gzip -n "$DEB_PKG/usr/share/doc/tux-wallpaper/changelog"

# Build .deb
dpkg-deb --build --root-owner-group "$DEB_PKG" "$DIST/tux-wallpaper_0.1.4_all.deb"
