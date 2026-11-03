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

## Demo

`make demo` seeds the boat register and replays one search. The boat is Sagar-4, three crew, out of Harnai in Ratnagiri. She is overdue by two hours. The last radio fix is a reef 6 km offshore. Four hours of daylight remain. The clock in the room template is 15 January 2026, 14:30 IST.

The replay posts into the live room and waits for each reply:

1. Ramesh reports that Sagar-4 is overdue and not back.
2. Context posts a one-screen summary: who is aboard, how long they have been out, the heading, the drift cone, and the daylight left. The message tags `@options`.
3. Options splits the cone into three sectors and posts exactly three plans. Each plan carries coverage, time, fuel, cost in INR, daylight margin, and risk flags. The message tags `@action`.
4. Action stores a pending Coast Guard and marine police escalation, matches the family to the scheme rules, and pins an operation checklist.
5. Sunita replies `Approved — escalation`. The thread refuses her. Escalation belongs to the community leader.
6. Ramesh replies `Approved — escalation`. The release is written into the audit with his name, role, message id, and time.
7. Sunita files `photo: https://example.test/reef.jpg`.
8. Ramesh posts `/audit`. Markdown and PDF land in `.runtime/exports/`.

The sign-off line uses an em dash. A hyphen does not count.
