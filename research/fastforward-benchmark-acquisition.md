# FastForward benchmark acquisition

Acquired 218 unpruned `.lola`/`.formula` pairs from
[p-offtermatt/FastForward](https://github.com/p-offtermatt/FastForward/tree/bf6bb6fefd03c640af25b2f5ea0a0dc053d47736)
at commit `bf6bb6fefd03c640af25b2f5ea0a0dc053d47736`.

| Repository suite | Queries | Source files | Bytes |
|---|---:|---:|---:|
| coverability | 61 | 122 | 7,476,348 |
| random_walk | 127 | 254 | 62,936,141 |
| sypet | 30 | 60 | 17,755,540 |
| Total | 218 | 436 | 88,168,029 |

Seven additional files preserve the root MIT license, README, suite selection
scripts, benchmark utilities and random-walk generation source. The complete
443-file acquisition occupies 88,203,721 source bytes. Each downloaded file
matches the pinned Git blob SHA-1 and has a recorded SHA-256. The full upstream
Git tree response is also preserved and hashed.

Manifest: `benchmarks/fastforward-repository-v1/acquisition.json`.
Reproduction: `python3 scripts/download_fastforward_benchmarks.py --tree
research/fastforward-repository-tree.json`. The script verifies existing files,
refuses to replace a differing manifest, and downloads no solver binaries.
Its first run rejected executable metadata file modes before downloading;
`research/fastforward-download.log` preserves that failure. The corrected
acquisition completed in `research/fastforward-download-v2.log`.

The upstream `artifact/benchmark/run_all_on_all.sh` explicitly selects these
three directories. Their counts match the paper's 61/127/30. This establishes
repository-suite membership, **not byte identity with the published artifact**.
The 960,594,789-byte Figshare artifact remains undownloaded. Prepruned suites,
workflow datasets, and alternate TTS/spec encodings were excluded. No reserved
MCC inputs were inspected.

The paper describes these as positive examples. This remains an upstream
expectation, not an independently verified verdict. The random-walk suite was
selected to exclude short witnesses found by FastForward or LoLA; it is useful
development data with known selection bias, not held-out evaluation.

## Converted suite and validation

`benchmarks/fastforward-import-v2/manifest.json` contains all **218 imported
queries, zero unsupported, zero representation-limit failures**. Each has
canonical branches, generated PNML/XML, Tina input, source identifier mappings,
source and output SHA-256 hashes. Conversion happened offline: solver timing on
these inputs excludes original LoLA parsing and is a common-representation
comparison, not an original-LoLA end-to-end result.

| Suite | Places (min–max) | Transitions (min–max) | Preserved explicit equality-zero predicates |
|---|---:|---:|---:|
| coverability | 16–2,826 | 14–27,370 | 0 |
| random_walk | 52–2,826 | 60–27,370 | 66,519 |
| sypet | 65–1,199 | 537–8,340 | 9,542 |

Every PNML net was independently parsed by `smpt_import.pnml` and compared to
source places, initial marking, and weighted pre/post arcs. Every XML property
was independently parsed by `smpt_import.properties` and each complete dense
coefficient vector and bound compared to the source predicate. Equality is
encoded by both inequalities; only nonnegative lower bounds of zero are
removed as tautologies. Exact zero therefore remains the upper-bound predicate.
Zero-weight source arcs are normalized to absence, preserving ordinary P/T
semantics. Source files themselves are unchanged.

There are 100,473,467 dense coefficient entries across the canonical queries;
the largest has 8,034,318, below the explicit 20-million-entry per-query import
limit. Limit failures would remain in the manifest denominator. All queries
have one target branch. No solver result was used for selection.

Seven parser/conversion test groups pass, including weighted read arcs, exact
zero preservation, disjunction, malformed syntax, zero arcs and temporal scope.
`research/fastforward-formula-scope-audit.json` additionally verifies all 218
source formulas have one explicit parenthesized EF operand and no outside
syntax. The frozen conversion snapshots were captured at process start; later
parser scope hardening was separately applied to every source formula. The
initial 100/218 audit rejected zero arcs and is preserved; the second audit
accepts 218/218. Preliminary import v1 has an explicit provenance note and must
not be used for frozen comparisons; v2 has correctly captured source snapshots.

`research/fastforward-indexed-duplicate-audit.json` compares all 218 new branches
against all 39 canonical branches of the 37-query classical SMPT corpus. It
finds nine within-corpus duplicate groups and zero cross-corpus exact indexed
matches. Place, transition and constraint order remain significant. This is
**not** an arbitrary-renaming/isomorphism or full logical-equivalence audit;
zero matches do not establish semantic disjointness. All duplicates stay in
the full denominator. The conversion manifest also records six duplicate
groups within the new suite using its source indexed representation.

No solver was installed, built, or executed for this acquisition. Difficulty,
positive expectations and performance remain unmeasured. Independent source
LoLA witness replay, broader equivalence-based duplicate checking, comparison
against the archived artifact, and fair baseline installation remain future
work. Fixed-initial LoLA inputs were not equated to the excluded parameterized
TTS encodings.
