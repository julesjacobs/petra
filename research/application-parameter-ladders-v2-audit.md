# Application parameter ladders v2: collection audit

**PASSED: 448/464 slots imported from 28/29 models.** All 464 preregistered slots are retained. TokenRing-PT-050 contributes 16 unavailable slots: its recorded extraction failure exceeded the 1 GiB expanded-archive limit. Its downloaded archive and partial files remain preserved and hashed. This audit checked the recorded failure evidence; it did not decompress that archive again to reproduce the limit.

The frozen selection remains `e729cd00a2facdddcb0273dda32915b0f5a78f17d6e70185a1cb172a80fec605`. The collected manifest is `5bff9f35b8b5b60c588fa379ab9c8ac3c65c96905c706bc40bbaaee2b98437f4`. All 22 reserved/evaluation families are excluded; no reserved payloads were read.

Verified all 29 downloaded archive checksums and URLs, collector/importer snapshots and runtime identity, every manifest-referenced input hash (2149 distinct files / 1194181487 bytes), and the complete retained corpus inventory (2331 files / 1526060589 bytes, including failed-model partial files). Source selection, per-model limits, property slots, and collection outcomes agree.

The 448 imported properties have **442 exact ordered-branch representatives**, in 6 duplicate groups containing 12 properties. There are **0 matching signatures** against the earlier development manifests listed in the JSON report, including both FastForward imports, earlier MCC development/stress/application sets, and SMPT classic. Reserved/evaluation rows are filtered before branch files are read. Earlier development views overlap and are not additional independent datasets.

Duplicates mean identical ordered canonical branch bytes. They do not establish graph equivalence or absence of renamed/reordered duplicates. Including EF/AG kind gives **443 original-property representatives**: FMS-PT-50000 RC01 (AG) and RC12 (EF) share branches but have opposite property polarity. Keep the full 464-slot denominator and report duplicate-aware coverage separately, retaining the 16 unavailable slots in both views; acquisition failure is not solver difficulty.

This is an artifact-identity audit, not an independent proof of importer semantics or benchmark hardness. No solver ran. Reproduce with `python3 research/audit-application-parameter-ladders-v2.py`; detailed identities, all-file hashes, duplicate membership, comparison exclusions, and failure evidence are in `research/application-parameter-ladders-v2-audit.json`.

Audit issues: [].
