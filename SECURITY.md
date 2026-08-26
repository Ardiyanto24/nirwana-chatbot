# Security Policy

*[Bahasa Indonesia](SECURITY.id.md)*

## Scope

This repository implements **Layer 1** of a two-layer RBAC design: understanding a user's intent, classifying which data domains it touches, and enforcing role- and individual-scope authorization *before* any data request is built. It never queries the underlying data platform directly.

**Layer 2** — row-level enforcement (`property_id` / `own_property` / `all_properties`) — is implemented by `chatbot_api`, an external service owned by a different team. It is consumed here as an HTTP client and is out of scope for this policy; report issues in that service to its own maintainers.

## Reporting a Vulnerability

This is a solo portfolio project, not a maintained product with a dedicated security team, but reports are welcome and taken seriously. Please use **[GitHub Security Advisories](../../security/advisories/new)** ("Report a vulnerability" under this repo's Security tab) rather than a public issue, so any fix can be verified before details go public. Response time is best-effort.

## Known Active Finding (as of 2026-08-23)

### Prompt injection bypasses the Domain Gate's RBAC classification — unpatched, high priority

**What was found.** An automated, scheduled adversarial-testing job (`.github/workflows/redteam.yml`) found that the two prompts responsible for classifying which data domains a question touches — the primary classifier and its independent "blind spot" second-opinion check — have no defense against prompt injection. A user message containing an explicit instruction-override pattern (impersonating a system-level directive) consistently caused *both* independent classification steps to omit a sensitive domain (`financial`) that the question genuinely touched. This reproduced identically across four independent runs, including a real scheduled CI execution — not a one-off fluke.

**Why it matters.** Domain classification is the first of the two independent, LLM-based authorization checks that make up Layer 1 of this system (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the "generate then verify, independently" pattern this project otherwise relies on). If classification is fooled into omitting a sensitive domain, the downstream authorization check never evaluates that domain at all — the request proceeds as though the sensitive domain was never mentioned. Layer 2 (`chatbot_api`) still enforces row-level access on whatever request actually reaches it, so this is not by itself a path to unrestricted data access — but it does mean Layer 1's stated purpose (catching intent before a request is even built) can be defeated with a simple instruction-override phrase, no sophisticated jailbreak technique required.

**Status.** Open, unpatched, high priority. The scheduled scan re-runs weekly and will keep surfacing this until it's fixed. It is deliberately non-blocking (it does not fail CI or block merges) while a proper fix is designed and verified — see [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) for how this fits into the project's broader open-issues tracking.

**Planned remediation** (not yet implemented or verified): add explicit anti-injection framing to both prompts — treat user-supplied text strictly as data to classify, never as instructions to follow — then re-run the adversarial suite to confirm the bypass no longer succeeds before this is closed out.

The full internal write-up — discovery methodology, all tested scenarios, and the complete red-team process — is documented (in Indonesian) in [`docs/keterbatasan-diterima.md`](docs/keterbatasan-diterima.md) (entry #22) and [`milestones/8.5-red-team-adversarial-scan/`](milestones/8.5-red-team-adversarial-scan/). It is deliberately not reproduced here in exploitable detail (no working payloads).

## Design Principle

This project runs a "generate, then verify independently" pattern at every point where a decision depends on understanding meaning rather than a fixed rule (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)). The finding above is a useful counter-example: two independent checks don't help when both share the same blind spot (neither was designed to resist adversarial input in the first place). Limitations that fall short of an active vulnerability are tracked separately in [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md).
