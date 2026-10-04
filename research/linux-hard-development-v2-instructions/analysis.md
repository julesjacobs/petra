# Instruction-count comparison

Complete matrix: 69 properties × 4 methods × 1 repetitions.

| Method | Solved runs / total | Stable solved properties / total | Unstable outcomes | Timeout runs | OOM runs | Missing / invalid / multiplexed counters |
|---|---:|---:|---:|---:|---:|---:|
| native-focused | 48 / 69 | 48 / 69 | 0 | 15 | 3 | 3 / 0 / 0 |
| native-symbolic | 49 / 69 | 49 / 69 | 0 | 12 | 1 | 1 / 0 / 0 |
| verifypn-default | 32 / 69 | 32 / 69 | 0 | 36 | 1 | 1 / 0 / 0 |
| smpt-full-portable | 9 / 69 | 9 / 69 | 0 | 40 | 20 | 22 / 0 / 0 |

## native-focused / native-symbolic

Geometric mean of per-property median instruction ratios: **0.959121** across **48** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| ff_random_walk_Boop_simple_vf_satabs_2_multi_40_0_7d80d074 | reachable | 155408058742 | 220706202940 | 0.70414 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_25_0_109789c0 | reachable | 390185360376 | 335186564622 | 1.16408 |
| DLCflexbar-PT-8b__RC04 | reachable | 63630564020 | 65972703904 | 0.964498 |
| ff_random_walk_peterson_vs_satabs_2_multi_100_0_0dc8b190 | reachable | 457379900679 | 452108382524 | 1.01166 |
| ff_random_walk_double_lock_p1_vs_satabs_2_multi_50_0_85cc4181 | reachable | 137463629609 | 125752844807 | 1.09313 |
| ff_random_walk_peterson_vs_satabs_2_multi_60_0_1f69f86b | reachable | 318284147530 | 277454638332 | 1.14716 |
| ff_random_walk_dekker_vs_satabs_2_multi_50_0_a060d7a3 | reachable | 171177962533 | 162129891923 | 1.05581 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_30_0_cfcf0d79 | reachable | 19697178583 | 27242552084 | 0.72303 |
| ff_random_walk_dekker_vs_satabs_2_multi_25_0_ce78db7b | reachable | 388158147182 | 423012985417 | 0.917603 |
| ff_random_walk_pthread5_vs_satabs_4_multi_40_0_df2950d1 | reachable | 289481179017 | 282621287309 | 1.02427 |
| ff_random_walk_double_lock_p3_vs_satabs_3_multi_100_0_964d5f2c | reachable | 357317166036 | 306034894945 | 1.16757 |
| ff_random_walk_double_lock_p3_vs_satabs_3_multi_75_0_28df1c8f | reachable | 293794439391 | 408197231235 | 0.719736 |
| DLCflexbar-PT-8b__RC11 | unreachable | 4769848219 | 4769869977 | 0.999995 |
| ff_random_walk_peterson_vs_satabs_2_multi_90_0_63a50e3a | reachable | 247335794870 | 269193626403 | 0.918803 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_75_0_4ea8c7e2 | reachable | 189687690298 | 185790352728 | 1.02098 |
| ff_random_walk_pthread5_vs_satabs_3_multi_60_0_25230f49 | reachable | 314522503340 | 110473114850 | 2.84705 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_60_0_7e4914f0 | reachable | 486291761293 | 493574896349 | 0.985244 |
| ff_random_walk_peterson_vs_satabs_2_multi_75_0_7b18af2a | reachable | 257634670910 | 239037391115 | 1.0778 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_40_0_6edcf2e4 | reachable | 27047683070 | 31737828393 | 0.852222 |
| DLCflexbar-PT-7b__RC04 | reachable | 19349979248 | 27478511273 | 0.704186 |
| DLCflexbar-PT-7b__RC08 | reachable | 27772519519 | 35895976616 | 0.773694 |
| ff_random_walk_double_lock_p1_vs_satabs_3_multi_90_0_d9e4397c | reachable | 295760650207 | 245158798922 | 1.2064 |
| ff_random_walk_dekker_vs_satabs_2_multi_30_0_60ea6be9 | reachable | 320998112498 | 360731780688 | 0.889853 |
| ff_random_walk_dekker_vs_satabs_2_multi_100_0_cd5224b8 | reachable | 579768050967 | 466781778134 | 1.24205 |
| ff_random_walk_dekker_vs_satabs_2_multi_75_0_39e56bc6 | reachable | 188966377617 | 230892293499 | 0.818418 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_35_0_45390a04 | reachable | 26925722780 | 31449704602 | 0.856152 |
| ff_random_walk_szymanski_vs_satabs_2_multi_50_0_82faf12b | reachable | 343709762796 | 381932035859 | 0.899924 |
| ff_random_walk_double_lock_p2_vs_satabs_2_multi_90_0_991eb40a | reachable | 528896063840 | 530474136909 | 0.997025 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_100_0_d3394668 | reachable | 27680103869 | 27820374740 | 0.994958 |
| DLCflexbar-PT-8b__RC12 | unreachable | 4571718569 | 4571620993 | 1.00002 |
| ff_random_walk_pthread5_vs_satabs_4_multi_75_0_a5685f8e | reachable | 297237610006 | 298140529368 | 0.996971 |
| ff_random_walk_szymanski_vs_satabs_2_multi_90_0_f3c821ab | reachable | 438862794050 | 428605306302 | 1.02393 |
| DLCflexbar-PT-7b__RC11 | reachable | 64491106886 | 72698265187 | 0.887107 |
| DLCflexbar-PT-8b__RC01 | reachable | 279511321452 | 289504132472 | 0.965483 |
| CloudOpsManagement-PT-20480by10240__RC12 | reachable | 43902108846 | 43816169915 | 1.00196 |
| DLCflexbar-PT-7b__RC01 | reachable | 26646583346 | 34836450040 | 0.764905 |
| DLCflexbar-PT-7b__RC15 | reachable | 5077138381 | 13224908522 | 0.383907 |
| DLCflexbar-PT-7b__RC06 | reachable | 25653485735 | 33880484852 | 0.757176 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_90_0_7680cd5d | reachable | 456165843320 | 437477022801 | 1.04272 |
| ff_random_walk_double_lock_p2_vs_satabs_2_multi_75_0_0282cae8 | reachable | 366993587120 | 416600604678 | 0.880924 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_75_0_4caa7013 | reachable | 90840252349 | 90791687645 | 1.00053 |
| ff_random_walk_double_lock_p1_vs_satabs_2_multi_75_0_4e32d951 | reachable | 374348328846 | 169023522910 | 2.21477 |
| ff_random_walk_pthread5_vs_satabs_3_multi_75_0_b294b730 | reachable | 298526968168 | 331508984386 | 0.900509 |
| ff_random_walk_dekker_vs_satabs_2_multi_35_0_9d7456ea | reachable | 193498536901 | 163263274601 | 1.18519 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_50_0_ca513233 | reachable | 140916087234 | 188752190655 | 0.746567 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_25_0_473b7be1 | reachable | 20537649123 | 24855292449 | 0.826289 |
| ff_random_walk_szymanski_vs_satabs_2_multi_100_0_4df7a98c | reachable | 351554866524 | 460386765849 | 0.763608 |
| ff_random_walk_pthread5_vs_satabs_3_multi_90_0_a70a8618 | reachable | 236578400367 | 232217289197 | 1.01878 |

