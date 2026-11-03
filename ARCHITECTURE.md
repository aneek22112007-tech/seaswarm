# Architecture

SeaSwarm is one Mattermost channel, a Switch process in front of it, three Python agents, and a SQLite file. The agents subscribe to the room over server-sent events and answer over HTTP. Humans speak in Mattermost. The bridge copies those posts onto the Switch hub, and copies agent replies back.

Numbers come from pure functions in `core/`. Drift, sector coverage, fuel, cost, daylight margin, risk flags, and scheme eligibility are computed before any sentence is written. The model, when a key is configured, may only rephrase a reply that still contains those figures. `SEASWARM_SEED` fixes the small random phase of the drift polygon so a demo can be repeated. The cone center does not depend on the seed.

## The room
