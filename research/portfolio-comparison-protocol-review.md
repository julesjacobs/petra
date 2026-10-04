# Portfolio comparison protocol review

Reviewed the proposed five-configuration comparison, current runner/analyzer,
both source manifests, and saved ladder/SMPT repair evidence. This is a protocol
review before final registration, not certification of an as-yet unwritten plan
or deployment. No builds, solvers, remote access, or measurements were used.

## Assessment

Suitable for a development screen once the following launch gates pass. It is
not a held-out evaluation or a stable timing study. No families are reserved in
this comparison; do not inherit the older reports' reserved-family claims.

1. **Interpretation:** old-binary focused versus new-binary focused+buffer
   measures their complete configurations, including intervening source changes.
   It cannot isolate buffer agglomeration. New-binary focused+buffer versus
   new-binary batched+buffer isolates the selected search method if every other
   flag is equal. Keep these distinctions in result labels. A new-binary focused
   control without buffer would be needed for a buffer ablation, but is not
   necessary for the proposed end-to-end comparison.
2. **Registration and scoring:** freeze each native label's binary identity,
   engine and exact feature-flag set; reject unregistered flags, missing labels,
   duplicate labels and swapped binaries. Register all five configurations in
   every slot. All native positives and negatives need successful independent
   checks; validation timeout/error is unresolved. Competitor answers remain
   tool-reported. Preserve both reported and strictly accepted totals rather
   than implying equal assurance. Reject deadline/OOM/nonzero-exit/capability
   failures and SMPT child tracebacks even if a definitive line was printed.
3. **Deployment:** preserve the actual old remote runner bytes before replacing
   shared scripts. Freeze and verify the full new runner/import/checker closure
   for every configuration, not just the launcher. Preserve old results and
   source snapshots. Smoke the actual final commands on positive and negative
   cases, including buffer lifting and repeated witnesses; a generic positive
   smoke alone does not exercise either new validation path. Finish all smoke,
   hashing, deployment and compilation before measurement starts.
4. **Dependencies:** rerun the registered MiniZinc repair preflight and retain
   its output. Preserve the portable SMPT patch identity, enabled method list,
   MiniZinc default solver/configuration, Python environment, executables and
   loaded libraries. Adding the repaired MiniZinc bundle to PATH is a new
   configuration; it does not repair the old application results retroactively.
   VerifyPN binary/source identity and full command must also be frozen.

## Corpus reconciliation

Direct manifest inspection gives **656 unique named slots, 640 imports and
16 collection failures** across 41 model instances. For five configurations and
one repetition this means **3,280 rows and 3,200 intended solver invocations**;
the failed TokenRing-PT-050 slots are retained but not executed.

Across the complete union there are **629 exact ordered-branch representatives**
and **630 kind-preserving representatives**. Recompute these from the final
manifest rather than adding or reusing previous summaries. Preserve source
manifest hashes, source membership, per-slot provenance, original PNML/XML and
canonical branch identities; verify rebased paths after construction. A name
collision must fail construction rather than silently overwrite a slot.

Give solved totals for all slots, imported properties, representatives, and
families. Duplicate correction alone does not correct the large contribution
of structurally similar parameter ladders: the 176 FMS properties were already
solved by all tools. Report the old corpus and ladder corpus separately as well
as the union. This is the full previously selected development corpus, not an
outcome-independent sample of Petri nets or a newly established hard set.

## Timing and analysis

The existing runner shuffles properties with a seed and rotates method order
across queries. Freeze a non-null seed and resulting order. Use the same CPU8
affinity, enforced aggregate 2 GiB including descendants, strict outer deadline
and perf settings for every configuration. Single-CPU affinity permits a
multiprocess portfolio time-sharing that CPU; it satisfies the single-core
resource budget. Record host topology and avoid engineering/transfers during
measurement. Affinity is not isolation.

Count parse, reduction, search, witness construction and solver output in solver
time. Bounded independent checking remains outside it for all native methods.
The existing repeated-search witness replay can exceed its internal deadline;
the outer timeout must remain authoritative, including output during shutdown
grace. Record validation cost separately. Audit all 3,280 rows and saved sidecars
before taking the generated summary as an accepted result.

One five-second repetition supports solved-set screening. Retired instructions
are supplementary work measurements on successful runs with acceptable counter
coverage; preserve missing/low-coverage counters and do not compare truncated
timeout counts as total solution costs. Shared-host contention still affects
timeout censoring. Report paired solved-set gains and losses, per-family gaps,
and disagreements. Any common-solved timing ratios need their denominator and
selection bias stated. Longer qualification of every jointly unresolved query
should use a separately frozen protocol; do not silently drop easy properties
or collection failures from this run's denominator.
