# Linux application artifact audit: failed

Rows: 704/704; queries: 176/176; exact ordered-branch representatives: 175.

{
  "properties": 176,
  "imported_properties": 176,
  "collection_unavailable": 0,
  "classifications": {
    "all_methods_definitive": 113,
    "mixed_solved_unresolved": 39,
    "no_method_definitive": 24
  },
  "definitive_by_method": {
    "native-reduced": 143,
    "native-frozen": 138,
    "verifypn-default": 140,
    "smpt-mcc-portable": 117
  },
  "disagreements": 0,
  "duplicate_disagreements": 0,
  "native_only": 11,
  "competitor_only": 9,
  "flagged_queries": {
    "error": 27,
    "nonzero_exit": 61,
    "timeout": 61,
    "memory_limit": 36,
    "inconsistent_definitive_answer": 1
  }
}

Checks saved validator requests/responses, native answer consistency and independent-check labels; does not rerun proofs or witnesses. External answers remain tool-reported. Unfetched tool identities are environment-reported only. Systemd sidecars contain accounting, not independent proof of configured limits; those rely on frozen runner bytes and recorded settings.

Development difficulty screen; one repetition with full planned and imported denominators reported separately. CPU affinity is not exclusive isolation. Instruction counts do not remove timeout censorship or contention. Failures and missing counters retained; no stable timing or superiority claim.

Audit issues:
- Classification reports conflicts or invalid definitive answers

Warnings: 80; all rows, failures, resource sidecars and identities are retained in `audit.json`.
