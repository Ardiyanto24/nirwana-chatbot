# Versioning Policy

*[Bahasa Indonesia](VERSIONING.id.md)*

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), adapted for a backend API service rather than a library:

| Bump | Triggered by |
|---|---|
| **MAJOR** | A breaking change to the `POST /v1/turns` request/response contract (see [`docs/panduan-integrasi-frontend.md`](panduan-integrasi-frontend.md)), or a change to RBAC behavior that alters who is authorized to see what. |
| **MINOR** | A new capability added without breaking the existing contract — a new processing layer, a new optional field, a new deployment/operational capability (e.g. the upcoming production deployment pipeline). |
| **PATCH** | A bug fix, internal refactor, or dependency bump with no observable change to the contract or to RBAC behavior. |

## Where the version lives

- **[`pyproject.toml`](../pyproject.toml)** (`[project].version`) is the single source of truth for the current version.
- Each release gets an **annotated git tag** (`vX.Y.Z`) matching that version.
- **[`CHANGELOG.md`](../CHANGELOG.md)** documents every tagged release under a `## [X.Y.Z] - YYYY-MM-DD` heading, following [Keep a Changelog](https://keepachangelog.com/).

## Why `v1.0.0` now, with deployment still pending

All 7 core processing workstreams (24 milestones) and the CI/CD foundation (linting, secret scanning, dependency scanning, test gates, an RBAC regression suite, an LLM-prompt evaluation gate, and a scheduled adversarial security scan) are complete and independently verified. What remains — provisioning a production VPS, a reverse proxy with TLS, and an automated deploy pipeline — is deployment *infrastructure*, not a change to the API contract or to what the system does. `v1.0.0` marks "the software is complete and behaves as documented"; the deployment milestones will land as a `MINOR` bump once finished, since they add operational capability (public reachability, automated releases) without changing the contract.

Before this project reached this point, `pyproject.toml` sat at a pre-1.0 `0.1.0` with no tags at all — by SemVer convention, that would have signaled "anything might still change." That's no longer an accurate signal now that the core system is stable and independently verified end-to-end.
