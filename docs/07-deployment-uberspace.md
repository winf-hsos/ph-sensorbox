# Deployment on Uberspace 8

Status: written on 2026-10-28 from the [Uberspace 8 manual](https://u8manual.uberspace.de/) (version 8.0.98 of 2026-10-05) and **not yet tested**, because access to the Asteroid has not been handed over. Steps marked **(check)** rely on a form of a command that the manual does not show exactly.

## Frame

The server runs on the Uberspace 8 Asteroid `hsos`, which is a shared workbench for several small web apps without personal data. For this project that means:

- its own subdomain `ph.hsos.uber.space`, its own port, its own service, its own SQLite file and its own secrets;
- no assumption to be alone: all apps of the Asteroid share 1500 MiB of memory and 300 % CPU ([resources](https://u8manual.uberspace.de/basics_resources/)). A single uvicorn worker with SQLite is small; the memory it really uses should be checked after the start;
- idle HTTP connections are closed after three minutes ([web backends](https://u8manual.uberspace.de/web_backends/)); the live view uses server-sent events with a keep-alive every 30 s.

Chosen values (change them if they collide with another app on the Asteroid, see `uberspace web backend list`):

| Item | Value |
|---|---|
| Directory | `/home/hsos/ph-sensorbox/` with `server/` (code), `data/` (database), `admin_password` |
| Port | `8710` |
| Service name | `ph-sensorbox` |
| Subdomain | `ph.hsos.uber.space` |

## 1. Copy the code

The repository has no remote yet, so the server directory is copied from the local checkout. The local virtual environment, database and password stay behind.

```bash
rsync -a --exclude .venv --exclude __pycache__ --exclude "*.sqlite3*" --exclude .admin_password server/ hsos@<host>.uberspace.de:ph-sensorbox/server/
```

`<host>` is the host the Asteroid lives on ([SSH](https://u8manual.uberspace.de/basics_ssh/)). Once the project has a Git remote, a `git clone` on the Asteroid replaces this step.

## 2. Python environment

Uberspace 8 provides Python 3.14 as `python3` ([Python](https://u8manual.uberspace.de/lang_python/)), the same version the server is developed with.

```bash
cd ~/ph-sensorbox/server
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
mkdir -p ~/ph-sensorbox/data
```

## 3. Admin password

The password lives in a file that only the account can read, so it appears neither in the service definition nor in the process list.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))" > ~/ph-sensorbox/admin_password
chmod 600 ~/ph-sensorbox/admin_password
```

## 4. Service

`uberspace service add` writes a systemd user unit to `~/.config/systemd/user/`, enables it and starts it ([services](https://u8manual.uberspace.de/services_systemd/)). The application has to listen on `0.0.0.0` or `::`, because `127.0.0.1` is not reachable for the web frontend.

```bash
uberspace service add ph-sensorbox "/home/hsos/ph-sensorbox/server/.venv/bin/python -m uvicorn phbox_server.main:create_app --factory --host 0.0.0.0 --port 8710" \
  --env PHBOX_DB=/home/hsos/ph-sensorbox/data/phbox.sqlite3 \
  --env PHBOX_ADMIN_PASSWORD_FILE=/home/hsos/ph-sensorbox/admin_password \
  --workdir /home/hsos/ph-sensorbox/server
```

Operation:

```bash
systemctl --user status ph-sensorbox
systemctl --user restart ph-sensorbox
journalctl --user --unit ph-sensorbox --since '10 minutes ago'
```

The manual gives no example for automatic restarts after a crash. If the service does not come back by itself, `Restart=on-failure` and `RestartSec=5` go into the `[Service]` section of `~/.config/systemd/user/ph-sensorbox.service`, followed by `systemctl --user daemon-reload` and a restart **(check)**.

## 5. Subdomain and web backend

```bash
uberspace web domain add ph.hsos.uber.space
uberspace web backend add ph.hsos.uber.space/ port 8710      # (check)
uberspace web backend list
```

The manual documents subdomains of `<user>.uber.space` and backends in the form `domain/path`, but shows no example for the root path of a subdomain; `uberspace web backend list` shows whether the route took effect. HTTPS comes from Let's Encrypt through the Caddy front end ([HTTP stack](https://u8manual.uberspace.de/background_http/)).

## 6. Check

1. `https://ph.hsos.uber.space/` shows the overview, `https://ph.hsos.uber.space/docs` the API.
2. `https://ph.hsos.uber.space/admin` asks for the user `admin` and the password from step 3.
3. On the bench: `python tools/bench_box.py --server https://ph.hsos.uber.space --box bench`, then approve the box under `/admin`.
4. The overview updates live within a minute and keeps updating for more than three minutes, which shows that the keep-alive gets through the front end (not covered by the manual) **(check)**.
5. Memory use: `systemctl --user status ph-sensorbox` shows it.

## 7. Updates

```bash
rsync -a --exclude .venv --exclude __pycache__ --exclude "*.sqlite3*" --exclude .admin_password server/ hsos@<host>.uberspace.de:ph-sensorbox/server/
ssh hsos@<host>.uberspace.de 'cd ph-sensorbox/server && .venv/bin/python -m pip install -r requirements.txt && systemctl --user restart ph-sensorbox'
```

Boxes keep their readings while the server restarts and upload them afterwards (see `06-box-protocol.md`).

## 8. Backups

Uberspace keeps daily and weekly snapshots of the home directory under `/backup` ([backups](https://u8manual.uberspace.de/basics_backup/)); directories named `tmp`, `cache`, `.cache` or `no_backup` and `~/logs` are excluded, which is why the database lives in `~/ph-sensorbox/data/`. The manual says nothing about SQLite, and a snapshot taken during a write may not be consistent **(inference)**. Still open: a daily consistent copy with SQLite's backup function into `~/ph-sensorbox/data/backup/`, and how to schedule it on Uberspace 8 (systemd timer or cron, not checked).

## Removal

```bash
uberspace web backend del ph.hsos.uber.space/      # (check)
uberspace web domain del ph.hsos.uber.space
uberspace service del ph-sensorbox
```

The data in `~/ph-sensorbox/data/` stay until they are deleted by hand.
