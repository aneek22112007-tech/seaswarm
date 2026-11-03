# Deploy SeaSwarm on one VPS

SeaSwarm runs as Docker Compose behind Caddy. Mattermost is the room people open in a browser. Switch is the console and the agent bus. Caddy terminates HTTPS. Nothing in this stack uses AWS.

## Machine

Use a small Linux VPS with a public IPv4 address, Docker Engine, and the Docker Compose plugin. Open TCP 80 and 443. The Compose file publishes Mattermost on `127.0.0.1` only when you follow the binding below; the copy in the repo publishes `8065` and `8090` on all interfaces so a laptop demo works. On a VPS, change those two ports in `docker-compose.yml` to `127.0.0.1:8065:8065` and `127.0.0.1:8090:8090` so only Caddy is reachable from the internet.

## DNS

Point two names at the VPS:

- `sar.example.org` for the Mattermost room
- `switch.example.org` for the Switch console

## Files

```bash
sudo mkdir -p /opt/seaswarm
sudo rsync -a ./ /opt/seaswarm/ --exclude .venv --exclude .runtime --exclude .git
cd /opt/seaswarm
test -f .env || cp .env.example .env
```

Edit `.env`:

- `LLM_API_KEY` if you want the agents to phrase the computed figures. Leave it empty and they use the deterministic wording.
- `MATTERMOST_BOT_TOKEN` only if you already have one. Empty means the Switch process creates the bots.
- `MM_SERVICESETTINGS_SITEURL` is set in `docker-compose.yml`. Change it from `http://localhost:8065` to `https://sar.example.org` before the first boot. Mattermost stores that URL.

## Caddy

Install Caddy from the official package. Copy the site file and start it:

```bash
sudo cp /opt/seaswarm/deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Override the hostnames without editing the file:

```bash
sudo systemctl edit caddy
```

```
[Service]
Environment=SEASWARM_HOST=sar.example.org
Environment=SEASWARM_SWITCH_HOST=switch.example.org
```

## systemd

```bash
sudo cp /opt/seaswarm/deploy/seaswarm.service /etc/systemd/system/seaswarm.service
sudo systemctl daemon-reload
sudo systemctl enable --now seaswarm
```

The unit runs `docker compose up --build -d --wait` in `/opt/seaswarm`. `systemctl status seaswarm` stays active after the containers are healthy. `sudo systemctl stop seaswarm` runs `docker compose down`.

## First sign-in

Open `https://sar.example.org` and sign in as `ramesh` with the password in `.env` (`SeaSwarm-Ramesh-2026!` unless you changed it). The channel is `sar-harnai` on the `seaswarm` team. The Switch console is `https://switch.example.org`.

Then, on the VPS:

```bash
cd /opt/seaswarm
docker compose --profile demo run --rm demo
```

That seeds Sagar-4 and replays the scenario. The audit PDF is written under `.runtime/exports/`.

## What stays on the box

SQLite lives in `/opt/seaswarm/.runtime`. Mattermost's Postgres lives in a Docker volume. Back up both before you rebuild the machine. Do not commit `.env`.
