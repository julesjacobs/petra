# Repeated-firing candidate status

The 192-query local regression is complete and audited: 384 rows, buffer-focused
control 190/192, buffer-batched 192/192, no losses or disagreements. All 382
definitive rows have saved successful independent checks. CircadianClock's gain
uses repeated firing; NoC's observed gain uses causal-state-equation reasoning
and is not attributed to repeated firing. Process session 77605 terminated exit0.

Independent source review found no blocking correctness issue. The existing
witness expansion/replay path does not enforce an internal deadline; original
PNML scheduling and the strict outer process deadline censor late answers.
See repeated-search-review.md. There is no general speed, novelty or completeness
claim, and neither method nor buffer reduction is promoted by default.

Linux candidate is built and fetched at results/linux-solver-repeated-search-v1.
Binary SHA256: 876e855affc6aab53f920295dcb57747df7de61bbb64733d89b63ff8c9aa0ab5.
Solver source archive matches the local frozen candidate exactly:
a10d053df3e97338e80be8b88608119747cdf89bb97b010bda3de596109fc651.
Tests: 179 library, 13 relaxed and six repeated-search tests pass on Linux.
The first deployment script had a syntax error before any remote action; it is
preserved in deploy-repeated-search-linux-v1-syntax-failure.log. The first Linux
test build then found three missing compile-time fixtures. Those are independently
pinned in test-fixtures-sha256.json and test-fixtures.tar.gz alongside the source
archive; the initial failed build log is retained. No solver source was changed.
Sessions73314(failed initial test build) and66316(successful completion) are terminal.

No local or Linux measurement is live. The Linux root runner scripts remain at
the previous campaign versions: the new candidate has not been timed there.
results/runner-repeated-search-v1 contains a frozen 22-file dependency closure
bundle and its hashes, prepared locally but **not deployed**. Deployment should
preserve the old remote runner bytes, explicitly register the new bundle, and
smoke-test buffer negative checks and expanded positive witnesses before timing.

Next comparisons must retain the complete parent sets. The 464-slot Linux ladder
has an audited 1,856-row result: 448 imported, 16 collection failures, 13 jointly
unresolved at five seconds. See application-parameter-ladders-v2-screen-report.md.
Qualify all 13 under longer budgets as preregistered; compare the new candidate
against the frozen capacity-direct binary and the repaired competitor setup.
The analysis/audit currently assumes one shared native binary and two legacy
method names; extend it with explicit per-method identities and flag checks
before using it for the new multi-binary campaign. Preserve its old behavior and
all prior reports. Do not reinterpret absent collection slots as timed failures.

The next substantive algorithm proposal is raw-SER adaptive control projection,
documented in raw-adaptive-projection-plan.md and benchmark-hardness-next-track.md.
It is not implemented or measured. It needs phase diagnostics to distinguish
missing serial schemas from projected-state growth and component-transfer work.
All 22 reserved families remain untouched.
