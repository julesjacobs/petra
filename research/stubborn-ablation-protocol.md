# Planned stubborn-set ablation

Status: protocol before implementation handoff. No run registered or launched;
binary, source and runner hashes must be added to a concrete plan after review,
tests, Clippy and release build pass. Do not measure alongside local engineering.
The live Linux comparison remains unchanged.

The primary comparison uses the same new frozen binary with `portfolio-focused`
and `portfolio-stubborn`, identical capacity preprocessing, relevance, scheduling,
state limits and original PNML/XML inputs. The only intended algorithmic change
is reduction in the unrestricted relaxed-search fallback. Keep default methods
unchanged. Initial K is eight; closure and seed policy must be fixed before runs.

First run all 104 candidate-challenge properties at five seconds, one repetition,
2 GiB, two million states, randomized paired method order and strict outer
deadline. Independently check every definitive native answer against original
inputs with separately bounded validation. Retain all failures and 208 expected
rows. This is a screening run, not a stable performance claim. Compare the 34
older competitor-solved cases separately without treating all as current gaps.

If the screen finds new checked solves or substantial state reduction in
separate diagnostics, register a full 104-property, three-repetition comparison
before changing the algorithm. Report stable and intermittent coverage, losses,
memory and conditional timings. Never discard failed repetitions or mix new
configuration runs into an old matrix. If no benefit appears, investigate or
reject the intervention before running a larger performance campaign.

Keep profiling out of the merged stdout/stderr measurement runner: diagnostic
events would corrupt its JSON answer parser. Separate diagnostic runs must
capture stderr independently and retain mapping to original query, method and
budget. Expanded/generated states, enabled/chosen transitions and each full
expansion fallback explain mechanisms; diagnostic timings are not substituted
for the primary results. Check whether the new fallback was actually reached.

The same-source baseline must preserve the existing lazy helpful-first expansion;
instrumentation must not force a full transition scan into helpful-only search.
Compare against the prior frozen focused binary separately if baseline overhead
or a functional change is observed.

Before a broader advantage claim, test full parent corpora (including all 368 MCC
properties), run matched Linux single-core competitor comparisons, and preserve
all source/export/validation failures. The eight reserved families remain unused
until final configurations are frozen. Neither this development view nor the
preservation argument establishes novelty or publication readiness.
