#!/bin/bash
# Install the pH Sensor Box service on a Raspberry Pi (Raspberry Pi OS Bookworm or later).
#
# Run it as root from the checkout in /opt/ph-sensorbox:
#
#   sudo apt-get install -y git
#   sudo git clone https://github.com/winf-hsos/ph-sensorbox.git /opt/ph-sensorbox
#   sudo /opt/ph-sensorbox/pi/install.sh
#
# Running it again is safe: it keeps the configuration, the secret and the backlog.
set -euo pipefail

REPO=/opt/ph-sensorbox
ORIGIN=https://github.com/winf-hsos/ph-sensorbox.git

[ "$(id -u)" = 0 ] || { echo "please run as root (sudo)"; exit 1; }
[ -d "$REPO/.git" ] || { echo "expected the checkout in $REPO"; exit 1; }
cd "$REPO"

echo "== Tinkerforge packages (brickd, python3-tinkerforge)"
if [ ! -f /etc/apt/sources.list.d/tinkerforge.list ]; then
    . /etc/os-release
    wget -q "https://download.tinkerforge.com/apt/$ID/tinkerforge.asc" -O - > /etc/apt/trusted.gpg.d/tinkerforge.asc
    echo "deb https://download.tinkerforge.com/apt/$ID $VERSION_CODENAME main" > /etc/apt/sources.list.d/tinkerforge.list
    apt-get update -q
fi
DEBIAN_FRONTEND=noninteractive apt-get install -y -q git brickd python3-tinkerforge

echo "== user and folders"
id phbox >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin phbox
install -d -m 755 /etc/ph-box
install -d -m 755 -o phbox -g phbox /var/lib/ph-box
if [ ! -f /etc/ph-box/config.toml ]; then
    sed "s/^box = .*/box = \"$(hostname)\"/" pi/config.example.toml > /etc/ph-box/config.toml
    echo "created /etc/ph-box/config.toml with box = \"$(hostname)\""
fi

echo "== checkout"
git remote set-url origin "$ORIGIN" 2>/dev/null || git remote add origin "$ORIGIN"
git describe --tags --always > /var/lib/ph-box/version
echo "version $(cat /var/lib/ph-box/version)"

echo "== commands and services"
install -m 755 pi/ph-box /usr/local/bin/ph-box
install -m 755 pi/ph-box-update /usr/local/sbin/ph-box-update
install -m 644 pi/systemd/ph-box.service pi/systemd/ph-box-update.service pi/systemd/ph-box-update.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now brickd.service ph-box-update.timer
systemctl enable ph-box.service
systemctl restart ph-box.service

echo
echo "Installed. 'ph-box status' shows the state, 'ph-box log -f' follows the log."
echo "A new box has to be approved once in the admin page of the server."
