# SMPT single-core baseline review

Source review, 2026-09-28. No new solver measurements. Existing completed and
running experiments keep their frozen configurations and conclusions.

`vendor/SMPT-portable/smpt/exec/parallelizer.py:384` starts one process for each
effective method. There is no CLI sequential scheduler or worker-count option.
The recorded CPU8 affinity therefore permits concurrent workers sharing one
core. This alone does not establish a performance disadvantage.

The full portable configuration requests ten methods. It does not always run
ten workers: `smpt/smpt.py:520-534` filters PDR-COV for non-monotone targets,
enables SMT and CP only for fully reducible nets, and adds BMC whenever
K-INDUCTION is selected. The method intersection uses a Python set, so requested
method order is not an execution schedule.

`--auto-reduce` is not `--project`. Reachability PDR and state-equation checking
can continue using the original net despite ordinary reduction; complete TFG
projection is a distinct capability (`exec/parallelizer.py:231-279`). Projection
needs `octant.exe` (`interfaces/octant.py:92`), whose availability and behavior
have not been verified for the proposed next screen.

Official `--mcc` has a preliminary WALK/state-equation stage and a separate
portfolio policy (`smpt.py:470-545`), including additional strengthening. The
current harness does not expose this flag. At short outer deadlines the
preliminary stage may consume the available budget; the complete process must
still obey the same deadline as every competitor. Competition mode is not a
sequential mode.

On Linux the harness sets outer grace to zero unless explicitly configured
otherwise (`scripts/benchmark_smpt_classic.py:394-399`). Frozen plans and actual
commands govern the comparison, not generic environment prose mentioning an
extra second. Independent native checking remains separately measured.

## Proposed next configuration screen

Use all 176 fixed general-development-v3 source slots after acquisition and
import audit. Retain unavailable slots and every outcome. Preserve original
PNML/XML, automatic reduction, the same whole-property limits and a single CPU.

| Configuration | Requested methods / policy |
|---|---|
| Full portable | Existing ten-method configuration, unchanged |
| Compact portfolio | WALK STATE-EQUATION BMC K-INDUCTION SMT |
| Unsaturated PDR | PDR-REACH SMT |
| Saturated PDR | PDR-REACH-SATURATED SMT |
| Competition mode | Official --mcc scheduling |

SMT retains fully reducible-net solving in the smaller portfolios; these are
not strict single-method ablations. Include the existing three native controls
and VerifyPN default. This is nine configurations, 1,584 planned rows at one
repeat, before optional mechanism ablations. No claim that any proposed
configuration is faster or stronger has been verified.

Implement these choices in a new isolated runner, leaving live pinned scripts
untouched. Before execution, verify command construction, capability handling,
complete original-property identity, timeout accounting and the completed
matrix audit. Freeze source/tool hashes and row count in the execution plan.
Projection variants require a separate successful capability preflight and
preregistered matrix; do not silently add or omit them after seeing outcomes.

For any later reserved evaluation choose one executed SMPT configuration using
whole-development-cohort definitive coverage first, then capped total solver
wall time for ties, then the fixed table order. Retain disagreements as blockers
to interpretation. Report all development configurations and selection costs.
Their oracle union is diagnostic coverage, not an implemented solver result.
Repeated balanced runs are required before a stable speed claim. All 22
reserved families stay untouched.

The configurations and selection rule above are proposals until the next
execution plan freezes them. They do not rewrite historical coverage counts.
