# Changelog

All notable changes to this project are documented here. The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](docs/VERSIONING.md).

This is the project's first tagged release, reconstructed from 52 completed milestones — each milestone gets its own entry below, grouped by workstream, rather than the usual flat `Added`/`Changed`/`Fixed` list, so the history stays legible at this scale. Every entry links to the detailed internal record (in Indonesian) the summary was drawn from.

## [Unreleased]

Nothing yet — the next milestones (production deployment: VPS provisioning, reverse proxy/TLS, automated deploy pipeline) will land here before becoming `1.1.0`.

## [1.0.0] - 2026-08-26

### Workstream 1 — Input Layer, Context Resolution & Decomposition

#### 1.1 — Observability foundation
- **Added**: a local OpenTelemetry stack (Collector, Jaeger, Prometheus) via Docker Compose as the single ingestion point for every layer's traces and metrics, with a slot reserved for a future public exporter.
- **Added**: a shared `gen_ai.*` span-attribute naming convention, enforced in code from the start.
- _Details: [`milestones/1.1-fondasi-collector/`](milestones/1.1-fondasi-collector/)_

#### 1.2 — Input Layer
- **Added**: the first HTTP endpoint (`POST /v1/turns`), validating an incoming conversation turn (fields, types, a 20-role whitelist, history rules) with clear per-field error messages.
- **Added**: a configurable role whitelist (YAML) instead of a hardcoded list.
- **Changed** (addendum, see 1.3): the payload was later revised to carry the full conversation history rather than just the previous turn.
- _Details: [`milestones/1.2-input-layer/`](milestones/1.2-input-layer/)_

#### 1.3 — Turn dependency detection
- **Added**: the project's first LLM call — detects whether a new message depends on an earlier turn in the conversation, and identifies which one.
- **Fixed**: the Input Layer's payload (1.2) was revised to carry the full conversation history, needed to detect references further back than the immediately preceding turn.
- **Fixed** (addendum): added missing error handling around the LLM call, matching every other layer's fallback behavior.
- _Details: [`milestones/1.3-pemetaan-ketergantungan-turn/`](milestones/1.3-pemetaan-ketergantungan-turn/)_

#### 1.4 — Standalone question rewriting
- **Added**: a step that rewrites a message into a fully self-contained sentence, resolving implicit references ("compare it to last year") using conversation history.
- **Added**: a deterministic check that flags (without blocking) any leftover vague references the rewrite missed.
- _Details: [`milestones/1.4-rewrite-mandiri/`](milestones/1.4-rewrite-mandiri/)_

#### 1.5 — Session memory
- **Added**: persistent "session memory" storage and retrieval (Supabase + SQLModel), the first purely deterministic, non-LLM mechanism in the pipeline.
- **Changed**: migrated the role-permissions config from a static YAML file into a proper database table.
- **Fixed** (addendum): added missing error handling around the retrieval function, matching project convention.
- _Details: [`milestones/1.5-tarik-session-memory/`](milestones/1.5-tarik-session-memory/)_

#### 1.6 — Decomposition
- **Added**: a 3-step "generate then verify" mechanism that splits a question into atomic, independently-answerable sub-requirements, with up to 3 retries on failed verification.
- **Fixed** (later, via 7.18): a crash when the LLM provider returned a malformed empty response instead of raising a proper error.
- _Details: [`milestones/1.6-decomposition/`](milestones/1.6-decomposition/)_

#### 1.7 — Matching against session memory
- **Added**: per-sub-requirement matching against stored session memory, deciding whether a fresh data request is needed, with a conservative "needs fresh data" fallback on any uncertainty.
- **Added**: re-archiving of reused data so it stays traceable across multiple turns.
- **Fixed**: a bug where re-archived data's source tracking was copied verbatim instead of rebuilt, which would have broken traceability on the first reuse hop.
- _Details: [`milestones/1.7-pencocokan-atomic-intent/`](milestones/1.7-pencocokan-atomic-intent/)_

