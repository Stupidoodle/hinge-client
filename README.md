# (Un)Hinge(d) — Reverse-Engineered Hinge API Client 🔓💀

I got bored on a Saturday night and my DMs were a barren wasteland. Four hours later, this repo existed. By the time my dopamine wore off, it had a typed Python client, a FastAPI surface, a SQLite mirror of every match's chat, real-time Sendbird events, and a rejection-detection scheduler.

This is a fully `async`, typed, DDD-layered Python client for Hinge's private mobile API, complete with a FastAPI command center. I reverse-engineered their REST surface + Sendbird WebSocket because I was convinced my dating life could be optimized with a bit of code. Turns out, I was right.

### The WTF Moment: No SSL Certificate Pinning

Yeah, you read that right.

One of the biggest dating apps in 2025, handling millions of users' data, **has no SSL certificate pinning** on their main API. I was geared up for a multi-day war with Frida, Objection, and a mountain of reverse-engineering tooling. The front door was wide open. 💀

### The Strategic Advantage

Hinge's app is a slot machine — one profile at a time, forcing you to waste your 8 daily likes on whoever the algorithm shows you first. Low-IQ gameplay. This tool gives you two superpowers:

1. **Full deck visibility** — fetches your *entire* daily recommendation queue at once and surfaces it via REST + WebSocket. See all 30-50 candidates upfront and pick strategically instead of reacting to the algorithm's first pull.
2. **Multi-account geo-arbitrage** — keep multiple authenticated sessions on disk (`hinge_sessions/<phone>.json`) and switch between them at runtime. Useful when you want to look at the pool in a different region without disrupting your main account.

### Disclaimer 🙏

For educational and research purposes only. Don't be a creep. Don't use this for malicious purposes. Not responsible if you get banned, cursed, ghosted into oblivion, or matched with your cousin. If Hinge sends a C&D, they should also send a job offer.

---

## Features

- **Full authentication flow** — SMS OTP, email 2FA, token refresh, per-phone session persistence
- **Recommendation feed** — v3 endpoints, paginated, with rating_token tracking
- **Voting** — like (photo + prompt comment), skip, send_note, block_match
- **Matches** — inbox listing, expired/active filtering, rematch
- **Chat** — full Sendbird mirror to SQLite (`hinge_chat_channels`, `hinge_chat_messages`), 60-second sync loop, send/typing/read endpoints
- **Real-time WebSocket bridge** — Sendbird events (messages, typing indicators, read receipts) forwarded to a single fan-out endpoint (`/api/v1/hinge/ws/chat`)
- **Profile management** — get/update self, photos CRUD, prompt answers, freshstart, content settings, like-limit quota
- **Preferences** — get/update full filter set (age, height, lifestyle, dealbreakers, gendered ranges)
- **Analytics** — daily decisions, rejection-scan history, dashboard aggregates
- **Rejection scanning** — periodically exhausts the feed and marks no-longer-appearing profiles in the DB (rejected vs gone vs passed)
- **Rule-based scorer** — pluggable profile scorer (`HingeScorerPort`), wired through the bootstrap container

---

## Architecture

Domain-driven design with ports & adapters under `src/hinge/`:

```
src/hinge/
├── domain/           # Pure business logic (dataclasses + ABCs)
│   ├── models/       # HingeProfile, HingeChatChannel, HingeDecision, ...
│   ├── ports/        # HingeApiPort, HingeProfileRepo, HingeChatRepo, ...
│   └── enums.py      # ID → display-label resolution tables
├── application/
│   └── services/     # ChatSyncService, SendbirdWsBridge, RejectionScan
├── infrastructure/
│   ├── hinge/        # HingeApiAdapter (wraps HingeClient)
│   ├── db/           # SQLAlchemy tables, mappers, repos, UoW
│   └── scoring/      # HingeRuleBasedScorer
├── api/              # FastAPI routes (auth, recs, chat, profile, ...)
├── core/             # Settings (pydantic-settings), structlog config
├── client.py         # Low-level reverse-engineered HingeClient
├── models.py         # Pydantic wire schemas
├── enums.py          # Wire-level IntEnums
├── bootstrap.py      # Composition root: bootstrap_hinge() → HingeContainer
└── main.py           # FastAPI app + lifespan
```

