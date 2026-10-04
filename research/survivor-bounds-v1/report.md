# Certified boundedness of the previous survivor models

All four original nets behind the 41 jointly unresolved properties in the earlier
five-second screen have nonincreasing total token count. Reimporting their pinned
PNML files reproduces the canonical nets. The existing independent place-bound
checker accepts the all-ones potential for each net.

| Original model | Places | Transitions | Initial total / certified place bound | Largest initial place |
|---|---:|---:|---:|---:|
| DNAwalker-PT-09ringLR | 27 | 260 | 22 | 2 |
| DNAwalker-PT-18lozangeBlock | 164 | 3,697 | 101 | 2 |
| RERS17pb114-PT-5 | 1,446 | 151,085 | 90 | 5 |
| RERS17pb114-PT-9 | 1,446 | 151,085 | 162 | 9 |

For every original transition, `sum(post) <= sum(pre)`. Induction gives
`sum(m) <= sum(m0) = K`, hence `m[p] <= K` for every place. RERS preserves total
tokens exactly. DNAwalker transitions either preserve the total or decrease it
by one. These are valid upper bounds, not claims that each bound is tight.
None of these exact initial markings is 1-safe.

Boundedness does not make explicit search small: even the ring's total-token
bound admits `binomial(27+22,22) = 49,699,896,548,176` possible markings. This is
an upper bound, not an enumeration of reachable markings. Bounds for all four
models and their certificates are recorded in [result.json](result.json).

The bounds settle a premise of the earlier Pro review. If a fixed word `w` with
nonzero integer effect `delta` fires `r` consecutive times, choose a place with
nonzero effect. Both endpoints lie in `[0,K]`, so
`r * abs(delta[p]) <= K`; therefore `r <= K`. If `delta=0`, further repetitions
visit the same intermediate markings as the first traversal. Very large
consecutive repetitions of one fixed word cannot explain these instances.
Long paths through many different markings remain possible. This says nothing
against BMC, dynamic acceleration, or learned relations in general.

The later repeated diagnostic leaves 24 representatives unresolved at thirty
seconds, on the lozenge and two RERS models. Its eight stable native losses to
VerifyPN are ring properties. Thus every model in those two diagnostic groups
is covered by these bounds. Their property truth remains a separate question.

Reproduce from the workspace root:

```sh
vendor/venv/bin/python research/survivor-bounds-v1/check.py
```

The script pins the selection, manifest, original models, canonical comparison
inputs, certificate bytes, and checker sources. Python optimization is refused
because the existing independent checker uses assertions. No solver timing or
new property verdict is reported.