Excluded properties: 21.

## native-focused / verifypn-default

Geometric mean of per-property median instruction ratios: **0.630461** across **27** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_25_0_109789c0 | reachable | 390185360376 | 234237310532 | 1.66577 |
| DLCflexbar-PT-8b__RC04 | reachable | 63630564020 | 39122903671 | 1.62643 |
| ff_random_walk_peterson_vs_satabs_2_multi_100_0_0dc8b190 | reachable | 457379900679 | 437498845733 | 1.04544 |
| ff_random_walk_dekker_vs_satabs_2_multi_25_0_ce78db7b | reachable | 388158147182 | 182330825470 | 2.12887 |
| DLCflexbar-PT-8b__RC11 | unreachable | 4769848219 | 38168982547 | 0.124967 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_75_0_4ea8c7e2 | reachable | 189687690298 | 629358127759 | 0.301399 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_60_0_7e4914f0 | reachable | 486291761293 | 298076139372 | 1.63143 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_40_0_6edcf2e4 | reachable | 27047683070 | 433931295419 | 0.0623317 |
| DLCflexbar-PT-7b__RC04 | reachable | 19349979248 | 32110144545 | 0.602613 |
| DLCflexbar-PT-7b__RC08 | reachable | 27772519519 | 45984409060 | 0.603955 |
| ff_random_walk_double_lock_p1_vs_satabs_3_multi_90_0_d9e4397c | reachable | 295760650207 | 356871629358 | 0.828759 |
| ff_random_walk_dekker_vs_satabs_2_multi_30_0_60ea6be9 | reachable | 320998112498 | 61164192456 | 5.24814 |
| ff_random_walk_dekker_vs_satabs_2_multi_75_0_39e56bc6 | reachable | 188966377617 | 44979197733 | 4.20119 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_35_0_45390a04 | reachable | 26925722780 | 433647472399 | 0.0620913 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_100_0_d3394668 | reachable | 27680103869 | 239653377664 | 0.115501 |
| DLCflexbar-PT-8b__RC12 | unreachable | 4571718569 | 36812777169 | 0.124188 |
| DLCflexbar-PT-7b__RC11 | reachable | 64491106886 | 61740929240 | 1.04454 |
| DLCflexbar-PT-8b__RC01 | reachable | 279511321452 | 148263690223 | 1.88523 |
| DLCflexbar-PT-7b__RC01 | reachable | 26646583346 | 33339951420 | 0.799239 |
| DLCflexbar-PT-7b__RC15 | reachable | 5077138381 | 31088643648 | 0.163312 |
| DLCflexbar-PT-7b__RC06 | reachable | 25653485735 | 48350082308 | 0.530578 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_90_0_7680cd5d | reachable | 456165843320 | 239370040695 | 1.90569 |
| ff_random_walk_double_lock_p2_vs_satabs_2_multi_75_0_0282cae8 | reachable | 366993587120 | 508480722011 | 0.721745 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_75_0_4caa7013 | reachable | 90840252349 | 277695934516 | 0.327121 |
| ff_random_walk_pthread5_vs_satabs_3_multi_75_0_b294b730 | reachable | 298526968168 | 272143826931 | 1.09695 |
| ff_random_walk_dekker_vs_satabs_2_multi_35_0_9d7456ea | reachable | 193498536901 | 42524982485 | 4.55023 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_25_0_473b7be1 | reachable | 20537649123 | 220764631772 | 0.0930296 |

