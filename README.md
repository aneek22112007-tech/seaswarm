<p align="center"><img src="docs/assets/hero.svg" alt="SeaSwarm — Agents propose. Humans dispose." width="100%"></p>

<p align="center">
<a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&pause=1200&color=3FA9F5&center=true&vCenter=true&width=720&lines=A+boat+is+overdue.+The+room+takes+over.;3+agents+propose.+Named+humans+decide.;No+sign-off%2C+no+escalation.;The+audit+trail+is+the+product." alt="Typing SVG"></a>
</p>

<p align="center">
<a href="https://aneek22112007-tech.github.io/seaswarm/"><img src="https://img.shields.io/badge/live-showcase-ffd54f?style=for-the-badge&logo=githubpages&logoColor=black" alt="Live showcase"></a>
<a href="https://github.com/aneek22112007-tech/seaswarm/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/aneek22112007-tech/seaswarm/ci.yml?branch=main&style=for-the-badge&label=CI" alt="CI"></a>
<img src="https://img.shields.io/badge/tests-121%20passing-2e7d32?style=for-the-badge&logo=pytest&logoColor=white" alt="121 tests passing">
<img src="https://img.shields.io/badge/python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
<img src="https://img.shields.io/badge/docker-compose-2496ed?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose">
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="MIT"></a>
<img src="https://img.shields.io/badge/UN%20SDG-14-0a97d9?style=for-the-badge" alt="SDG 14">
</p>

<h3 align="center">A Switch-powered coordination room for fishing-boat search-and-rescue and family support in coastal Maharashtra.</h3>

<p align="center"><a href="https://aneek22112007-tech.github.io/seaswarm/"><b>🌊 Open the 3D landing page</b></a> · <a href="https://aneek22112007-tech.github.io/seaswarm/replay/"><b>▶ Sagar-4 replay</b></a></p>

<p align="center"><a href="https://aneek22112007-tech.github.io/seaswarm/"><img src="docs/assets/landing-3d-hero.png" alt="SeaSwarm 3D landing page: Sagar-4 with SOS beacon on a dusk ocean" width="32%"></a> <a href="https://aneek22112007-tech.github.io/seaswarm/#gate"><img src="docs/assets/landing-3d-gate.png" alt="Human gate approval stamp" width="32%"></a> <a href="https://aneek22112007-tech.github.io/seaswarm/#audit"><img src="docs/assets/landing-3d-audit.png" alt="Search sectors cleared, audit trail" width="32%"></a></p>

---

When a boat is overdue, the village WhatsApp/Telegram group is where everyone already is, and it's where coordination breaks: the last-known position gets buried, boats search the same stretch twice, and nobody can say who approved the Coast Guard call. **SeaSwarm turns that same chat into a governed, auditable operations room.**

| | Agent | What it does |
|---|---|---|
| 🧭 | **Context** | Who is missing, since when, last fix, heading, drift cone, daylight left. Tags `@options`. |
| 🗺️ | **Options** | Exactly 3 search plans with coverage, time, fuel, INR cost, daylight margin and risk flags. Re-plans live; never sends two boats to one sector. Tags `@action`. |
| 🛟 | **Action** | Coast Guard / marine police escalation stored as *pending*, fishermen-welfare & insurance matching, pinned checklist, photo/GPS evidence. |

> [!IMPORTANT]
> 🔒 **Human gate:** nothing irreversible (escalation, spending, outside messages, scheme outreach, closing the search) happens until a named human with the right role replies `Approved — <action>`. Wrong role? The thread refuses it on screen.
>
> 📜 **The audit trail is the product.** Every assignment, correction and sign-off is timestamped and attributable. `/audit` exports Markdown + PDF.
>
> 🧪 **Deterministic.** Every number comes from pure functions in `core/`; the LLM only phrases it. 121 tests passing.

<p align="center"><img src="docs/assets/flow.svg" alt="Agents to human gate to audit" width="100%"></p>

## 🚀 Quickstart

