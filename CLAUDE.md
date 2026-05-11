# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reverse-engineered Hinge mobile API client (the dating app). Uses the `prod-api.hingeaws.net` REST surface plus the Sendbird realtime layer for chat. The library exposes auth, feed/recommendations, voting, profile, preferences, matches, and chat through typed async Python (httpx + websockets). Targets parity with the iOS Hinge app, version `9.82.0` build `11616`.

The project is organised as a domain library plus an optional FastAPI surface and a local SQLite store that mirrors Sendbird channels and messages.

## Commands

**Important**: Always use `uv run` (never bare `python` or `python3`). **NEVER** manually create or edit `pyproject.toml` dependency entries — always use uv commands (`uv add <package>`, `uv add --group dev <package>`, `uv remove <package>`).

### Setup & Dependencies
```bash
uv sync                           # Install all dependencies
uv run pre-commit install         # Install git hooks
make setup                        # Full setup: deps + hooks
uv add <package>                  # Add a new runtime dependency
uv add --group dev <package>      # Add a dev dependency
```

### Running Tests
```bash
make test                                                        # Run all tests
uv run pytest tests/path/to/test_file.py::TestClass::test_name   # Single test
```

### Linting & Formatting
```bash
make lint                          # Ruff linter
make lint-fix                      # Ruff linter with auto-fix
make format                        # Ruff format + lint fix
make typecheck                     # Mypy type checking
make pre-commit                    # Run all pre-commit hooks on all files
```

### Running Python
```bash
uv run python -c "from hinge.client import HingeClient; ..."   # One-liners
uv run python script.py                                         # Scripts
```

## Architecture

### Layered DDD (Hexagonal / Ports & Adapters)

The codebase follows Domain-Driven Design with clear layer separation under `src/hinge/`:

- **`domain/`** — Pure business logic, no framework dependencies
  - `models/` — Domain dataclasses (`HingeProfile`, `HingeChatChannel`, `HingeChatMessage`, `HingeDecision`, `HingeMatch`, `Recommendation`, `HingeSwipeSession`, `HingeLikeLimit`)
  - `ports/` — Abstract interfaces (`HingeApiPort`, `HingeProfileRepo`, `HingeDecisionRepo`, `HingeSessionRepo`, `HingeChatRepo`, `HingeScorerPort`, `HingeUnitOfWorkPort`)

- **`application/`** — Use cases and orchestration
  - `services/` — `ChatSyncService` (Sendbird → DB mirror), `SendbirdWsBridge` (realtime events), `RejectionScan` + `RejectionScheduler` (profile rejection detection)

- **`infrastructure/`** — Concrete implementations of ports
  - `hinge/` — `HingeApiAdapter` wraps `HingeClient`, maps Pydantic → domain models
  - `db/` — SQLAlchemy tables, imperative mappers, repositories, `UnitOfWork`
  - `scoring/` — `HingeRuleBasedScorer` (rule-based profile scoring)

- **`api/`** — FastAPI routes (`/api/v1/hinge/...`) for auth, recommendations, likes, matches, chat, profile, preferences, analytics

- **`core/`** — Cross-cutting concerns
  - `config.py` — Pydantic Settings with `.env` support (`get_settings()` cached via `@lru_cache`)
  - `logging_config.py` — structlog setup

