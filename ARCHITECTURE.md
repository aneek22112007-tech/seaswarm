# Architecture

SeaSwarm is one Mattermost channel, a Switch process in front of it, three Python agents, and a SQLite file. The agents subscribe to the room over server-sent events and answer over HTTP. Humans speak in Mattermost. The bridge copies those posts onto the Switch hub, and copies agent replies back.

Numbers come from pure functions in `core/`. Drift, sector coverage, fuel, cost, daylight margin, risk flags, and scheme eligibility are computed before any sentence is written. The model, when a key is configured, may only rephrase a reply that still contains those figures. `SEASWARM_SEED` fixes the small random phase of the drift polygon so a demo can be repeated. The cone center does not depend on the seed.

## The room

```mermaid
flowchart TD
  people[Ramesh and Sunita] --> mm[Mattermost channel sar-harnai]
  mm --> bridge[Switch bridge]
  bridge --> hub[Switch hub]
  hub --> context[Context agent]
  hub --> options[Options agent]
  hub --> action[Action agent]
  context --> core[Pure functions in core]
  options --> core
  action --> core
  action --> gate[Human gate]
  gate --> db[(SQLite audit)]
  context --> db
  options --> db
```

Context listens for "overdue", "SOS", "not back", and "missing". It loads the boat, the last position, the mock wind and tide, and posts the drift cone. Options turns that cone into three sectors and three plans, and it re-plans when someone clears a sector, reassigns a boat, or rejects option B. It refuses a second boat on a sector that already has one, and it says so in the thread. Action drafts the escalation, runs the scheme rules, pins the checklist, and asks again on the follow-up interval. The default interval is 30 minutes. The demo does not wait that long. The checklist shows the next prompt from the scenario clock.

## Human gate

```mermaid
sequenceDiagram
  participant Action
  participant Room
  participant Ramesh
  participant Gate
  Action->>Room: PENDING escalation card
  Ramesh->>Room: Approved, em dash, escalation
  Room->>Gate: username, role, message id
  Gate->>Room: audit row gated_executed
```

An approval row starts at `pending`. A reply of the form `Approved — <action>` from an allowed role stores the approver, the role, the message id, and the time, and sets the row to `approved`. A person without that role leaves the row pending. The thread says `Only community_leader can approve escalation.` Closing the search updates the operation status only after `perform_irreversible` has accepted the row.

Events are append-only. SQLAlchemy rejects updates and deletes on that table.

## Tables

`operations`, `boats`, `positions`, `sectors`, `approvals`, `events`, and `evidence` live in one SQLite file. Agents share it with WAL. `make audit` reads those tables directly, including rows that the kill switch would hide from the agents.

## Kill switch

`PERSISTENCE=off` makes reads of operations, events, positions, sectors, and approvals look empty. Sector inserts still happen, so a second plan duplicates rows. Approval writes are skipped, so a sign-off has nowhere to land. `scripts/killswitch_demo.py` records both modes.