Excluded properties: 42.

## native-focused / smpt-full-portable

Geometric mean of per-property median instruction ratios: **2.27285** across **1** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| CloudOpsManagement-PT-20480by10240__RC12 | reachable | 43902108846 | 19315917701 | 2.27285 |

Excluded properties: 68.

## native-symbolic / verifypn-default

Geometric mean of per-property median instruction ratios: **0.709162** across **28** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_25_0_109789c0 | reachable | 335186564622 | 234237310532 | 1.43097 |
| DLCflexbar-PT-8b__RC04 | reachable | 65972703904 | 39122903671 | 1.68629 |
| ff_random_walk_peterson_vs_satabs_2_multi_100_0_0dc8b190 | reachable | 452108382524 | 437498845733 | 1.03339 |
| ff_random_walk_dekker_vs_satabs_2_multi_25_0_ce78db7b | reachable | 423012985417 | 182330825470 | 2.32003 |
| DLCflexbar-PT-8b__RC11 | unreachable | 4769869977 | 38168982547 | 0.124967 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_75_0_4ea8c7e2 | reachable | 185790352728 | 629358127759 | 0.295206 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_60_0_7e4914f0 | reachable | 493574896349 | 298076139372 | 1.65587 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_40_0_6edcf2e4 | reachable | 31737828393 | 433931295419 | 0.0731402 |
| DLCflexbar-PT-7b__RC04 | reachable | 27478511273 | 32110144545 | 0.855758 |
| DLCflexbar-PT-7b__RC08 | reachable | 35895976616 | 45984409060 | 0.780612 |
| ff_random_walk_double_lock_p1_vs_satabs_3_multi_90_0_d9e4397c | reachable | 245158798922 | 356871629358 | 0.686966 |
| ff_random_walk_dekker_vs_satabs_2_multi_30_0_60ea6be9 | reachable | 360731780688 | 61164192456 | 5.89776 |
| ff_random_walk_dekker_vs_satabs_2_multi_75_0_39e56bc6 | reachable | 230892293499 | 44979197733 | 5.13331 |
| DLCflexbar-PT-8b__RC02 | reachable | 95245587933 | 99715553170 | 0.955173 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_35_0_45390a04 | reachable | 31449704602 | 433647472399 | 0.0725237 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_100_0_d3394668 | reachable | 27820374740 | 239653377664 | 0.116086 |
| DLCflexbar-PT-8b__RC12 | unreachable | 4571620993 | 36812777169 | 0.124186 |
| DLCflexbar-PT-7b__RC11 | reachable | 72698265187 | 61740929240 | 1.17747 |
| DLCflexbar-PT-8b__RC01 | reachable | 289504132472 | 148263690223 | 1.95263 |
| DLCflexbar-PT-7b__RC01 | reachable | 34836450040 | 33339951420 | 1.04489 |
| DLCflexbar-PT-7b__RC15 | reachable | 13224908522 | 31088643648 | 0.425394 |
| DLCflexbar-PT-7b__RC06 | reachable | 33880484852 | 48350082308 | 0.700733 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_90_0_7680cd5d | reachable | 437477022801 | 239370040695 | 1.82762 |
| ff_random_walk_double_lock_p2_vs_satabs_2_multi_75_0_0282cae8 | reachable | 416600604678 | 508480722011 | 0.819305 |
| ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_75_0_4caa7013 | reachable | 90791687645 | 277695934516 | 0.326946 |
| ff_random_walk_pthread5_vs_satabs_3_multi_75_0_b294b730 | reachable | 331508984386 | 272143826931 | 1.21814 |
| ff_random_walk_dekker_vs_satabs_2_multi_35_0_9d7456ea | reachable | 163263274601 | 42524982485 | 3.83923 |
| ff_random_walk_Function_Pointer3_vs_satabs_3_multi_25_0_473b7be1 | reachable | 24855292449 | 220764631772 | 0.112587 |

