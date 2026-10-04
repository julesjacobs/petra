# Typed streaming proof output

All eight matched rows completed and artifact reconciliation passed. Both control
sharing alone and control sharing with streaming output solve3/4queries at10B
solver/checker work,30seconds including input/checking, and sampled2GiB. All six
definitive answers passed independent checking. This is a local diagnostic; Linux
artifact retrieval overlapped part of it, so timing is not a competition result.

Streaming serializes typed raw certificates directly through a buffered writer,
without constructing a serde_json::Value tree. JSON proof fields and checker
acceptance rules are unchanged. CLI verification/forgery and automaton/unsafe
counterexample tests pass, as do diagnostic/schema integration tests and Clippy.
Library code is unchanged from the203-test control-sharing freeze.

n5 previously exceeded memory after Rust verification and before output. Streaming
writes the complete125MiB answer, and the worker reaches independent negative
verification. It then exceeds2GiB at27.6seconds. The baseline exceeds memory during
the solver stage. Neither is accepted: output and Rust checks alone are insufficient.

Next investigation: independent checking retains dense tuples of every control
marking to reject duplicate nodes, in addition to the original dense certificate.
Exact sparse keys could remove these duplicate vector allocations while preserving
full u64 validation and duplicate rejection. This is a proposal; no checker change
or new accepted answer is claimed.

Artifacts: `raw-proof-streaming-pilot-v1-{plan,analysis,verification}.json` and
`results/solver-raw-proof-streaming-v1`. Earlier frozen binaries and failures are
preserved. All source/runner/binary identities are registered and reconciled.
