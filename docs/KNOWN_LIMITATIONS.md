# Known Limitations & Open Decisions

*[Bahasa Indonesia](KNOWN_LIMITATIONS.id.md)*

This project has kept a working log of every limitation it has found and every decision it has deliberately deferred, from day one — [`docs/keputusan-tertunda.md`](keputusan-tertunda.md) (open decisions, 5 active entries) and [`docs/keterbatasan-diterima.md`](keterbatasan-diterima.md) (accepted limitations, 22 entries including already-resolved ones). Those files are the full, authoritative history, written in Indonesian as internal working notes.

This page is a curated, external-facing summary of the items that are still open and most likely to matter to someone evaluating or extending this codebase — **not a replacement** for the two files above, which remain the source of truth (including full context, evidence, and every item already closed).

For the one item that rises to an active security concern rather than a design limitation, see **[SECURITY.md](../SECURITY.md)**.

---

## RBAC & data integrity

### The role→domain permission table is a manual copy, not a live read of production

**Problem.** This project can't query the production `role_permissions` table directly (that credential is reserved for the data platform's own Layer 2 API). Instead, it keeps its own copy, seeded once by hand from the source specification.
**Why it exists.** Credential segregation by access pattern is a deliberate architectural boundary, not an oversight — giving Layer 1 read access to a production table it doesn't otherwise need would widen its blast radius for no benefit.
**Current mitigation.** Layer 2 (`chatbot_api`) independently re-enforces the real permissions regardless of what Layer 1 decides, so staleness here can cause an incorrect early denial (UX friction) but not a data leak.
**What resolves it.** A notification process (or, eventually, a scheduled sync) for whenever the source permissions matrix changes upstream.

### Per-view API parameters and the data-staleness threshold are still provisional

**Problem.** The exact query parameters each of the 67 data views accepts were never formally published by the platform team, so this project derived a best-effort convention from column names in the data catalog and documented it as a proposal, pending reconciliation. Similarly, a 48-hour "data is stale" threshold was picked as a reasonable starting point, not calibrated against each view's actual refresh schedule.
**Why it exists.** The formal contract genuinely didn't exist yet at the time this had to be built; the system was deliberately designed with a recovery path (a failed request gets revised and retried) rather than blocking on an external dependency.
**Current mitigation.** None beyond the retry/revision loop already built into request handling.
**What resolves it.** Formal reconciliation with the data platform team; per-view refresh-schedule data once available.

---

## LLM behavior

### Reference resolution shows recency bias on genuinely ambiguous inputs

**Problem.** When a follow-up question could plausibly refer to more than one earlier topic, the models used for turn-dependency detection and question rewriting sometimes default to whichever topic was mentioned most recently, even when it isn't the one that's actually coherent to compare against.
**Why it exists.** Observed consistently across two different models and two different tasks — likely a general LLM tendency on ambiguous reference resolution, not a fixable prompt bug from a single data point.
**Current mitigation.** None active; the failure mode is narrow (only genuinely ambiguous multi-candidate cases) and every non-ambiguous scenario in evaluation passes cleanly.
**What resolves it.** More production evidence before investing in a targeted prompt fix, to avoid overfitting to a handful of hand-built test scenarios.

### The Domain Gate's second-opinion check is intentionally biased toward over-flagging domains

**Problem.** The independent "blind spot" check that runs after initial domain classification tends to add domains that aren't clearly needed when a question contains financial or time-related keywords in an unrelated context.
**Why it exists.** This is a deliberate asymmetric trade-off: a missed sensitive domain is a real RBAC gap, while an over-flagged domain only causes an unnecessary authorization denial. The check is tuned to fail toward the safer side.
**Current mitigation.** None — this is accepted as the correct trade-off given the alternative risk.
**What resolves it.** Evidence that over-flagging is causing disruptively frequent false denials in practice would justify tightening the prompt.

---

## Product-level trade-offs

### A narrative that fails fact-checking is replaced entirely, even the parts that were correct

**Problem.** The final answer to a user goes through an independent fact-check step before being returned. If it fails — even because of a single unsupported claim buried in an otherwise accurate answer — the *entire* response is swapped for a generic "please try again" message, discarding any correct information it contained.
**Why it exists.** A conservative first-pass decision for the very first version of the public HTTP endpoint: preventing any unsupported claim from reaching a user was judged more important than preserving partially-correct answers, while a more surgical strategy was still undesigned.
**Current mitigation.** The response still includes a note that verification failed and why, so the failure is never silently hidden.
**What resolves it.** Evidence that this happens often enough in practice to be worth designing a more targeted fix (e.g. regenerating just the unsupported portion).

### A handful of prompt-quality checks fail intermittently, and the CI gate still blocks on all of them

**Problem.** Continuous evaluation of the project's prompts (17 automated test suites) surfaced 9 pre-existing failing scenarios across 8 suites when it was first wired into CI as a required, 100%-pass gate — including two RBAC-sensitive ones. These are real, pre-existing prompt behaviors, not regressions introduced by turning the gate on.
**Why it exists.** A conscious choice to keep the bar at 100% rather than carve out exceptions, accepting that unrelated pull requests can occasionally get blocked by one of these known-flaky scenarios until each is individually investigated and fixed.
**Current mitigation.** None automatic; failures are triaged manually per occurrence.
**What resolves it.** Investigating and fixing each of the 9 scenarios individually (two of the RBAC-sensitive ones turned out to overlap with the security finding above, rather than being ordinary flakiness).

---

## Infrastructure & operational

### LLM calls occasionally hang indefinitely with no exception raised

**Problem.** Calls to the LLM provider have, on a handful of occasions across the project's history, hung for many minutes with no error, no timeout firing, and no distinguishable cause — isolated all the way down to raw `curl` against the provider's own completions endpoint, ruling out this codebase's HTTP client or SDK.
**Why it exists.** Everything isolated in testing behaves normally; this looks like an intermittent characteristic of the upstream provider or network path, outside this project's control.
**Current mitigation.** Explicit client-side timeout + limited retries, and active trace monitoring during long-running operations rather than waiting blindly.
**What resolves it.** Deeper network-level investigation (packet capture) if this starts affecting a documented success criterion rather than occasional test friction.

### The observability dashboard's latency histogram doesn't cover the project's real latency range

**Problem.** The metrics pipeline's default histogram buckets span roughly 2ms–15s, but real spans in this system range from sub-5ms deterministic checks to 90+ second LLM reasoning calls — so a chunk of the "latency per layer" panel renders as empty/`NaN` rather than a real value.
**Why it exists.** Tuning custom bucket boundaries across five-plus orders of magnitude needs real production-scale latency data to do well; the panel's core purpose (showing that LLM steps dominate latency) already works with the defaults.
**Current mitigation.** None; the panel is used as-is, with the gap disclosed in its own description.
**What resolves it.** Enough real traffic volume to calibrate custom bucket boundaries from actual data instead of a guess.

---

*Last curated alongside the v1.0.0 release. If you're deciding whether a specific limitation still applies, check the dated entry in [`keputusan-tertunda.md`](keputusan-tertunda.md) / [`keterbatasan-diterima.md`](keterbatasan-diterima.md) directly — this page summarizes a point in time, those files are kept current.*
