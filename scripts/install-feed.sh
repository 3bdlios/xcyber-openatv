#!/bin/sh
set -eu
grep -q '^distro=openatv$' /etc/image-version || { echo 'Expected OpenATV receiver'; exit 1; }
grep -q '^version=8.0.1$' /etc/image-version || { echo 'Expected OpenATV 8.0.1'; exit 1; }
opkg print-architecture | grep -q 'arch xconn ' || { echo 'Expected xconn architecture'; exit 1; }
BASE="https://raw.githubusercontent.com/3bdlios/xcyber-openatv/main/feeds/openatv-8.0.1/xconn"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
for ARCH in all cortexa55 xconn; do
    wget -q -O "$TMP/$ARCH.gz" "$BASE/$ARCH/Packages.gz"
    gzip -t "$TMP/$ARCH.gz"
done
BACKUP="/etc/xc-opkg-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for NAME in all cortexa55 xconn static-cortexa55 static-xconn private; do
    FILE="/etc/opkg/$NAME-feed.conf"
    if [ -f "$FILE" ]; then mv "$FILE" "$BACKUP/"; fi
done
{
    for ARCH in all cortexa55 xconn; do
        echo "src/gz xc-openatv-$ARCH $BASE/$ARCH"
    done
    echo 'src/gz xc-openatv-debug https://github.com/3bdlios/xcyber-openatv/releases/download/feed-debug-8.0.1-20261125'
} > /etc/opkg/xcyber-openatv-feed.conf
opkg update
echo "Previous distro feeds saved in $BACKUP"
