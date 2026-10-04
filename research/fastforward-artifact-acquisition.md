# Published FastForward artifact: acquisition and installation assessment

2026-09-28. Archive acquired and inspected only. No solver, build, installer,
package manager, or upstream shell script was run. No remote host was accessed.
No benchmark instances were extracted or imported.

## Provenance

The current [version-1 Figshare metadata](https://api.figshare.com/v2/articles/13573592/versions/1)
identifies [10.6084/m9.figshare.13573592.v1](https://doi.org/10.6084/m9.figshare.13573592.v1),
published 2021-01-14, with an MIT deposit license. Its file identity matches the
previous baseline plan:

| Item | Verified value |
|---|---|
| File | `FastForward.zip`, Figshare file `26048870` |
| Download | `https://ndownloader.figshare.com/files/26048870` |
| Bytes | `960594789` |
| Upstream and measured MD5 | `78521fa06a5b88257b42d4bb519dce35` |
| Measured SHA-256 | `3424e0285729df073756e7947b710b3b7f55eb0d396d9781f32d5ad6872dd65f` |
| ZIP directory entries | `6841` |

The unchanged archive, raw API metadata, acquisition manifest, complete ZIP
directory, dependency assessment, and selected-file hashes are preserved under
`vendor/FastForward-artifact-v1/`. The ZIP directory SHA-256 is
`2ef3d820348075d91af7869e099e51133cf10f8f7b59995ebeeab1adf354367c`.
`inspection-manifest.json` records the **28 selected documentation/source/metadata
files, totaling 727,030 bytes**. Three are Debian control records read from nested
package metadata; no package payload was extracted. ZIP reads checked CRCs for
the directly extracted members. The acquisition manifest's `extracted: false`
describes acquisition before this separate selective inspection.

Reproduction: `python3 scripts/acquire_fastforward_artifact.py`. The script now
pins size, MD5 and SHA-256; preserves partial failures; refuses differing
existing files; and never extracts or executes archive contents. Download log:
`research/fastforward-artifact-download.log`. Download session **81115 completed
with exit 0**; no download remains live.

## Main finding: the published source has an intended no-Gurobi build

This artifact differs from repository commit
`bf6bb6fefd03c640af25b2f5ea0a0dc053d47736` examined in the earlier plan.
The archived README, project file and `Program.cs` have different Git blob
identities; `dependency-inspection.json` records the comparisons. There is no
archived `.git` directory establishing a source commit. Keep artifact and later
repository configurations separately labeled.

In the **published** `artifact/src/fastforward.csproj`, `GUROBI` is added only when
the MSBuild property `GUROBI` equals `true`. Its `Release` configuration does not
unconditionally enable Gurobi. The unrelated `Editor` configuration spells its
symbol `GUROBi`; do not use it for this build. Inspection of all 40 source `.cs`
members found no hard-coded `#define GUROBI`. The Gurobi implementation files,
structural Gurobi method, imports and dispatch calls are conditionally guarded.
The later repository's `HeuristicPicker.cs` and unguarded saturation entrypoint
are absent from this artifact's layout.

The archived README explicitly supports both build modes. Source dispatch confirms:

| Configuration | Source-level dependency |
|---|---|
| `qReachability` | Continuous-reachability heuristic through Z3 |
| `syntactic`, `zero` | No Gurobi heuristic calls |
| `markingEQ` and Z3 syntactic-baseline variants | Z3 implementations; label separately from Gurobi variants |
| `QMarkingEQGurobi`, `NMarkingEQGurobi`, structural Q/N variants | Gurobi compilation and runtime required |

Without the flag, requesting a Gurobi-only heuristic prints an explicit message
and exits with code 5. It must not be counted as a negative answer.

**Verified here:** the intended no-Gurobi source path and its guards. **Not yet
verified:** successful compilation or execution. The project still contains an
unconditional assembly reference to an absent Gurobi DLL. It may produce an
unresolved-reference warning when unused; whether the selected build tolerates
that remains a build check. No compatibility patch has been applied.

The archive contains no Gurobi library or license. Its README specifies Gurobi
**9.0.3**, Linux x86-64, and copying `gurobi90.netstandard20.dll` into `src/gurobi/`;
native `libgurobi90.so` and an activated license are also needed. The README's
historical installer MD5 is `832040cce622ba7f267e26645fcd200d`; this installer was
not downloaded or verified. No license input is needed to attempt the separate
no-Gurobi configuration. Reproducing the paper's Gurobi state-equation modes
requires the licensed configuration; a Z3 mode is not an interchangeable label.

## Runtime and package findings

The artifact includes a **self-contained Linux x86-64 FastForward build** under
`artifact/benchmark/fastforward/`, with a native launcher, managed assembly,
CoreCLR and host libraries. Its runtime configuration specifies
`Microsoft.NETCore.App 3.1.9`. Its dependency manifest contains no Gurobi entry.
No executable or library from that directory has been extracted or run.

For rebuilding, the archive supplies `.NET SDK 3.1.403` Debian packages and
runtime `3.1.9`, plus SDK `2.1.811` and runtime `2.1.23`. The project targets
`netcoreapp3.1`. The direct NuGet versions match the earlier plan: CommandLineParser
2.7.82, CsvHelper 12.3.2, FibonacciHeap 1.1.8, MathNet.Numerics 4.12.0,
Microsoft.NET.Test.Sdk 16.4.0, Microsoft.Z3.x64 4.8.7, Newtonsoft.Json 12.0.3,
OptimizedPriorityQueue 4.2.0, Simbool 0.1.0, and xunit 2.4.1.

Two practical dependencies need explicit handling:

1. **Native Z3 resolution.** The published executable directory contains
   `Microsoft.Z3.dll` but **no `libz3.so`**, and its selected `linux-x64` dependency
   target has no native Z3 asset. The archived NuGet package does contain
   `microsoft.z3.x64/4.8.7/runtimes/ubuntu-x64/native/libz3.so` (24,295,512 bytes).
   Its build target copies only the Windows DLL; its package metadata requires
   `libgomp.so.1` on Linux. Separately bundled `dependencies/z3/bin/libz3.so` is
   from **Z3 4.8.9.0**, according to `include/z3_version.h`. Do not silently mix
   that native version with the 4.8.7 managed package.
2. **Offline restore is not established from the cache alone.** The archive has
   51 NuGet package/version directories. Of the 125 packages in the archived
   `project.assets.json`, **78 are absent from that cache**. That assets file
   also names `/usr/share/dotnet/sdk/NuGetFallbackFolder`; the bundled SDK 2.1 may
   supply the fallback, but its payload was not unpacked or verified here.
   The complete missing list and archived package hashes are saved in
   `dependency-inspection.json`. `nuget.config` clears network sources, and no
   `packages.lock.json` was found.

The runtime's Debian control metadata requires `libgcc1`, `libstdc++6`, `libc6`,
`zlib1g`, `libgssapi-krb5-2`, an accepted ICU version (including `libicu66`), and
`libssl1.0.0`, `libssl1.0.2` or `libssl1.1`. This is a concrete compatibility
requirement for a modern Linux host, even with the self-contained executable.
The README identifies the TACAS21 Ubuntu evaluation VM as its tested environment;
compatibility with our Linux host has not been checked during its live run.

## Precise next setup steps, not performed

1. After the Linux measurement window closes, prepare an isolated Linux x86-64
   environment matching the above native requirements. Do not upgrade the
   target framework or runtime silently. Keep native package identities and
   environment configuration in the baseline manifest.
2. The shortest executable path is to extract **only the archived FastForward
   runtime directory**, plus the matching **4.8.7** native Z3 dependency, into a
   separate runtime installation. Make that dependency discoverable explicitly,
   record this packaging choice, and test native loading. Self-contained runtime
   execution does not require installing an SDK. Label this as the archived
   executable configuration until compilation flags and modes are checked by
   smoke tests; dependency metadata alone does not establish executability.
3. For a separately labeled source rebuild, extract the source and necessary
   dependency packages into an isolated build tree. Pin SDK **3.1.403**, runtime
   **3.1.9**, `Release`, `linux-x64`, and `GUROBI=false`. Restore into a dedicated
   NuGet cache using the archived packages plus a verified SDK fallback, or
   explicitly fetch the missing exact package versions. Generate a lock file
   and compare the resolved versions/content hashes with the archived assets
   before a locked restore. Publish self-contained output to a new directory
   with `--no-restore`; record any required project/packaging change.
4. For Gurobi modes, additionally obtain and verify Gurobi 9.0.3 and a working
   license, provide its managed/native libraries, and publish separately with
   `GUROBI=true`. `InitializeModel` sets logging but does not set `Threads`;
   configure and verify one-thread behavior for the user's single-core track.
5. Before admitting either executable to benchmarks, run tiny weighted/read-arc,
   equality-zero, zero-step, reachable and unreachable-interface cases; check
   mode availability, JSON/error parsing and original witness replay. Re-audit
   the artifact-version parser and integer-overflow boundary instead of assuming
   the later repository's frontend assessment transfers unchanged. Preserve
   unsupported target cases. These are future correctness checks, not results
   obtained by this inspection.

Do not run the upstream `install.sh` wholesale for this purpose: it installs
all bundled Debian packages, builds LoLA/MIST, installs Python 2/3 and plotting
dependencies, and creates a global Z3 symlink. Those are broader than the
FastForward baseline. Both upstream republish scripts delete the existing
benchmark executable directory; use an explicit new output directory instead.

The result is a pinned acquisition and concrete setup plan, **not a verified
executable competitor yet**. No timing, benchmark-difficulty, performance or
novelty conclusion follows from this work.
