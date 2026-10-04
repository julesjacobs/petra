# Automatic acceleration words and complete classical mechanism screen

The prototype now constructs its own vocabulary. Every original transition is
retained as a singleton. A deterministic, bounded search adds shortest cycles
in the transition-dependency graph: an edge means one transition has a positive
net effect on a place consumed by the next. Read arcs with zero net effect do
not create production dependencies. These words are only search proposals;
the original-net enabling constraints and independent witness checks decide
whether a proposed execution is valid. Exhausted discovery retains singletons
and reports truncation; it never supplies a negative reachability answer.

New practical components:

- Ordinary BMC, singleton acceleration and discovered-word acceleration share
  the Rust encoder. Ordinary BMC restricts repetition counts to zero or one.
- Sparse encoding emits frame/effect constraints once per place and step,
  rather than once per word/place/step. Word guards omit zero requirements.
- A Python process driver enforces a whole-query deadline over discovery,
  encoding, external Z3 and exact Rust witness checking. It increases segment
  depth geometrically up to a configured limit. Encoding/work/output limits
  return unknown. OS memory limits still belong to the outer benchmark runner.
- `scripts/check_accelerated_witness.py` independently checks compressed words
  by verifying each original transition guard at both extreme repetition indices.

Twelve targeted Rust tests pass (accelerated BMC, discovery, existing summaries),
as do 66 real-Z3 semantic checks, a three-mode synthetic ablation, six process-driver
checks, targeted Clippy and changed-file formatting. Existing vendored varisat
warnings remain. Synthetic control-cycle discovery recovers a trillion repetitions
at depth two, where ordinary BMC and singleton acceleration report bounded UNSAT.
This demonstrates the mechanism, not practical superiority.

## Full classical development screen

All 37 classical properties, including both duplicate certificate examples, were
retained. The complete matrix has 111 rows: one seeded, rotated run of each of
three configurations. Each property gets one second shared across its canonical
branches; each positive answer is independently checked outside that deadline
in a separately bounded child. Sampled 2-GiB process-tree limits apply on macOS.
All source, release-binary, Z3 and canonical-input identities are frozen in
`results/abmc-classic-mechanism-v1/plan.json` and `results/solver-accelerated-bmc-v1`.

| Method | Checked reachable / 37 | Remaining unknown |
|---|---:|---:|
| Ordinary BMC | 0 | 37 |
| Singleton acceleration | 1 | 36 |
| Discovered-word acceleration | 1 | 36 |

Both acceleration modes find `Performance__NTest__3u`; there are no gains or
losses between them. All111rows pass the saved-artifact audit, including both
bounded independent-validation receipts. This is a witness-only screen: none
of these configurations supplies an unreachability proof.

The historical checked native results in `results/classic-v2-final/runs.jsonl`
classify exactly this one property reachable and the other36unreachable in each
of three repetitions. Thus the corpus has little power to compare positive
search mechanisms. Those historical results are context, not a matched current
baseline timing. The screen gives no new evidence that discovered words improve
practical coverage over singleton acceleration. No timing speedup is claimed.

Next use the complete192-property MCC development cohort for broader witness
search and include a frozen native control under matched canonical-input budgets.
The strongest frozen Linux candidate/competitor comparison on176newproperties
continues independently; do not interrupt it or mix hosts in speed claims.
Before general integration, improve budgeted encoding construction and source
identity/validation support in the standard original-property runner. This
prototype remains opt-in and separate from the default solver.