Schema is managed by Alembic (`migrations/`). The bootstrap never issues DDL — it only wires already-defined ports and adapters.

---

## Setup

You need [`uv`](https://github.com/astral-sh/uv) (not pip).

```bash
# 1. Install deps
make setup                                         # or: uv sync && uv run pre-commit install

# 2. Configure (.env at repo root)
cat > .env <<'EOF'
HINGE_PHONE_NUMBER="+49123456789"
DATABASE_URL="sqlite:///hinge.db"
DEBUG=false
EOF

# 3. Migrate the DB
make db-upgrade                                    # or: uv run alembic upgrade head

# 4. Run the API
uv run uvicorn hinge.main:app --reload --port 8000
```

Once running, open `http://localhost:8000/docs` for the full OpenAPI surface.

### Auth flow

```bash
# Start SMS OTP flow
curl -X POST localhost:8000/api/v1/hinge/auth/connect \
    -H 'Content-Type: application/json' -d '{"phone": "+49123456789"}'

# Submit OTP from SMS
curl -X POST localhost:8000/api/v1/hinge/auth/otp \
    -H 'Content-Type: application/json' -d '{"otp": "123456"}'

# If email 2FA kicks in
curl -X POST localhost:8000/api/v1/hinge/auth/email-code \
    -H 'Content-Type: application/json' -d '{"code": "ABCD"}'
```

Sessions are persisted per-phone in `hinge_sessions/<phone>.json` and reloaded on subsequent boots.

---

## Development

```bash
make test          # pytest tests/ (in-memory SQLite, no external calls)
make lint          # ruff
make format        # ruff format + ruff --fix
make typecheck     # mypy src/
make pre-commit    # run all hooks

# Add a runtime dep
uv add <package>

# Add a dev dep
uv add --group dev <package>

# Generate a new migration
make db-migrate msg="add hinge_foo column"
```

**NEVER** hand-edit `pyproject.toml` dependency entries — always go through `uv add` / `uv remove`. See `CLAUDE.md` for the full rule set Claude Code follows when working on this repo.

---

## Hinge API Surface

Base URL: `https://prod-api.hingeaws.net`

| Action | Method | Endpoint |
|---|---|---|
| Request OTP | POST | `/identity/request-otp` |
| Submit OTP | POST | `/identity/submit-otp` |
| Submit email 2FA | POST | `/identity/submit-email-2fa` |
| Recommendations (v3) | POST | `/rec/recommendations` |
| Standouts (v3) | POST | `/standouts/v3` |
| Profile (full) | POST | `/profile/v2` |
| Quick profile batch | POST | `/profile/quick` |
| Rate (like/skip/note) | POST | `/rate/v2` |
| Matches inbox | GET | `/match/inbox` |
| Self profile | GET | `/user` |
| Update self | POST | `/user/update` |
| Preferences | GET | `/preferences` |
| Update preferences | POST | `/preferences/update` |
| Like-limit quota | GET | `/likelimit` |
| Prompts library | POST | `/prompts/all` |

Chat is delegated to Sendbird (app ID `3CDAD91C-1E0D-4A0D-BBEE-9671988BF9E9`). The `SendbirdWsBridge` pins TLS to certifi's CA bundle to avoid the system trust store getting in the way.

---

## To-Do

- [ ] **The Rizzler Agent™** — LLM that uses conversation history to draft replies in your own voice
- [ ] **Type Detector ML model** — automate skip/like based on hyper-niche aesthetic preferences
- [ ] **Multi-region pooling dashboard** — visualize cross-account feed differences

Go break some shit. Or get a date. Whatever.