### Workstream 2 — Domain Gate & Verification Gate (RBAC, Layer 1)

#### 2.1 — Domain identification
- **Added**: identification of which data domains a question touches, with an independent second-opinion "blind spot" check to catch domains a first pass might miss.
- **Added**: correct separation of closely related domains that could otherwise leak sensitive data (e.g. reservations vs. profit-margin financials).
- _Details: [`milestones/2.1-identifikasi-domain/`](milestones/2.1-identifikasi-domain/)_

#### 2.2 — Authorization check
- **Added**: deterministic role-vs-domain permission checking against a seeded copy of the official 20-role × 10-domain access matrix, supporting mixed allow/deny results within one question.
- Verified against all 200 possible role×domain combinations, cross-checked against two independently transcribed copies of the source matrix.
- _Details: [`milestones/2.2-pemeriksaan-otorisasi/`](milestones/2.2-pemeriksaan-otorisasi/)_

#### 2.3 — Individual-scope detection
- **Added**: detection of "individual performance" queries (e.g. staff asking about a specific employee's metrics) that must be restricted to the caller's own record, via a curated view list plus an independent generate+verify LLM check.
- **Added**: deterministic pre-filters that skip the LLM check entirely for obvious cases.
- _Details: [`milestones/2.3-deteksi-cakupan-individu/`](milestones/2.3-deteksi-cakupan-individu/)_

#### 2.4 — Verification Gate
- **Added**: the final, fully deterministic gate before any request is sent externally — validates request structure, that the resolved data view matches what was authorized, and force-corrects the employee-scope filter when 2.3's constraint applies.
- **Security**: flagged that the `employee_id` row-filter convention this gate relies on had not yet been confirmed with the data platform team — resolved in [4.1](#41--chatbot-api-integration).
- Completes the Domain Gate + Verification Gate authorization pipeline (2.1–2.4).
- _Details: [`milestones/2.4-verification-gate/`](milestones/2.4-verification-gate/)_

### Workstream 3 — Retriever & Query Engine

#### 3.1 — Candidate view retrieval
- **Added**: hybrid search over 67 data views — fast keyword search (BM25) first, falling back to semantic/embedding search only when nothing is found.
- **Changed**: results are restricted to domains the caller's role is authorized for.
- **Fixed**: a stopword-filtering bug that made the semantic fallback almost never trigger.
- _Details: [`milestones/3.1-pengumpulan-kandidat-view/`](milestones/3.1-pengumpulan-kandidat-view/)_

#### 3.2 — Semantic relevance check
- **Added**: an independent two-step AI review confirming each candidate view actually matches the meaning of the request (not just keywords), using a generate-then-independently-re-check pattern.
- _Details: [`milestones/3.2-kecocokan-makna/`](milestones/3.2-kecocokan-makna/)_

#### 3.3 — Structural sufficiency check
- **Added**: a hybrid (mostly deterministic, LLM only for ambiguous cases) check that verifies a candidate view's actual structure matches the requested answer shape, finalizing the winning view.
- Completes the candidate-search-to-selection pipeline (3.1–3.3).
- _Details: [`milestones/3.3-kecukupan-struktural/`](milestones/3.3-kecukupan-struktural/)_

#### 3.4 — Request construction
- **Added**: an AI step that converts an approved view + request into a concrete API request, including translating natural-language date ranges into calendar dates.
- **Added**: a defensive filter stripping any parameter the model invents outside the approved whitelist for that view.
- Published a provisional per-view parameter whitelist as a proposal pending reconciliation with the data platform team.
- _Details: [`milestones/3.4-penyusunan-request/`](milestones/3.4-penyusunan-request/)_

#### 3.5 — Request shape verification
- **Added**: an independent check confirming the built request's view matches what was approved upstream, and that its parameters genuinely produce the requested answer shape.
- Completes the Retriever + Query Engine pipeline (3.1–3.5).
- _Details: [`milestones/3.5-verifikasi-bentuk-request/`](milestones/3.5-verifikasi-bentuk-request/)_

### Workstream 4 — Execution & Interpretation

#### 4.1 — `chatbot_api` integration
- **Added**: the HTTP client that makes the system's only real network calls, to the external `chatbot_api` (Layer 2) backend, passing responses through unmodified for later classification.
- **Added**: a mapping table translating internal view names to the API's actual URL slugs.
- **Security**: found that 7 of 9 views meant to be scoped per-employee were not enforcing that filter server-side — reported to the data platform team and fixed the same day; re-verified all 9 views now enforce it correctly.
- _Details: [`milestones/4.1-membangun-pemanggilan-chatbot-api/`](milestones/4.1-membangun-pemanggilan-chatbot-api/)_

#### 4.2 — Response classification & failure handling
- **Added**: classification of API responses into success / partial / technical-failure outcomes, with authorization/not-found errors escalated as high-priority bugs, server errors retried automatically, and malformed requests routed through an automatic revise-and-resubmit loop (capped at 3 attempts).
- **Added** (later revisit): genuine "partial success" handling once a data-freshness/quality-status signal became available from the data platform.
- _Details: [`milestones/4.2-klasifikasi-respons-dan-penanganan-kegagalan/`](milestones/4.2-klasifikasi-respons-dan-penanganan-kegagalan/)_

#### 4.3 — Session memory persistence
- **Added**: saving each request's outcome to persistent session memory so later turns can reference it.
- **Added**: explanatory notes for known "meaningful null" cases (a blank value that's a legitimate business signal, not missing data).
- _Details: [`milestones/4.3-penyimpanan-paket-session-memory/`](milestones/4.3-penyimpanan-paket-session-memory/)_

#### 4.4 — Narrative generation
- **Added**: the step that writes the final natural-language answer, weaving together results from multiple sub-requirements across the current and prior turns, with distinct tone for permission-denied vs. technical-failure cases.
- First AI step producing free-form text rather than structured JSON.
- _Details: [`milestones/4.4-penyusunan-narasi/`](milestones/4.4-penyusunan-narasi/)_

#### 4.5 — Narrative fidelity check & visualization data
- **Added**: an independent fact-check step that rejects a generated narrative if it makes unsupported cause-and-effect claims not backed by the underlying data.
- **Added**: a deterministic (non-AI) transformer producing correctly-shaped chart data (single value, time series, etc.) per answer type.
- Completes the Execution & Interpretation workstream.
- _Details: [`milestones/4.5-verifikasi-kesetiaan-dan-visualisasi/`](milestones/4.5-verifikasi-kesetiaan-dan-visualisasi/)_

### Workstream 5 — Observability Dashboard

#### 5.1 — Grafana dashboard
- **Added**: a self-hosted Grafana instance wired to Jaeger and Prometheus, with 5 panels (trace search, waterfall view, latency per layer, status distribution, error-type frequency), backed by a new span-metrics pipeline in the Collector.
- _Details: [`milestones/5.1-membangun-dashboard-grafana/`](milestones/5.1-membangun-dashboard-grafana/)_

#### 5.2 — Public dashboard data layer
- **Added**: the `traces`/`spans` tables in Supabase (previously only planned), and a new Next.js project with a read-only, least-privilege connection and a data-access layer for fetching a full trace with correctly ordered child spans.
- _Details: [`milestones/5.2-skema-data-koneksi-nextjs-supabase/`](milestones/5.2-skema-data-koneksi-nextjs-supabase/)_

#### 5.3 — Public trace views
- **Added**: a filterable trace list and a per-trace waterfall view on the public dashboard, mirroring the internal Grafana panel — failed spans marked with three simultaneous visual signals (color, border, explicit text) for accessibility.
- _Details: [`milestones/5.3-tampilan-waterfall-daftar-trace/`](milestones/5.3-tampilan-waterfall-daftar-trace/)_

#### 5.4 — Public summary panel
- **Added**: an aggregate summary page (total queries, success rate, status distribution, latency percentiles per layer, error-type frequency) — the public dashboard now matches Grafana's informational content in full.
- Completes the Observability Dashboard workstream (5.1–5.4).
- _Details: [`milestones/5.4-panel-agregat-metrik-ringkasan/`](milestones/5.4-panel-agregat-metrik-ringkasan/)_

### Workstream 6 — Custom Exporter (Go)

#### 6.1 — Base exporter
- **Added**: a custom Go exporter, compiled directly into the OpenTelemetry Collector, writing trace/span data to Supabase.
- **Fixed**: an architectural gap where a specific internal span was forming its own disconnected trace instead of nesting under the turn's root span, which would have left a key status column permanently empty in production.
- _Details: [`milestones/6.1-membangun-exporter-dasar/`](milestones/6.1-membangun-exporter-dasar/)_

#### 6.2 — Delivery reliability
- **Added**: automatic retry with exponential backoff for transient write failures, and TTL-based eviction (60 min default) for spans whose parent trace never arrives.
- Verified via real fault injection (stopping/restarting a local Postgres instance mid-flight) and a real 69-span production-scale trace.
- Completes the entire 7-workstream / 24-milestone core system.
- _Details: [`milestones/6.2-membangun-penanganan-kegagalan-dan-keandalan-pengiriman/`](milestones/6.2-membangun-penanganan-kegagalan-dan-keandalan-pengiriman/)_

### Workstream 7 — Orchestration & API Layer

#### 7.1 — Cross-layer contract audit
- Audited real call evidence for all 18 units of work across the 9-layer pipeline ahead of wiring them together end-to-end; found 4 deviations from plan and 2 gaps later resolved.
- _Details: [`milestones/7.1-audit-kontrak-antar-layer/`](milestones/7.1-audit-kontrak-antar-layer/)_

#### 7.2 — Decomposition connectivity
- Verified `decompose_question()` was already wired correctly since its original milestone (1.6); added connectivity tests, no new production code needed.
- _Details: [`milestones/7.2-menyambungkan-decomposition/`](milestones/7.2-menyambungkan-decomposition/)_

#### 7.3 — Domain Gate connectivity
- Verified domain identification + blind-spot verification were already wired correctly; added a connectivity test using the real `gop_margin` RBAC scenario.
- _Details: [`milestones/7.3-menyambungkan-domain-gate/`](milestones/7.3-menyambungkan-domain-gate/)_

#### 7.4 — Query Engine connectivity
- **Added**: a new orchestrator function connecting request-building to request-shape verification — this pairing genuinely wasn't wired together before.
- _Details: [`milestones/7.4-menyambungkan-query-engine/`](milestones/7.4-menyambungkan-query-engine/)_

#### 7.5 — Interpretation connectivity
- **Added**: a new orchestrator function connecting narrative generation to fidelity verification and visualization — completes all four Level-1 layer-pairing milestones.
- _Details: [`milestones/7.5-menyambungkan-interpretation/`](milestones/7.5-menyambungkan-interpretation/)_

#### 7.6 — End-to-end orchestrator, part 1
- **Added**: `proses_turn()`, the first cross-layer orchestrator in the project (`src/orchestration/`), connecting the Input Layer to turn-dependency detection, and opening the `invoke_agent` root span for the first time in production code.
- **Fixed**: added missing error handling to `detect_turn_dependency()` (1.3), found via real evaluation.
- _Details: [`milestones/7.6-sambungan-input-layer-pemetaan-ketergantungan/`](milestones/7.6-sambungan-input-layer-pemetaan-ketergantungan/)_

#### 7.7 — End-to-end orchestrator, part 2 (parallel branch)
- **Added**: genuine parallel execution (the project's first concurrency mechanism) of question rewriting and session-memory retrieval, with manually propagated trace context.
- **Fixed**: added missing error handling to `retrieve_session_memory()` (1.5).
- _Details: [`milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/`](milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/)_

#### 7.8 — End-to-end orchestrator, part 3
- **Changed**: Decomposition now runs on the rewritten (self-contained) question rather than the raw input, connected sequentially after the parallel branch.
- _Details: [`milestones/7.8-sambungan-rewrite-decomposition/`](milestones/7.8-sambungan-rewrite-decomposition/)_

#### 7.9 — End-to-end orchestrator, part 4 (first merge point)
- **Changed**: session-memory matching now genuinely receives both the decomposition output and the session-memory retrieval output as real inputs — the pipeline's first point where two independent branches converge.
- _Details: [`milestones/7.9-sambungan-pencocokan/`](milestones/7.9-sambungan-pencocokan/)_

#### 7.10 — End-to-end orchestrator, part 5
- **Changed**: domain identification is now genuinely called from the orchestrator for items that need fresh execution.
- _Details: [`milestones/7.10-sambungan-domain-gate/`](milestones/7.10-sambungan-domain-gate/)_

#### 7.11 — End-to-end orchestrator, part 6
- **Fixed**: closed two previously-undiscovered wiring gaps — authorization checking (2.2) and individual-scope detection (2.3) had never actually been called by any orchestrator since their original milestones.
- **Added**: a new batch-level Retriever function, connecting the now-complete Domain Gate chain to view retrieval.
- _Details: [`milestones/7.11-sambungan-retriever/`](milestones/7.11-sambungan-retriever/)_

#### 7.12 — End-to-end orchestrator, part 7
- **Added**: a new batch-level Query Engine function connecting Retriever output to request building + verification.
- _Details: [`milestones/7.12-sambungan-query-engine/`](milestones/7.12-sambungan-query-engine/)_

#### 7.13 — End-to-end orchestrator, part 8
- **Added**: a new batch-level Verification Gate function that fans in three independent upstream sources (query engine, retriever, individual-scope results), matched by ID.
- _Details: [`milestones/7.13-sambungan-verification-gate/`](milestones/7.13-sambungan-verification-gate/)_

#### 7.14 — End-to-end orchestrator, part 9 (execution waves)
- **Added**: a new wave-grouping mechanism (`kelompokkan_wave()`) that partitions independent sub-requirements into sequential execution waves based on their dependencies — the first genuinely new scheduling concept in the project.
- **Verified**: `chatbot_api` reachability and the full execution path against a real running instance for the first time.
- _Details: [`milestones/7.14-sambungan-execution/`](milestones/7.14-sambungan-execution/)_

#### 7.15 — End-to-end orchestrator, part 10 (second merge point)
- **Added**: merging of already-answered ("done") sub-requirements, freshly executed results, and honest placeholders for RBAC-denied/technically-failed items into one set of packages for narrative generation.
- **Fixed**: an identity bug where reused session-memory packages carried the wrong turn's ID.
- _Details: [`milestones/7.15-sambungan-interpretation-lengkap/`](milestones/7.15-sambungan-interpretation-lengkap/)_

#### 7.16 — Full end-to-end verification
- Verified the complete 9-layer pipeline against 3 real scenarios (single request, multi-wave, cross-turn reference) — no new production code needed, the pipeline was already complete after 7.15.
- _Details: [`milestones/7.16-verifikasi-alur-penuh-end-to-end/`](milestones/7.16-verifikasi-alur-penuh-end-to-end/)_

#### 7.17 — HTTP endpoint
- **Changed**: `POST /v1/turns` now runs the full 9-layer pipeline and returns a real `TurnResponse`, replacing the milestone-1.2-era payload echo.
- **Added**: [`docs/panduan-integrasi-frontend.md`](docs/panduan-integrasi-frontend.md), the first formal integration contract for frontend consumers.
- **Fixed**: an orphaned server process on restart, and a blocking-event-loop bug found via real HTTP load testing.
- _Details: [`milestones/7.17-membangun-endpoint-api/`](milestones/7.17-membangun-endpoint-api/)_

#### 7.18 — Conversation history
- **Added**: a `conversation_turns` table recording each turn's question, answer, and outcome status for application-level history (separate from session memory), written best-effort so a history-write failure never fails the user-facing response.
- **Fixed**: a crash in Decomposition (1.6) triggered by a malformed LLM provider response, found via real HTTP execution.
- Completes the Orchestration & API Layer workstream (7.1–7.18) and the entire core system (all 7 workstreams).
- _Details: [`milestones/7.18-database-percakapan/`](milestones/7.18-database-percakapan/)_

### Workstream 8 — CI/CD

#### 8.1 — CI foundation
- **Added**: `.github/workflows/ci.yml` with lint (`ruff`), Go lint (`golangci-lint`), secret scanning (`gitleaks`), and dependency scanning (`pip-audit`, `govulncheck`), plus branch protection on `main`.
- _Details: [`milestones/8.1-fondasi-ci/`](milestones/8.1-fondasi-ci/)_

#### 8.2 — Test gate
- **Added**: `pytest`/`go test` wired into CI as a required check, with a fast always-run tier and a path-filtered tier for expensive LLM-dependent tests.
- _Details: [`milestones/8.2-test-gate/`](milestones/8.2-test-gate/)_

#### 8.3 — RBAC regression gate
- **Added**: [`tests/rbac_regression/`](tests/rbac_regression/), a permanent, deterministic regression suite covering 5 real zero-leakage RBAC scenarios, run as its own required CI check without needing an LLM API key.
- **Security**: verified the gate genuinely fails when RBAC enforcement is deliberately weakened in a test pull request.
- _Details: [`milestones/8.3-rbac-regression-gate/`](milestones/8.3-rbac-regression-gate/)_

#### 8.4 — LLM prompt evaluation gate
- **Added**: continuous prompt-reliability evaluation (17 Promptfoo suites) wired into CI as a required, 100%-pass gate, pushing results to Supabase for tracking over time.
- Uncovered 9 pre-existing failing scenarios (see [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md)).
- _Details: [`milestones/8.4-llm-eval-gate/`](milestones/8.4-llm-eval-gate/)_

#### 8.5 — Scheduled adversarial security scan
- **Added**: a weekly scheduled red-team workflow testing this system's prompts against RBAC-bypass and prompt-injection attacks.
- **Security**: found that the Domain Gate's two classification prompts are 100% bypassable via simple instruction-override injection — unpatched; see [`SECURITY.md`](SECURITY.md).
- _Details: [`milestones/8.5-red-team-adversarial-scan/`](milestones/8.5-red-team-adversarial-scan/)_

#### 8.6 — CI & hosting for the public dashboard
- **Added**: a public GitHub repository, CI pipeline (lint/test/build), and automatic Vercel deployment for the public observability dashboard.
- **Fixed**: a build-time database dependency in the dashboard, refactored to a lazy connection.
- _Details: [`milestones/8.6-remote-ci-dashboard/`](milestones/8.6-remote-ci-dashboard/)_

#### 8.7 — Backend containerization
- **Added**: a multi-stage `Dockerfile` for the backend, a `GET /health` endpoint, and CI jobs building and pushing native ARM64 images for both the backend and the exporter.
- **Changed**: restructured the git workflow into three permanent branches (`staging` → `develop` → `main`) with tiered branch protection.
- Verified the ARM64 image actually runs (not just builds) via QEMU emulation, answering `/health` with `200`.
- _Details: [`milestones/8.7-kontainerisasi-backend/`](milestones/8.7-kontainerisasi-backend/)_

---

[1.0.0]: https://github.com/Ardiyanto24/nirwana-chatbot/releases/tag/v1.0.0
