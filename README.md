# hinge-client

Typed, **async** Python client for the Hinge dating-app API — auth, recommendations,
profiles, rating, preferences, content, prompts, and Sendbird chat — built on `httpx`
and `pydantic`.

[![CI](https://github.com/Stupidoodle/hinge-client/actions/workflows/ci.yml/badge.svg)](https://github.com/Stupidoodle/hinge-client/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hinge-client.svg)](https://pypi.org/project/hinge-client/)
[![Python](https://img.shields.io/pypi/pyversions/hinge-client.svg)](https://pypi.org/project/hinge-client/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> ⚠️ **Unofficial & reverse-engineered.** For educational and research purposes only.
> Not affiliated with, authorized, or endorsed by Hinge / Match Group. Using it may
> violate Hinge's Terms of Service and can get your account banned. Use at your own risk.

## Install

```bash
pip install hinge-client
# or
uv add hinge-client
```

Requires Python 3.14+.

## Quickstart

```python
import asyncio

from hinge import HingeClient, configure_logging

configure_logging()  # opt-in colored console logs (no-op until you call it)


async def main() -> None:
    client = HingeClient("+15555550123")

    # --- auth (lifecycle lives on the client) ---
    await client.initiate_login()          # sends an SMS OTP
    await client.submit_otp(input("OTP: "))
    # If Hinge requires email 2FA, it raises HingeEmail2FAError carrying the
    # case id; complete it with: await client.submit_email_code(code, case_id)

    # --- data lives in resource namespaces ---
    recs = await client.recommendations.list()
    for feed in recs.feeds:
        for subject in feed.subjects:
            print(subject.subject_id)

    me = await client.profile.me()
    prefs = await client.profile.preferences()
    limit = await client.rating.limit()

    # human-readable enum labels, resolved in memory (no DB)
    print(client.catalog.enums.label("religions", 6))   # -> "Muslim"

    # the prompt library is fetched live and cached in memory
    prompts = await client.prompts.fetch()
    print(prompts.get_prompt_display_text("5b5799a05b162c2841794201"))


asyncio.run(main())
```

## API at a glance

**Client lifecycle** (auth & session): `initiate_login`, `submit_otp`, `submit_email_code`,
`ensure_fresh_token`, `is_session_valid`, `check_session_health`, `switch_session`,
`list_sessions`, `refresh_all_sessions`.

**Resource namespaces** (data):

| Namespace | Examples |
|---|---|
| `client.recommendations` | `list`, `repeat`, `standouts`, `standouts_v3`, `likes_received`, `matches`, `remove` |
| `client.profile` | `me`, `preferences`, `update`, `update_preferences`, `get`, `get_v2`, `content`, `traits`, `put_photos` |
| `client.rating` | `rate`, `respond`, `block`, `limit` |
| `client.content` | `settings`, `update_settings`, `evaluate_prompt`, `config`, `boost_status`, `store_account` |
| `client.prompts` | `fetch` |
| `client.chat` | `conversations`, `messages`, `send`, `react`, `mark_read`, `unread_count` |

**Catalog** (`client.catalog`): in-memory enum-label lookup (`enums.label/ordinal/is_valid`)
plus the live prompt library. **Logging**: structlog throughout; call
`configure_logging(level=..., pretty=...)` for the colored console renderer — the library
never configures global logging on import.

Sessions persist to a per-phone JSON file under `./hinge_sessions/` (override with the
`HINGE_SESSIONS_DIR` env var).

## Development

```bash
uv sync                # install
uv run pre-commit install
make check             # ruff + format + ty + leak-canary
make cov               # tests with the 100% branch-coverage gate
```

## License

MIT — see [LICENSE.md](LICENSE.md).

## Disclaimer

For educational and research purposes only. Don't be a creep. Don't use this for malicious
purposes. Not responsible if you get banned, cursed, ghosted into oblivion, or matched with
your cousin. If Hinge sends a C&D, they should also send a job offer.
