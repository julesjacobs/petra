# Provenance

Paper: Amir, Barbone, Amat, Jacobs, *Deciding Serializability in Network Systems*, TACAS 2026. https://arxiv.org/abs/2601.02251

Artifact: https://zenodo.org/records/17253581
Archive: https://zenodo.org/api/records/17253581/files/ser_artifact.zip/content
SHA-256: `d5bdbc52b11470fc7c0d74e06c5fe5a32880db5344c06e204cff42ec5831eeeb`

Downloaded on 2026-09-26. Unpacked under `vendor/`; source unchanged. The frontend was built in release mode with the existing Homebrew ISL. The executable bit on its SMPT wrapper was enabled. SMPT was run with its supplied STATE-EQUATION and BMC configuration and Z3 5.1.0. Generated files and build products are not part of the original archive.

The artifact root includes an MIT license for SER; SMPT includes its own GPLv3 license. Original license files are preserved under `vendor/`.

Collection attempted every one of the 47 examples sequentially. Each SMPT invocation was limited to 20 seconds, each complete frontend invocation to 40 seconds. A frontend exit code of zero can still mean TIMEOUT; consult the actual result in the per-program log. Source cases with no backend queries were discharged by preprocessing. Cases that timed out can have only a prefix of their queries captured.

Pro consultation: https://chatgpt.com/c/6ab8245e-dd18-83e9-a7c6-0ac9cd28e682
The current ChatGPT UI labels the selected model family Latest and the selected power Pro. The public source archive URL and detailed context were supplied; file-chooser attachment failed. Pro's conclusions require independent verification.