```bash
git clone https://github.com/aneek22112007-tech/seaswarm && cd seaswarm
make up      # builds and waits for Postgres, Mattermost, Switch and the three agents
make demo    # seeds the register and replays the Sagar-4 search
```

- Mattermost: http://localhost:8065 · Switch console: http://localhost:8090
- Team `seaswarm`, channel `sar-harnai`
- `ramesh` / `SeaSwarm-Ramesh-2026!` (community leader) · `sunita` / `SeaSwarm-Sunita-2026!` (family representative)

`LLM_API_KEY` is optional: leave it empty and the room hears the same figures in fallback wording. Leave `MATTERMOST_BOT_TOKEN` empty and Switch creates the bots on boot. `make down` stops, `make test` / `make lint` run pytest, ruff and black.

## 🏗️ Architecture

```mermaid
flowchart LR
  subgraph Room["Mattermost #sar-harnai (Switch room)"]
    H1["👤 Ramesh<br/>community_leader"]
    H2["👤 Sunita<br/>family_rep"]
  end
  Room -- SSE events --> C["🧭 Context Agent"]
  Room -- SSE events --> O["🗺️ Options Agent"]
  Room -- SSE events --> A["🛟 Action Agent"]
  C & O & A -- HTTP posts --> Room
  C --> CORE["core/: drift · sectors · cost · risk · daylight · schemes_matcher"]
  O --> CORE
  A --> CORE
  A --> G{"🔒 gate.py<br/>pending → approved?"}
  G -- named role sign-off --> X["perform_irreversible<br/>(escalation, spend, outreach, close)"]
  C & O & A & G --> DB[("SQLite<br/>operations · sectors · approvals · events · evidence")]
  DB --> AU["📜 /audit → Markdown + PDF"]
  D["data/*.json<br/>weather · tide · schemes · boats"] --> CORE
```

## 🎬 Demo: Sagar-4

Sagar-4, three crew, out of Harnai in Ratnagiri, is overdue by two hours. The last radio fix is a reef 6 km offshore. Four hours of daylight remain. The room clock is 15 January 2026, 14:30 IST.

```mermaid
sequenceDiagram
  autonumber
  actor R as Ramesh (community_leader)
  actor S as Sunita (family_rep)
  participant C as Context
  participant O as Options
  participant A as Action
  participant G as Gate + Audit
  R->>C: "Sagar-4 overdue, not back"
  C->>O: summary · drift cone · daylight · @options
  O->>A: Options A / B / C with coverage, time, fuel, INR, risk · @action
  A->>G: store PENDING escalation, match schemes, pin checklist
  S->>G: "Approved — escalation"
  G-->>S: ⛔ refused: escalation belongs to the community leader
  R->>G: "Approved — escalation"
  G-->>R: ✅ released, written with name, role, message id, time
  S->>A: photo: https://example.test/reef.jpg
  R->>G: /audit
  G-->>R: Markdown + PDF in .runtime/exports/
```

<details>
<summary><b>📋 Plans the Options agent computes for the seeded room</b></summary>

| Option | Boats | Sectors | Time | Fuel | Cost | Daylight margin |
|---|---|---|---|---|---|---|
| A | Meerabai | Sector-2 | 1.45 h | 4.1 L | INR 389.50 | 2.55 h |
| B | Meerabai, Chandra-2 | Sector-2, Sector-1 | 1.65 h | 9.4 L | INR 893.00 | 2.35 h |
| C | Meerabai, Chandra-2, Harnai-Queen | all three | 1.95 h | 16.7 L | INR 1586.50 | 2.05 h |

Room commands: `reject option B`, `Sector-1 clear`, `reassign Meerabai to Sector-1`. The sign-off line uses an em dash; a hyphen does not count.
</details>

<details>
<summary><b>🔒 The human gate in detail</b></summary>

`agents/common/roles.py` maps Mattermost usernames to `community_leader`, `boat_owner`, `family_rep` and `volunteer`. Every irreversible action goes through `agents/common/gate.py` and is stored as a pending approval. The irreversible set is escalation, spending money, a message that leaves the room, scheme outreach and closing the search. Scheme outreach can be signed by the community leader or the family representative; the other four require the community leader.

