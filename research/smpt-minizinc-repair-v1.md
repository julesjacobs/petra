# Isolated Linux MiniZinc capability repair

**MiniZinc 2.10.1 with default Gecode 6.4.0 works on the Linux benchmark host.** Direct satisfiable/unsatisfiable models and actual SMPT CP invocations both pass. This repairs a missing dependency for future experiments; no timed benchmark suite ran and no old results or configurations changed.

The official Linux bundle is installed privately at:

```
/home/jules/experiments/pvass-publication/vendor/minizinc-linux-v1/MiniZincIDE-2.10.1-x86_64-linux-gnu
```

Its archive SHA-256, independently matched against the captured GitHub release asset digest, is `b63dd88491d47b05d0eb0ff4aa1112d1e6f77292c023800b20b98851458ce01c`. Acquisition URL and upstream metadata are retained in `smpt-minizinc-release-metadata-v1.json`. No system package, global library, shell startup file or SMPT source was modified.

For a newly registered Linux run, add:

```
--tool-bin vendor/minizinc-linux-v1/MiniZincIDE-2.10.1-x86_64-linux-gnu/bin
```

SMPT invokes `minizinc` without `--solver`. The bundle's existing `share/minizinc/Preferences.json` selects `org.gecode.gecode` by default. The smoke tests use precisely this default, with no solver override. No user MiniZinc preferences, user solver directory, external solver configuration directories, or MiniZinc environment overrides were present. A changed dependency configuration requires a new experiment identity; this does not retroactively repair the earlier SMPT runs.

| Smoke | Checked result |
|---|---|
| MiniZinc `x∈0..1`, `x=1` | Exit 0, `x = 1;` |
| MiniZinc `x∈0..1`, `x=2` | Exit 0, `UNSATISFIABLE` |
| SMPT CP, one token transferred from p to q, EF q≥1 | TRUE, `CONSTRAINT_PROGRAMMING`, model q(1) |
| Same net, EF q≥2 | FALSE, `CONSTRAINT_PROGRAMMING`, MiniZinc `UNSATISFIABLE` |

SMPT ran with `--auto-reduce --methods CP`; TINA fully reduced the fixture and supplied the equation p+q=1. Debug logs retain the generated MiniZinc constraints and solver output. Thus CP actually ran rather than merely appearing among enabled methods. These finite smoke cases establish availability, not general SMPT correctness or performance.

The evidence freezes hashes of all **1,136 bundle files**, **58 loaded shared-library paths**, MiniZinc and FlatZinc executables, Python, TINA `reduce`, SMPT sources, configuration files/absences, inputs and outputs. Bundled libraries are found through their executable's library paths; no `LD_LIBRARY_PATH` change was needed. SMPT source hashes exactly match the earlier application-expansion screen. Other backends listed by `--solvers` were not tested.

Run the read-only preflight on Linux before using this capability:

```
vendor/venv/bin/python research/check-smpt-minizinc-repair-v1.py
```

It checks bundle membership, dependencies, tools, configuration and smoke evidence. It passed after installation. No MiniZinc, FlatZinc or SMPT smoke processes remained. All owned handles are terminal.

Two unsuccessful smoke-driver attempts are preserved. The first omitted the XML description element required by SMPT's positional parser. The second successfully ran CP but used an overly strict technique-label assertion. Only the new fixtures/assertions changed; the third attempt passed all checks.

Evidence: `research/smpt-minizinc-repair-v1.json`, `research/smpt-minizinc-repair-v1/metadata.json`, the complete evidence archive `research/smpt-minizinc-repair-v1-evidence.tar.gz`, and the setup/preflight scripts. The setup script verifies the pinned archive and refuses to overwrite its evidence directory.
