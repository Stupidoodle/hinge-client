# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Typed async Hinge API client with resource namespaces
  (`client.recommendations`, `client.profile`, `client.rating`, `client.content`,
  `client.prompts`, `client.chat`) and auth/session lifecycle on the client.
- In-memory `Catalog` (enum labels + live prompt library), no database.
- Opt-in colored structlog console logging via `configure_logging()`.
- 100% branch-covered test suite.
