# Hard survivors v1

All eight jointly unresolved queries from the complete 276-row hard-development-v2 run: six FastForward random-walk queries and two synthetic pigeonhole queries. The full selection denominator remains 69, drawn from 620 parent queries. This is an outcome-selected development follow-up, not independent evaluation.

`selection-audit.json` preserves every row, all 69 selection decisions, parent evidence hashes, and verified input identities. No unknown query was excluded; failures remain failures. Five selected rows carry memory-limit flags and 31 carry outer-timeout flags; flags overlap. Reserved evaluation families remain excluded.

The manifest references unchanged sibling corpora. Transfer those corpora with this directory. Run `python3 scripts/build_hard_survivors.py --output benchmarks/another-name` to reproduce selection; normalized input paths depend on the output directory. The registered 300-second run has not been launched.