`perform_irreversible` is the only release. It raises if the approval row is missing, pending or rejected, and refuses a second release of the same row. `tests/test_gate.py` and the action-agent test prove a pending escalation cannot run.
</details>

## 🔌 The kill switch

`make killswitch` runs the same two planning passes with and without room persistence:

| | `PERSISTENCE=on` ✅ | `PERSISTENCE=off` 💥 |
|---|---|---|
| Sectors after two passes | 3 (Sector-1/2/3 ×1) | **6** (each ×2) |
| Stored approvals | 1, approver `ramesh` | **0** |
| Sign-off reply | "ramesh (community_leader) approved escalation." | "No pending approval for escalation. The sign-off was not applied." |

Logs: [`logs/persistence-on.txt`](logs/persistence-on.txt) · [`logs/persistence-off.txt`](logs/persistence-off.txt). Remove the room and the operation collapses. **That is why Switch is the product.**

<details>
<summary><b>📜 Audit export</b></summary>

`/audit` in the room, and `make audit` on the host, write a timestamped Markdown file and a PDF listing the operation, sector assignments, every sign-off with approver and message id, the evidence, and the append-only event log.
</details>

<details>
<summary><b>💬 Optional Telegram / Discord doors</b></summary>

Off unless `TELEGRAM_ENABLED` or `DISCORD_ENABLED` is set. Start with `docker compose --profile adapters up -d adapters` (port 8091). A forwarded line keeps the sender's username, so `ramesh` on Telegram has the same role as in Mattermost.
</details>

## 🧰 Tech stack

<p>
<img src="https://img.shields.io/badge/Switch-protocol-0b1d3a?style=flat-square">
<img src="https://img.shields.io/badge/Mattermost-0058cc?style=flat-square&logo=mattermost&logoColor=white">
<img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
<img src="https://img.shields.io/badge/SQLAlchemy%20%2B%20Alembic-d71f00?style=flat-square">
<img src="https://img.shields.io/badge/SQLite-003b57?style=flat-square&logo=sqlite&logoColor=white">
<img src="https://img.shields.io/badge/Postgres-4169e1?style=flat-square&logo=postgresql&logoColor=white">
<img src="https://img.shields.io/badge/pytest-0a9edc?style=flat-square&logo=pytest&logoColor=white">
<img src="https://img.shields.io/badge/ruff%20%2B%20black-000?style=flat-square">
<img src="https://img.shields.io/badge/Caddy-1f88c0?style=flat-square&logo=caddy&logoColor=white">
<img src="https://img.shields.io/badge/GitHub%20Actions-2088ff?style=flat-square&logo=githubactions&logoColor=white">
</p>

## 🌐 Deploy

A single VPS with Docker and Caddy. The Caddyfile, systemd unit and steps are in [deploy/VPS.md](deploy/VPS.md). The 3D landing page (Three.js Gerstner ocean, GSAP scroll story, no build step) lives in [`docs/`](docs/) and is served by GitHub Pages at **https://aneek22112007-tech.github.io/seaswarm/**; the 2D replay is at [`/replay/`](https://aneek22112007-tech.github.io/seaswarm/replay/).

## 🌍 Impact & track fit

- **UN SDG 14 (Life Below Water)** and disaster management for small-scale fishers.
- One governance template (agents propose, humans dispose) for flood response, factory safety and health-worker rooms.
- **Best Business Workflow** (primary) · **Best Blog**: [BLOG.md](BLOG.md) · **Code with Wispr**.
- More detail: [ARCHITECTURE.md](ARCHITECTURE.md).

<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d5fa8,100:3fa9f5&height=120&section=footer&text=Agents%20propose.%20Humans%20dispose.&fontSize=22&fontColor=ffffff" width="100%"></p>

<p align="center">MIT © aneek22112007-tech</p>
