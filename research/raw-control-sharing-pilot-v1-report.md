# Exact control-marking sharing

The matched eight-row pilot preserves the four original queries, 30-second
input/check-inclusive deadline, sampled 2 GiB and two billion solver/checker work.
Both frozen binaries solve 3/4; all six definitive answers are independently
checked. There is no solved-coverage gain at this allowance.

For n5, the baseline crosses 2 GiB. Sharing stops at its work cap around 459 MiB;
it has interned 2,293 controls at its last complete game record. The two runs stop
at different game sizes, so this is not a same-state RSS ratio. Saved n4 certificates
had already established many nodes with identical control markings. Interning
preserves full u64 markings and original component identities; it does not merge
components. Extra interning work is charged, and certificate/checker formats remain
unchanged. 203 library tests, seven CLI tests, three diagnostic integration tests,
two schema tests, formatting, Clippy and release build pass.

A separately registered two-row diagnostic gives both binaries ten billion work
with the same30s/2GiB limits. Baseline again exceeds memory during game construction.
Sharing completes the game:167,874nodes,2,315distinct control markings. It extracts
37,024certificate nodes and passes the Rust invariant and schema checks, then
exceeds2GiB before writing any output. The worker's saved stage is `solver` and
`solver.stdout` is empty. It therefore remains Unknown without independent
acceptance. Code inspection identifies conversion of the dense proof into
`serde_json::Value` as a large additional allocation after the checks. A separate
streaming-output ablation tests this hypothesis with unchanged serialized proof
semantics. None of these local diagnostic timings supports a competition claim.

Artifacts: `raw-control-sharing-pilot-v1-{plan,analysis,verification}.json`,
`raw-control-sharing-expanded-v1-{plan,analysis,verification}.json`,
`results/solver-raw-control-sharing-v1` and `raw-control-sharing-observation-v1.json`.