Excluded properties: 41.

## native-symbolic / smpt-full-portable

Geometric mean of per-property median instruction ratios: **2.2684** across **1** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| CloudOpsManagement-PT-20480by10240__RC12 | reachable | 43816169915 | 19315917701 | 2.2684 |

Excluded properties: 68.

## verifypn-default / smpt-full-portable

Geometric mean of per-property median instruction ratios: **unavailable** across **0** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|

Excluded properties: 69.

## Repeat variability

| Method | Eligible properties | Median max/min | Largest max/min |
|---|---:|---:|---:|
| native-focused | 48 | unavailable | unavailable |
| native-symbolic | 49 | unavailable | unavailable |
| verifypn-default | 32 | unavailable | unavailable |
| smpt-full-portable | 9 | unavailable | unavailable |

Definitive disagreements: [].

- Instructions count user-space work in the measured process tree; they are not wall-time speedups.
- Timeout and OOM runs remain in failure counts. Their counters never enter ratios; elapsed-time censoring still depends on machine load.
- Each pair uses its own stable, matching, fully scheduled common-solved subset; inspect the case list and denominator.
- Instruction variability uses stable solved properties with positive counters at 100% time_running_percent in every repeat; it is unavailable with one repetition.
- Definitive verdict agreement does not independently validate external solver answers.
- Frontend and preprocessing scope remain those recorded in environment.json; this analysis does not establish matched input scopes.
