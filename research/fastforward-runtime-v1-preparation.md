# FastForward archived Linux runtime: local preparation

Status: **prepared, not executed or deployed**. Linux session 31070 was live;
no remote action, dependency probe, Rust change/build, installer, package manager
or benchmark was performed. Packaging session **15236 terminated with exit 0**;
all extraction, hashing and archive-verification processes are terminal.

## Deliverable

- Directory: `vendor/FastForward-runtime-v1/`.
- Deployment package: `vendor/FastForward-runtime-v1.tar.gz`.
- Size: **46,069,878 bytes**.
- SHA256: **cdd2b7d30b9e69d893ce5a57dd3f1ef60e89edea3e42957354a3f3c1c2ead87e**.
- Package: **386 files**, 473 archive entries; every packaged file's hash was
  verified by rereading the tarball without extracting or executing it.
- `vendor/FastForward-runtime-v1.tar.gz.manifest.json` records the package identity.
- `package-files.json` covers every payload file except itself; its SHA256 is
  **763dea64fba746e9239a21c7bdafae2c9c58fb6efca4594c91d0023b01c0d03a**.

The archive hash was rechecked before extraction against the pinned Figshare
version-1 file 26048870:
`3424e0285729df073756e7947b710b3b7f55eb0d396d9781f32d5ad6872dd65f`.
`scripts/prepare_fastforward_runtime.py` performs the bounded selective extraction
and static ELF inspection. No archive executable was invoked. It refuses existing
output, path traversal, symlinks, special files, duplicate destinations, encrypted
entries and unexpected inventory; file and total size caps are 64/128 MiB.
All selected ZIP members were fully read with CRC checks.

## Verified contents

The entire published `artifact/benchmark/fastforward` directory plus the matching
NuGet Z3 4.8.7 native library yields **302 files / 116,237,181 bytes**. Binary
contents are unchanged. Permissions are normalized to 0644, with the FastForward
launcher executable. Unrelated test DLLs/resources inside that published runtime
folder remain preserved. No benchmark instances were extracted.

`extraction-manifest.json` records each member path, bytes, CRC, SHA256 and modes.
The managed `Microsoft.Z3.dll` byte-matches the archived 4.8.7 NuGet binding:
`378e46881093550fe0044405952ae9be9dc441012782183334e9105f022b557e`.
The selected native library is from that same package, not the separate bundled
4.8.9 distribution.

`static-inspection.json` records 17 ELF64 little-endian AMD64 files. The launcher
and createdump request `/lib64/ld-linux-x86-64.so.2`. Runtime configuration remains
self-contained `.NET Core 3.1.9`; dependency metadata names managed Z3 4.8.7 and
no Gurobi entry. These are metadata facts, not successful execution evidence.

External DT_NEEDED names include libc, libstdc++, libgcc_s, pthread/dl/rt/m,
zlib, GSSAPI, libcurl and liblttng-ust.so.0. The latter belongs to the optional
tracing provider; actual startup need is untested. ICU and OpenSSL are loaded
dynamically and require separate checks. NuGet declares libgomp.so.1, while the
supplied native Z3 has no direct DT_NEEDED edge to it. No Linux host dependency
availability was inferred from the macOS preparation.

## Notices and launch plan

`notice-manifest.json` preserves **62 relevant archived license, notice and NuGet
metadata files / 339,946 bytes**, including .NET runtime 3.1.9 notices and matching
NuGet packages. The 4.8.7 Z3 package has no embedded license text; its preserved
nuspec points to source commit `30e7c225cd510400eacd41d0a83e013b835a8ece`.
The separate archive's Z3 4.8.9 license is preserved under an explicitly labeled
directory, without claiming that it authenticates the 4.8.7 license. No network
fetch was performed.

`launch-configuration.json` and `launch.sh` specify future isolated Linux x86-64
execution. The wrapper refuses other platforms, selects packaged native library
paths, disables shared framework fallback and clears globalization-invariant
switches, retaining the original framework and default globalization behavior.
It permits explicitly labeled A*/best-first modes with zero, syntactic,
marking-equation Z3 and continuous-reachability Z3 heuristics. Actual compiled
mode availability remains unverified; Gurobi has not been supplied.

`smoke-plan.json` supplies seven authored tiny LoLA/formula fixtures: zero-step,
one-step, an unreachable exact-zero target, weighted enabled/disabled guards,
and enabled/disabled self-loop guards. Expected results follow directly from
those tiny nets; they are **not observed FastForward results**. Additional planned
checks cover startup/help, native Z3 resolution, unavailable/invalid heuristics,
malformed inputs and parser integer boundaries. Positive witnesses require
independent original-net replay; errors and malformed output remain unknown.

After the Linux timing window closes, the next owner can deploy into a fresh
isolated directory, verify package hashes, resolve dependencies in a compatible
isolated Linux userland, then run sequential 10-second/2-GiB smoke invocations
with the complete process tree pinned to CPU8. Do not patch host global libraries
or enable invariant globalization to bypass missing dependencies. The source
parser uses permissive regexes; accepted grammar and output schema require
executable interface checks before benchmark admission.

No timing, performance, executable capability or baseline competitiveness claim
follows from this preparation. No follow-on work or process remains active.
