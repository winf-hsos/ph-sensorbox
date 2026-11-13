# Raspberry Pi as box computer

Status: running on a Raspberry Pi 3B (`ph-box-1`) since 2026-11-13. Until the ESP32 firmware exists, a Raspberry Pi takes the place of the laptop that ran `tools/bench_box.py`: the Master Brick hangs on the Pi's USB port, brickd talks to it, and the service `ph-box` measures and uploads over Wi-Fi with the [box protocol](06-box-protocol.md). The server does not see a difference.

```
Analog In 3.0 ─┐
               ├─ Master Brick ── USB ── Raspberry Pi (brickd, ph-box) ── Wi-Fi ── HTTPS ── server
Thermocouple ──┘
```

A Pi draws much more power than an ESP32, so it suits places with a socket; battery operation stays the ESP32's job.

## 1. Prepare the SD card

Raspberry Pi Imager, device "Raspberry Pi 3" (or newer), operating system "Raspberry Pi OS (other)" → "Raspberry Pi OS Lite (64-bit)". 16 GB is plenty. In the customisation:

- hostname, for example `ph-box-1`; it becomes the box name on the server
- user name and password
- Wi-Fi with country `DE`; a Pi 3B only sees 2.4 GHz networks
- SSH with public-key authentication only

Power: micro-USB, 5 V / 2.5 A for a Pi 3B. `vcgencmd get_throttled` must answer `0x0`; anything else means the supply is too weak.

## 2. Network requirements

| Direction | Purpose |
|---|---|
| outgoing TCP 443 | upload to the server, updates from GitHub, Tinkerforge packages, Raspberry Pi Connect |
| outgoing UDP 123 | NTP; the Pi has no real-time clock and waits for the time before measuring |
| outgoing UDP 3478 (and the TURN ports) | only for Raspberry Pi Connect |

## 3. Install

On the Pi:

```
sudo apt-get install -y git
sudo git clone https://github.com/winf-hsos/ph-sensorbox.git /opt/ph-sensorbox
sudo /opt/ph-sensorbox/pi/install.sh
```

The installer adds the Tinkerforge APT repository and installs `brickd` and `python3-tinkerforge` from it, creates the system user `phbox`, writes `/etc/ph-box/config.toml` with the hostname as box name, installs the commands `ph-box` and `ph-box-update` and enables the services. Running it again keeps the configuration, the secret and the backlog.

The box then registers as `pending`; approve it once in the admin page of the server.

| Path | Content |
|---|---|
| `/opt/ph-sensorbox` | checkout of this repository, owned by root |
| `/etc/ph-box/config.toml` | server, box name, optional Bricklet UIDs (template `pi/config.example.toml`) |
| `/var/lib/ph-box/` | `secret` (box secret, mode 600), `backlog.jsonl` (records not yet confirmed), `version`, `failed-versions` |
| `/run/ph-box/state.json` | current state, read by `ph-box status` and the updater |

## 4. Everyday commands

| Command | Effect |
|---|---|
| `ph-box status` | version, service, clock, approval, Brick, last record, last upload, backlog, last error |
| `ph-box log` / `ph-box log -f` | the last messages of the service and the updater / follow them |
| `ph-box update` | look for a new release now |
| `ph-box restart` | restart the service |

The output is German because it is meant for the people who run the box.

## 5. What the service survives

- **Brick unplugged:** it drops the interrupted record and resumes when the Brick answers; the outage is a gap in the data.
- **No network or server:** records stay in `backlog.jsonl` (at most 100,000, about eleven days at 10 s) and are sent in batches of 1,000 when the server is back.
- **Restart or power cut:** every record is appended to `backlog.jsonl` when it is taken, so nothing older than the record in progress is lost.
- **No time yet after boot:** it waits for NTP before the first record.
- **Crash:** systemd restarts it after 10 s.

## 6. Updates

The Pi fetches updates itself, which also works where nobody can reach it from outside. `ph-box-update.timer` runs `ph-box-update` 15 minutes after boot and once a day around 03:00. It fetches the tags from GitHub and switches only to **release tags** of the form `box-v1.2.0`, never to an arbitrary commit on `main`. A release is therefore made by pushing a tag:

```
git tag box-v1.0.0
git push origin box-v1.0.0
```

After switching, the updater restarts the service and waits 60 s. The new version counts as good if the service is still active, has not been restarted by systemd in the meantime and reports the new version in `state.json`. Otherwise the updater checks out the previous version again, restarts it and writes the tag into `/var/lib/ph-box/failed-versions`, so the timer does not retry it every day. Both paths were tested on `ph-box-1` on 2026-11-13 with a local test origin.

The version a box runs is part of its `firmware` field (`ph-box box-v1.0.0`) and shows in the admin page of the server.

The updater only changes the checkout. A release that needs new system packages, changed systemd units or a new `ph-box` command needs `sudo /opt/ph-sensorbox/pi/install.sh` once on the Pi.

## 7. Remote access

SSH works in the same network. For a Pi in a network that cannot be reached from outside, Raspberry Pi Connect (package `rpi-connect-lite`, preinstalled on Raspberry Pi OS Lite) offers a remote shell in the browser at connect.raspberrypi.com, signed in with a Raspberry Pi ID. It needs the user to linger, otherwise the Pi is unreachable after a reboot:

```
sudo loginctl enable-linger <user>
rpi-connect on
rpi-connect signin     # prints a link to confirm with the Raspberry Pi ID
```

In that shell, `ph-box status` and `ph-box update` are all that is needed for routine checks.
