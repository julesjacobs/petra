# Independent RC12 witness check

Passed after root confirmed all timed measurements were complete and both whole-cohort audits passed. The preflight found no workspace build/solver workloads. The reviewer ZIP was read only as JSON data; no reviewer program or solver discovery was executed.

The original weighted net executes all 5,192 transition indices and reaches the complete original EF target. Each component word is executable from the initial marking divided by five. The expanded trace contains two copies of the 181-step word and three copies of the 1,610-step word; their endpoints sum to the replayed original endpoint. Exact row values are `[2, 0, 3, 0, 2]`. Original PNML/XML and canonical branch hashes and transition identities matched; the existing independent Python checker also accepted the trace.

Checking completed in 3.912 seconds with 930,676,736 bytes sampled peak RSS, within the 60-second/2-GiB checking limits. This is external witness-checking cost, not a solver result. Native measured coverage remains **363/368 in both repeats**. This check does not verify the separate conserved-block argument excluding uniform lifting.

`worker.py` preserves the independently written checker command; `preflight.json`, `execution.json`, `checker.log`, and `result.json` retain the record.
