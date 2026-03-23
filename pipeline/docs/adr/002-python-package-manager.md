# ADR-002: Python Package Manager

## Status
Accepted

## Date
2026-03-23

## Context
The pipeline is a Python service that needs dependency management. We're building a monorepo and need fast CI/CD builds with reproducible environments.

**Options considered:**
1. **Poetry** — Mature, well-documented, large community
2. **UV** — Rust-based, extremely fast, modern lock file format

## Decision
**UV**

## Rationale
UV delivers 10-100x faster dependency resolution and installation than Poetry—critical for CI/CD speed in a monorepo. Key advantages:
- **Speed** — Rust-based resolver is dramatically faster
- **Lock-file first** — Reproducible builds by default
- **Monorepo support** — Excellent workspace support for shared dependencies
- **Ecosystem alignment** — Default in Astral's Python tooling stack (alongside Ruff)

The ecosystem has matured significantly; UV is production-ready.

## Consequences

### Positive
- CI builds complete in seconds instead of minutes
- Consistent with our Ruff usage (same vendor)
- Modern lock file format with better security guarantees
- Built-in virtual environment management

### Negative
- Newer tool with slightly smaller community than Poetry
- Requires learning UV-specific commands
- Lock-file format differs from Poetry (migration needed if switching)
- Git diffs on lock files are less human-readable

### Mitigations
- Document UV commands in CONTRIBUTING.md
- Use automation to update dependencies (Dependabot/Renovate support UV)
- Team ramp-up is minimal—basic commands are intuitive
