# Boolean-consistency comparison, v2

Outcome-selected synthetic development views; one 5-second single-core Linux repetition, 2 GiB. Native certificates independently checked. Competitor answers are tool-reported. Unknowns and errors are not negative answers. Use all 34 queries for comparisons; these are not held-out evaluation.

| Method | Reachable | Unreachable | Unknown | Error |
|---|---:|---:|---:|---:|
| before | 8 | 0 | 26 | 0 |
| dag-v1 | 15 | 7 | 12 | 0 |
| symbolic | 15 | 9 | 10 | 0 |
| verifypn-default | 4 | 1 | 29 | 0 |
| smpt-full-portable | 1 | 9 | 24 | 0 |

## Development filters

Apply these filters to `benchmarks/boolean-consistency-v3`.

- `candidate-unresolved.filter`: 10 queries.
- `all-unresolved.filter`: 10 queries.
- `competitor-only.filter`: 0 queries.
- `candidate-only.filter`: 11 queries.

The application comparison remains separate: the last complete 368-query
run left 70 Rust queries unresolved, with 58 solved by VerifyPN.
Synthetic gains do not establish an application performance advantage.
