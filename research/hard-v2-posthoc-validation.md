# Separate validation of oversized native certificates

The live60-second Linux run is unchanged. For random3_n72_r480_s2026092701,
portfolio-symbolic returned unreachable in3.414seconds (Rust solving3.284seconds).
Its1,381,425-byte dag-cnf-rup-v2 answer exceeded the original1MiB answer limit,
so the measured row remains a validation error.

A read-only download preserved the answer hash. Posthoc attemptv1 raised the
size limit to64MiB but retained20million checker work: it returned unknown at
the work cap after5.64seconds. Attemptv2 raised only the checker work cap to
200million, retaining60seconds/2GiB; independent original-input translation and
RUP proof checking accepted the negative answer in13.50seconds locally.

Plans, outcomes and logs are under research/hard-v2-posthoc-validation-v{1,2}-*
and results/hard-v2-posthoc-validation-v{1,2}. This is a separately bounded
posthoc certificate result, not a replacement benchmark row or a remeasured
solver time. Validation timing on Mac is not comparable to Linux solver timing.
The ongoing full run may expose more such failures; audit every failure after
completion and apply any follow-up policy uniformly, preserving the full matrix.