- **`client.py`** — The low-level reverse-engineered `HingeClient` (httpx + websockets)
- **`models.py`** — Pydantic API schemas (UserProfile v2/v3, RecommendationsResponse, CreateRate, etc.)
- **`enums.py`** — Hinge field enums (DatingIntentionEnum, EducationAttainedEnum, etc.) with base-preference fallbacks
- **`prompts_manager.py`** — Dynamic prompt catalogue (Hinge's question library)
- **`bootstrap.py`** — Composition root: `bootstrap_hinge()` wires the full `HingeContainer`

### Key Patterns

**Composition Root (`bootstrap.py`)**: All dependency wiring happens here. API/CLI/tests call `bootstrap_hinge(session_factory, phone_number)` to get a fully-wired `HingeContainer`.

**Ports & Adapters**: Every external dependency (Hinge API, Sendbird, DB) is an abstract interface in `domain/ports/`. Infrastructure provides concrete implementations. Testing swaps in fakes — no mocking libraries needed.

**Unit of Work**: Transactional boundaries via `HingeSqlAlchemyUnitOfWork`. Each UoW aggregates profile, decision, session, and chat repos. Application services call `with uow: ...` for atomic operations.

**Imperative ORM Mapping**: Domain models stay framework-free. SQLAlchemy `Table` definitions live in `infrastructure/db/tables/`; mappers register them in `infrastructure/db/mappers/__init__.py` (`start_mappers()`).

## Hinge API

Base URL: `https://prod-api.hingeaws.net`

### Authentication

Phone-based OTP with optional email 2FA. JWT tokens auto-refresh.

| Action | Method | Endpoint |
|---|---|---|
| Request OTP | POST | `/identity/request-otp` |
| Submit OTP | POST | `/identity/submit-otp` |
| Submit email 2FA | POST | `/identity/submit-email-2fa` |
| Refresh token | POST | `/identity/refresh` |

### Core Endpoints (Reverse-Engineered)

| Action | Method | Endpoint |
|---|---|---|
| Recommendations (v3) | POST | `/rec/recommendations` |
| Standouts (v3) | POST | `/standouts/v3` |
| Profile lookup | POST | `/profile/v2` |
| Quick profile (batch) | POST | `/profile/quick` |
| Rate (like/skip/note) | POST | `/rate/v2` |
| Matches | GET | `/match/inbox` |
| Self profile | GET | `/user` |
| Update self | POST | `/user/update` |
| Preferences | GET | `/preferences` |
| Update preferences | POST | `/preferences/update` |
| Like limit | GET | `/likelimit` |
| Prompts library | POST | `/prompts/all` |

### Sendbird (Chat)

Chat is delegated to Sendbird (app id: `3CDAD91C-1E0D-4A0D-BBEE-9671988BF9E9`).

- REST: `https://api-{app_id_lower}.sendbird.com`
- WebSocket: `wss://ws-{app_id_lower}.sendbird.com`

Authentication uses a Sendbird JWT issued by Hinge during auth. Hinge mirrors channels and messages via `SERVER_GET_USER_LIST`-style aggregation; locally we sync them into `hinge_chat_channels` and `hinge_chat_messages` every 60s and via push events from `SendbirdWsBridge`.

## Database & Persistence

SQLite (`hinge.db`) via SQLAlchemy 2.0. Alembic for migrations.

**Persisted tables:**
- `hinge_profiles` — every observed user profile with photos, prompts, lifestyle fields, miss/rejection tracking
- `hinge_decisions` — like/skip/note history with score and reasoning
- `hinge_swipe_sessions` — per-run analytics (profiles seen, likes sent, score histogram)
- `hinge_chat_channels` — Sendbird channel mirror (counterparty subject_id, unread counts, last-message metadata, orphan flag for unmatches)
- `hinge_chat_messages` — Sendbird message mirror with file/voice metadata

## Testing

- **Unit/integration tests** (`tests/hinge/`): in-memory SQLite, fake `HingeApiPort` implementation. No external API calls.
- **Real-API tests**: any test that hits Hinge or Sendbird directly should be marked `@pytest.mark.integration` and gated behind credentials.
- Fixtures (`tests/hinge/fixtures/`) store representative Sendbird JSON payloads.

## Configuration

Settings loaded via Pydantic Settings (`hinge.core.config.get_settings`) with priority: env vars > `.env` file > defaults. Key fields:

- `BASE_URL`, `SENDBIRD_APP_ID`, `SENDBIRD_API_URL`, `SENDBIRD_WS_URL`
- `HINGE_APP_VERSION`, `HINGE_BUILD_NUMBER`, `OS_VERSION`
- `DATABASE_URL` (default `sqlite:///hinge.db`)
- `DEBUG`

## Code Style

- Python 3.14, line length 88
- Ruff for linting (rules: E, F, C, D, B, I, Q) and formatting
- Double quotes, trailing commas enforced
- Google-style docstrings (per ruff D rules)

## Python 3.14 — CRITICAL RULES

### Type Hints
**ALWAYS** use built-in types. **NEVER** import from `typing` for these:
- `list[X]` not `List[X]`
- `dict[K, V]` not `Dict[K, V]`
- `X | Y` not `Union[X, Y]`
- `X | None` not `Optional[X]`

Still valid from `typing`: `Any`, `Literal`, `TypeVar`, `Protocol`, `TypedDict`.

### Annotations & Forward References (PEP 649)
- **NEVER** use `from __future__ import annotations` — this is Python 3.14, not needed
- **NEVER** use string-quoted type annotations (e.g., `"MyClass"`) — forward references resolve natively in 3.14 via PEP 649
- **NEVER** use `if TYPE_CHECKING:` import guards — all annotations are evaluated lazily, circular imports in type hints are not an issue
- **NEVER** wrap type hints in quotes for any reason — if you see `def foo() -> "Bar":` that is WRONG, it should be `def foo() -> Bar:`

If you violate any of these rules, the code review will reject your PR.

## Disclaimer

For educational and research purposes only. Don't be a creep.
