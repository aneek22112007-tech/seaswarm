# SeaSwarm

SeaSwarm is a Switch-powered room where three agents and the people running a search coordinate a fishing-boat search, and support the family, in coastal Maharashtra. Agents suggest and keep track. Humans make the decisions. Nothing irreversible leaves the room until a named person signs off in the thread.

The product is the audit trail.

## Run the stack

Docker is the runtime. Copy `.env.example` to `.env` yourself, or let `make up` do it the first time. Set `LLM_API_KEY` when you want the model to phrase figures that `core/` has already computed. Leave the key empty and the room hears that same wording from the fallback. Leave `MATTERMOST_BOT_TOKEN` empty and Switch creates the Mattermost bots on boot.

```bash
make up
```

`make up` builds the images and waits until Postgres, Mattermost, Switch, and the three agents are healthy.

- Mattermost: http://localhost:8065
- Switch console: http://localhost:8090
- Team `seaswarm`, channel `sar-harnai`
- `ramesh` / `SeaSwarm-Ramesh-2026!` (community leader)
- `sunita` / `SeaSwarm-Sunita-2026!` (family representative)

`make down` stops the containers. `make test` and `make lint` run pytest, ruff, and black.
