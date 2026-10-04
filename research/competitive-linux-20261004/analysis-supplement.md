# Supplemental saved-evidence audit

Status: passed. Reconstructed 2208 external rows across both complete blocks.

Coverage, paired gains/losses, repeated solved sets, PAR-2, summed solver/checker costs and conditional timing ratios were recomputed independently for all slots and representatives, by corpus and family.

100 observed definitive external outputs were rejected by the frozen admission rules; exact reasons remain in the JSON.

Historical underlying-log read failures retained: 0.

This supplements the frozen artifact audit under the documented Z3 provenance amendment; the original failed audit remains preserved. The measurement is a contended pilot. It changes no row, deadline, score or reporting rule and executes no solver or proof checker.

| Method | Rejected definitive formula outputs | Overlapping rejection reasons |
|---|---:|---|
| verifypn-default | 0 | none |
| smpt-mcc-portable | 57 | diagnostic-failure: 52, nonzero-exit: 5, outer-timeout: 6, wall-budget: 6 |
| its-mcc | 43 | diagnostic-failure: 11, invalid-wrapper-result: 34, nonzero-exit: 34, outer-timeout: 34, wall-budget: 34 |

These counts describe consistent raw FORMULA results rejected as unknown. They include ITS outputs printed before its wrapper completed. They are separate from accepted coverage; rejection reasons can overlap.

