# Buffer agglomeration integration

Opt-in Rust module, independent Python checker, CLI and benchmark runner support
are implemented and tested. Discovery skips expanding Cartesian products.
Proof contract and initial evidence: buffer-agglomeration-contract.md and
buffer-agglomeration-results-v1.md. No default promotion or novelty claim.

Flag order: target-zero trap, target-path potential, buffer agglomeration, then
existing engine. Preparation uses at most 10% of remaining time, capped at 100 ms,
with 20 million work units. Preparation failure falls back with remaining time.
Failed witness lifting or missing negative proof returns unknown. Proof dispatch
shares the 32-level nesting bound and monotonic deadline.

Frozen v2 binary SHA256:
790bf9dac689a43445fae5afac31bb9981725dcd2b02d35981a9a641079bc9a8
Frozen source SHA256:
2683400c2b0d39e27841af66bb8706f853416602d4d30863ecdc3bebe8667a72
Source archive contains 160 files, including vendor/varisat and inspector example.

Local build/test/inspection/NoC handles are terminal. Full application regression
is running in local session 72658 (384 rows). Linux session 10739 remains live;
no engineering or bulk transfer on either host until its measuring session terminates.
Wait for both before retrieving remote bulk artifacts.
