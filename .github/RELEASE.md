# Release & security runbook

## One-time setup (before the first publish)
- PyPI account with **hardware / WebAuthn 2FA** enabled.
- Register a **PyPI Trusted Publisher** for this repo: project `hinge-client`,
  workflow `release.yml`, environment `pypi`. (No API tokens — OIDC only.)
- Create a **protected GitHub Environment** named `pypi` with a required reviewer.
- Confirm the repo is safe to make public (run the go-public audit below).

## Go-public audit (do BEFORE flipping the repo public)
History is forever, so audit it, not just the working tree:
```bash
git log --all -p | grep -iE 'apk|dk8|qoh|decompil|jadx|smali|bumble|hinge-decompiled' || echo CLEAN
```
- Must print `CLEAN`. If anything matches, rewrite history (e.g. `git filter-repo`) or start
  a fresh history before going public.
- Confirm `.env` was never committed and `reversal/` was never tracked
  (`git log --all -- reversal/ .env` should be empty).
- The leak-canary (`tests/test_no_secrets.py`) must pass in CI.

## Cut a release (automated — python-semantic-release)
Releases are driven by **conventional commits** — you do NOT tag by hand. Just push to `master`:
- `fix:` -> patch (0.1.0 -> 0.1.1); `feat:` -> minor (0.1.0 -> 0.2.0);
  `feat!:` / `BREAKING CHANGE:` -> minor while in 0.x (major once >= 1.0.0);
- `docs:` / `chore:` / `ci:` / `test:` / `refactor:` / `style:` -> no release.

On push to `master`, `.github/workflows/release.yml`:
1. runs python-semantic-release: computes the next version, updates `CHANGELOG.md`, commits, tags
   `vX.Y.Z`, and creates the GitHub Release;
2. only if a release was made, builds and OIDC-publishes to PyPI with PEP 740 attestations, gated
   behind the protected `pypi` environment (your one-click approval).

- Preview the next version without changing anything:
  `uvx python-semantic-release version --print`
- Verify after publish: `uvx --from hinge-client python -c "import hinge"`.

## Incident response
- Malicious/bad release: **yank** the version on PyPI; revoke the Trusted Publisher; rotate
  GitHub + PyPI 2FA; inspect the offending workflow run and the dependency graph.
- Never add a long-lived PyPI token to the repo or CI — Trusted Publishing (OIDC) only.
