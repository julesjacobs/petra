# Survivor budget sweep

All 18 property runs remain unknown: three unresolved development properties,
two frozen portfolios, and 1-, 5-, and 20-second budgets shared across branches.
The artifact audit passes, including input, executable, selection and script pins.

The properties are DoubleExponent-PT-003 RC02 and RC07, and TokenRing-PT-015 RC12.
Neither the combined portfolio nor the count portfolio gains coverage at larger
budgets under the existing state limits. This does not prove unreachability or
intrinsic hardness.

Across 30 branch invocations, 12 expired externally and 24 exceeded their assigned
wall budget, including process startup and cleanup overhead. All were retained as
unknown. Six other branch invocations prove the second branch of DoubleExponent
RC07 unreachable, with independently checked certificates. Its first branch remains
unknown, so the whole property remains unknown. No sampled memory limit was
exceeded; the largest sampled peak was 1,420,476,416 bytes. Sampling is a lower bound,
not an enforced OS memory ceiling.

Fourteen logs report a time limit, ten contain no JSON answer, and six report
one arithmetic node with no integer model or causal cut. The latter are all the
second branch of DoubleExponent RC07. These outcome summaries do not identify
which earlier portfolio stages consumed the budget. Stage profiling is the next
diagnostic, separate from this frozen comparison.

Plan SHA256: cc61e0ecf13d679bbcf6acdbe4d7dd9b123ac47fe24c57cee1ac9f52f0129c29.
Raw evidence: runs.jsonl and individual branch logs. Audit: audit.json, generated
by ../audit-development-survivors-v1.py. This is one local development sweep;
it provides no held-out or stable timing evidence.
