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

# Install wheel into temp dir
pip3 install --target="$DEB_PKG/usr/lib/python3/dist-packages" \
    --no-deps --no-build-isolation .

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
Icon=/usr/share/icons/hicolor/128x128/apps/vlc.png
Terminal=false
Type=Application
Categories=Utility;Video;
EOF

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
tux-wallpaper (1.0.0) stable; urgency=low

  * Initial release

 -- Dean  Tue, 07 Jul 2026 00:00:00 +0000
EOF
gzip -n "$DEB_PKG/usr/share/doc/tux-wallpaper/changelog"

# Build .deb
dpkg-deb --build --root-owner-group "$DEB_PKG" "$DIST/tux-wallpaper_1.0.0_all.deb"
