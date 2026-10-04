# General development v3: unused family groups

Frozen selection: `benchmarks/general-development-v3-selection.json`, SHA256
8b0c3496bc31f6fecf4cb54ff49a8d826b10feb7387ea5a1de7f562d1616fc90.
Selection audit passed. This is a development extension, not reserved evaluation
or an established harder benchmark set. Difficulty is still unmeasured.

The selected family names are TriangularGrid, IBM319, RERS17pb114, RefineWMG,
CloudReconfiguration and DNAwalker. Median-rounded-up and final indexed PT
instances give11models and176planned ReachabilityCardinality slots; IBM319 has
one indexed instance, so its coincident ordinals are counted once.

The selector uses only the frozen2021index and named selection metadata. It
excludes all22reserved families and all previously used groups. It conservatively
groups RERS*,IBM*,DLC*,names containingProductionCell,and names containingGPU.
These are explicit exclusion/deduplication heuristics, not proof that all other
groups have independent generators. Related-generation provenance needs review
before any publication-level split claim. All remaining families are ranked by
SHA256(pvass-general-development-v3:+family); the first six distinct groups are
selected. Every indexed family decision, rank and selected ordinal is retained.
No candidate/reserved model, property or solver result was read during selection.

This addresses a concrete limitation of the present application cohort: its
families' larger indexed instances are already exhausted, and those ladders
mostly expand representation size. A fresh group selection tests broader behavior
rather than repeatedly enlarging the same generators. It may still prove easy;
that outcome must be reported rather than replaced with selected successes.

## Acquisition after the measurement gate

Do not run this while local signed-threshold screen session34053is active:

```
vendor/venv/bin/python scripts/collect_stress_mcc.py --selection benchmarks/general-development-v3-selection.json --output benchmarks/general-development-v3 --seconds 120 --memory-mib 2048 --archive-mib 256 --expanded-mib 1024 --artifact-mib 1024
```

Collector preflight additionally rejects conflicting workspace workloads. One
model worker at a time, nominal22minute worker budget, sampled2GiB locally,
256MiBcompressed archive,1GiBexpanded/artifact limits per model. All176slots survive
archive/import/property-count/resource failures. Remote URL bytes are not frozen
by the index: record downloaded archive hashes and original input identities.
Maximum artifact allowance11GiB plus logs/metadata. No solver runs in acquisition.

Independently check original PNML/XML translations and complete canonical target
branches, then audit exact indexed/canonical duplicates within the cohort and
against prior development corpora. Preserve duplicates in full-denominator
reporting and show representative summaries separately. Do not open reserved
payloads to perform overlap checking; reserved metadata/group exclusions suffice
for this development stage.

## Qualification and claims

The source review in `research/smpt-single-core-review-v1.md` proposes four
additional SMPT configurations, including official competition mode. Freeze the
final matrix and an isolated runner before qualification; the proposal has no
performance result yet.

Freeze configurations only after collection and import audit. Use the current
strongest audited native-walk configuration, matched batched and historical
frozen native, VerifyPN default, and repaired full portable SMPT. Signed-threshold
binary/unary are separate opt-in mechanisms; comparing their standalone coverage
must not be mislabeled a measured integrated portfolio gain.

Primary5soriginal-input budget, single core, enforced2GiBLinux, separate60s/2GiB
native checking. Record instruction counters and invalid/missing-counter reasons,
plus solver-only and checked end-to-end costs. Linux31728must terminate before
any remote builds, bulk transfers or new measurements. Preserve native/external
answer-validation distinctions and detect disagreements before interpretation.

Apply longer60s and300s stages to all jointly unresolved imported properties,
with predeclared stage matrix and full parent denominators. These are outcome-
selected diagnostic views, not a replacement cohort. One repetition qualifies
coverage/difficulty only. Repeat balanced orders on matched configurations before
claiming stable speedups. No goal success, novelty or publication-readiness claim
from a selected engine union or an isolated winner.

The publication objective stays a general solver with serializability as an
application, and coverage/speed first. This cohort can falsify an overfit engine;
it cannot itself establish broad superiority. All22reserved families remain
untouched until the integrated algorithm and evaluation protocol are frozen.
