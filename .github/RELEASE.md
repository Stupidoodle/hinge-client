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

## Cut a release
1. CI green on `master`.
2. Update `CHANGELOG.md` (move Unreleased -> the new version).
3. `git tag vX.Y.Z && git push origin vX.Y.Z`
4. Publish a **GitHub Release** for the tag — `release.yml` builds and publishes to PyPI via
   OIDC with PEP 740 attestations; the `pypi` environment gate requires a reviewer.
5. Verify: `pip install hinge-client` in a clean venv, then `python -c "import hinge"`.

## Incident response
- Malicious/bad release: **yank** the version on PyPI; revoke the Trusted Publisher; rotate
  GitHub + PyPI 2FA; inspect the offending workflow run and the dependency graph.
- Never add a long-lived PyPI token to the repo or CI — Trusted Publishing (OIDC) only.
