# Instruction-count comparison

Complete matrix: 368 properties × 3 methods × 1 repetitions.

| Method | Solved runs / total | Stable solved properties / total | Unstable outcomes | Timeout runs | OOM runs | Missing / invalid / multiplexed counters |
|---|---:|---:|---:|---:|---:|---:|
| frozen-v2 | 119 / 368 | 119 / 368 | 0 | 142 | 109 | 127 / 0 / 0 |
| portfolio-local | 275 / 368 | 275 / 368 | 0 | 83 | 19 | 35 / 0 / 0 |
| verifypn-default | 341 / 368 | 341 / 368 | 0 | 27 | 0 | 0 / 0 / 0 |

## frozen-v2 / portfolio-local

Geometric mean of per-property median instruction ratios: **1.84097** across **114** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| JoinFreeModules-PT-2000__RC09 | reachable | 8649637440 | 11762576149 | 0.735352 |
| JoinFreeModules-PT-2000__RC10 | reachable | 8388744812 | 17262082952 | 0.485964 |
| CircularTrains-PT-768__RC13 | reachable | 777974626 | 537856058 | 1.44644 |
| JoinFreeModules-PT-1000__RC00 | reachable | 4529601611 | 4431584754 | 1.02212 |
| CloudOpsManagement-PT-10240by05120__RC08 | reachable | 1437394874 | 225450847 | 6.37565 |
| CircularTrains-PT-384__RC05 | unreachable | 690829618 | 345671613 | 1.99851 |
| CloudOpsManagement-PT-05120by02560__RC01 | unreachable | 259336424 | 196230001 | 1.32159 |
| CloudOpsManagement-PT-20480by10240__RC05 | unreachable | 236972823 | 195135096 | 1.2144 |
| CloudOpsManagement-PT-10240by05120__RC09 | reachable | 1386392381 | 219129804 | 6.32681 |
| CloudOpsManagement-PT-10240by05120__RC02 | unreachable | 257821144 | 195913906 | 1.31599 |
| CircularTrains-PT-768__RC05 | reachable | 667274960 | 549565486 | 1.21419 |
| Echo-PT-d05r03__RC07 | unreachable | 2280704294 | 1877882848 | 1.21451 |
| CloudOpsManagement-PT-10240by05120__RC14 | unreachable | 387618046 | 201604204 | 1.92267 |
| CloudOpsManagement-PT-05120by02560__RC10 | reachable | 337770364 | 209473237 | 1.61248 |
| GPUForwardProgress-PT-40a__RC07 | reachable | 5263752269 | 249249332 | 21.1184 |
| JoinFreeModules-PT-2000__RC11 | reachable | 8334718023 | 24924492525 | 0.334399 |
| CircularTrains-PT-384__RC15 | reachable | 527195541 | 354225757 | 1.4883 |
| Echo-PT-d04r03__RC04 | unreachable | 788248511 | 587212384 | 1.34236 |
| DLCflexbar-PT-8a__RC07 | unreachable | 8330034505 | 7954029472 | 1.04727 |
| CircularTrains-PT-384__RC00 | reachable | 480362176 | 360893540 | 1.33104 |
| CircularTrains-PT-768__RC08 | reachable | 733076300 | 513020098 | 1.42894 |
| JoinFreeModules-PT-1000__RC11 | reachable | 4590608832 | 9080202446 | 0.505562 |
| CircularTrains-PT-768__RC15 | reachable | 733044611 | 514224985 | 1.42553 |
| CloudOpsManagement-PT-10240by05120__RC00 | reachable | 1385606759 | 223520792 | 6.19901 |
| Echo-PT-d04r03__RC00 | reachable | 28830401675 | 715902261 | 40.2714 |
| CloudOpsManagement-PT-05120by02560__RC09 | reachable | 1397761877 | 222305070 | 6.28758 |
| DLCflexbar-PT-8a__RC05 | unreachable | 8432848154 | 7854665931 | 1.07361 |
| CloudOpsManagement-PT-20480by10240__RC02 | reachable | 1929681574 | 5099381763 | 0.378415 |
| CloudOpsManagement-PT-05120by02560__RC12 | reachable | 1522224758 | 220904649 | 6.89087 |
| CloudOpsManagement-PT-05120by02560__RC02 | unreachable | 381540758 | 201684182 | 1.89177 |
| CircularTrains-PT-384__RC01 | unreachable | 505390977 | 345165891 | 1.4642 |
| JoinFreeModules-PT-5000__RC08 | reachable | 20486423056 | 62574088886 | 0.327395 |
| CloudOpsManagement-PT-10240by05120__RC07 | reachable | 1497796670 | 216329986 | 6.92367 |
| DLCflexbar-PT-8a__RC10 | unreachable | 9124022191 | 7859670474 | 1.16087 |
| GPUForwardProgress-PT-40a__RC13 | reachable | 18565897958 | 2643580727 | 7.02301 |
| CloudOpsManagement-PT-20480by10240__RC15 | reachable | 1878904760 | 5547465341 | 0.338696 |
| CloudOpsManagement-PT-05120by02560__RC15 | unreachable | 254660517 | 195949819 | 1.29962 |
| DLCflexbar-PT-8a__RC11 | unreachable | 10457104052 | 8824735884 | 1.18498 |
| CloudOpsManagement-PT-10240by05120__RC15 | unreachable | 255515059 | 195517684 | 1.30686 |
| CircularTrains-PT-768__RC03 | reachable | 758145205 | 542776868 | 1.39679 |
| GPUForwardProgress-PT-40a__RC06 | reachable | 9555000591 | 246032574 | 38.8363 |
| DLCflexbar-PT-8a__RC14 | unreachable | 8432670950 | 7984190484 | 1.05617 |
| JoinFreeModules-PT-1000__RC03 | reachable | 4580840699 | 6420511021 | 0.71347 |
| CloudOpsManagement-PT-05120by02560__RC13 | unreachable | 318632269 | 198227905 | 1.6074 |
| CircularTrains-PT-768__RC06 | reachable | 740978756 | 533364644 | 1.38925 |
| DLCflexbar-PT-8a__RC04 | unreachable | 8404529350 | 7964883452 | 1.0552 |
| CircularTrains-PT-384__RC12 | reachable | 464821826 | 350795711 | 1.32505 |
| CloudOpsManagement-PT-05120by02560__RC11 | reachable | 1821182391 | 219896467 | 8.282 |
| CircularTrains-PT-384__RC02 | reachable | 576202234 | 363235902 | 1.5863 |
| CloudOpsManagement-PT-10240by05120__RC13 | reachable | 359877225 | 232965616 | 1.54477 |
| CloudOpsManagement-PT-20480by10240__RC00 | unreachable | 320162993 | 198729571 | 1.61105 |
| CloudOpsManagement-PT-10240by05120__RC05 | reachable | 1870477372 | 5629057784 | 0.33229 |
| CloudOpsManagement-PT-10240by05120__RC06 | unreachable | 256978488 | 196104161 | 1.31042 |
| GPUForwardProgress-PT-40a__RC14 | reachable | 9484973220 | 247081855 | 38.388 |
| CloudOpsManagement-PT-05120by02560__RC06 | unreachable | 254900548 | 195468715 | 1.30405 |
| CloudOpsManagement-PT-05120by02560__RC04 | reachable | 1398828239 | 206938380 | 6.75964 |
| Echo-PT-d04r03__RC09 | unreachable | 853240627 | 593537667 | 1.43755 |
| JoinFreeModules-PT-5000__RC06 | reachable | 21843675897 | 33585464612 | 0.650391 |
| CircularTrains-PT-384__RC13 | unreachable | 517546344 | 345652044 | 1.4973 |
| CloudOpsManagement-PT-20480by10240__RC04 | reachable | 1438790094 | 197202353 | 7.29601 |
| CloudOpsManagement-PT-05120by02560__RC08 | reachable | 1455498950 | 197481822 | 7.37029 |
| GPUForwardProgress-PT-40a__RC08 | unreachable | 9247010323 | 244332896 | 37.8459 |
| CloudOpsManagement-PT-20480by10240__RC03 | unreachable | 253178699 | 195429017 | 1.2955 |
| JoinFreeModules-PT-2000__RC00 | reachable | 8516015044 | 9719397945 | 0.876188 |
| CircularTrains-PT-384__RC11 | unreachable | 505489204 | 345121120 | 1.46467 |
| CircularTrains-PT-768__RC01 | reachable | 732823477 | 513742836 | 1.42644 |
| JoinFreeModules-PT-1000__RC07 | reachable | 4825274546 | 5090850038 | 0.947833 |
| GPUForwardProgress-PT-40a__RC03 | reachable | 8109024358 | 279107904 | 29.0534 |
| CloudOpsManagement-PT-05120by02560__RC14 | reachable | 1855990467 | 232370250 | 7.98721 |
| CloudOpsManagement-PT-10240by05120__RC01 | reachable | 952048256 | 198160265 | 4.80444 |
| CircularTrains-PT-768__RC00 | reachable | 734416812 | 513886868 | 1.42914 |
| CloudOpsManagement-PT-10240by05120__RC04 | reachable | 1483831013 | 228105576 | 6.50502 |
| CloudOpsManagement-PT-10240by05120__RC11 | reachable | 810618372 | 196589054 | 4.12342 |
| CloudOpsManagement-PT-20480by10240__RC07 | unreachable | 237988851 | 195059135 | 1.22009 |
| CloudOpsManagement-PT-20480by10240__RC11 | reachable | 1975252315 | 2176923829 | 0.907359 |
| CloudOpsManagement-PT-20480by10240__RC01 | reachable | 2109624575 | 2265899269 | 0.931032 |
| CloudOpsManagement-PT-10240by05120__RC10 | reachable | 402357909 | 2232827964 | 0.180201 |
| JoinFreeModules-PT-5000__RC15 | reachable | 23898214310 | 24568082224 | 0.972734 |
| Echo-PT-d05r03__RC00 | unreachable | 3000715877 | 1887356374 | 1.5899 |
| CircularTrains-PT-768__RC07 | reachable | 758209673 | 539931176 | 1.40427 |
| CloudOpsManagement-PT-05120by02560__RC07 | reachable | 358862005 | 219544220 | 1.63458 |
| Echo-PT-d04r03__RC03 | reachable | 36125634779 | 676121049 | 53.4307 |
| GPUForwardProgress-PT-40a__RC05 | reachable | 7299688291 | 250560448 | 29.1334 |
| CloudOpsManagement-PT-20480by10240__RC14 | reachable | 3343368167 | 7693363150 | 0.434578 |
| Echo-PT-d04r03__RC07 | unreachable | 816018324 | 586770625 | 1.39069 |
| JoinFreeModules-PT-1000__RC08 | reachable | 4650082144 | 9397149150 | 0.49484 |
| JoinFreeModules-PT-2000__RC13 | reachable | 9141827168 | 10091940524 | 0.905854 |
| GPUForwardProgress-PT-40a__RC11 | reachable | 19129719968 | 271966028 | 70.3386 |
| CloudOpsManagement-PT-20480by10240__RC08 | unreachable | 258653502 | 196469994 | 1.3165 |
| CircularTrains-PT-768__RC09 | reachable | 743681375 | 520108332 | 1.42986 |
| CloudOpsManagement-PT-05120by02560__RC00 | reachable | 1283087738 | 208521908 | 6.15325 |
| CloudOpsManagement-PT-10240by05120__RC03 | reachable | 1874138847 | 5513207944 | 0.339936 |
| AutoFlight-PT-96a__RC13 | unreachable | 1663117738 | 842029081 | 1.97513 |
| DLCflexbar-PT-8a__RC01 | unreachable | 9216396213 | 8831197581 | 1.04362 |
| GPUForwardProgress-PT-40a__RC01 | reachable | 16610941398 | 1677760095 | 9.90067 |
| JoinFreeModules-PT-5000__RC01 | reachable | 20432277015 | 28761655174 | 0.7104 |
| DLCflexbar-PT-8a__RC06 | unreachable | 10331480833 | 8938676561 | 1.15582 |
| JoinFreeModules-PT-2000__RC03 | reachable | 8797628341 | 11173701460 | 0.787351 |
| CloudOpsManagement-PT-10240by05120__RC12 | reachable | 840461081 | 196919892 | 4.26804 |
| JoinFreeModules-PT-5000__RC13 | reachable | 21402455217 | 36931252526 | 0.579522 |
| CloudOpsManagement-PT-20480by10240__RC06 | unreachable | 253943305 | 195758543 | 1.29723 |
| DLCflexbar-PT-8a__RC03 | unreachable | 10392524569 | 8943574203 | 1.16201 |
| CloudOpsManagement-PT-20480by10240__RC09 | unreachable | 252738699 | 195750841 | 1.29112 |
| DLCflexbar-PT-8a__RC12 | unreachable | 8616578343 | 7975620806 | 1.08036 |
| JoinFreeModules-PT-1000__RC12 | reachable | 4905853166 | 27273647820 | 0.179875 |
| JoinFreeModules-PT-1000__RC09 | reachable | 4889608207 | 9083978801 | 0.538267 |
| CloudOpsManagement-PT-20480by10240__RC13 | unreachable | 315700417 | 198495453 | 1.59047 |
| JoinFreeModules-PT-2000__RC08 | reachable | 8328859018 | 12173161000 | 0.684199 |
| CircularTrains-PT-384__RC04 | reachable | 465328789 | 351048085 | 1.32554 |
| CloudOpsManagement-PT-20480by10240__RC10 | unreachable | 253105677 | 195523451 | 1.2945 |
| CloudOpsManagement-PT-05120by02560__RC03 | reachable | 359698531 | 227831289 | 1.57879 |
| JoinFreeModules-PT-2000__RC04 | reachable | 8338570994 | 12831730963 | 0.64984 |
| GPUForwardProgress-PT-40a__RC04 | reachable | 2870005435 | 250527347 | 11.4559 |
| JoinFreeModules-PT-1000__RC06 | reachable | 4513181197 | 6632454619 | 0.680469 |

Excluded properties: 254.

## frozen-v2 / verifypn-default

Geometric mean of per-property median instruction ratios: **11.8278** across **116** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| JoinFreeModules-PT-2000__RC09 | reachable | 8649637440 | 3328551155 | 2.59862 |
| JoinFreeModules-PT-2000__RC10 | reachable | 8388744812 | 2199672437 | 3.81363 |
| CircularTrains-PT-768__RC13 | reachable | 777974626 | 177207936 | 4.39018 |
| JoinFreeModules-PT-1000__RC00 | reachable | 4529601611 | 1751209040 | 2.58656 |
| CloudOpsManagement-PT-10240by05120__RC08 | reachable | 1437394874 | 8307275 | 173.028 |
| CircularTrains-PT-384__RC05 | unreachable | 690829618 | 33319215 | 20.7337 |
| CloudOpsManagement-PT-05120by02560__RC01 | unreachable | 259336424 | 5190673 | 49.962 |
| CloudOpsManagement-PT-20480by10240__RC05 | unreachable | 236972823 | 3079715 | 76.9463 |
| CloudOpsManagement-PT-10240by05120__RC09 | reachable | 1386392381 | 166068580 | 8.34831 |
| CloudOpsManagement-PT-10240by05120__RC02 | unreachable | 257821144 | 4334747 | 59.4778 |
| CircularTrains-PT-768__RC05 | reachable | 667274960 | 205760162 | 3.24297 |
| Echo-PT-d05r03__RC07 | unreachable | 2280704294 | 305570026 | 7.46377 |
| CloudOpsManagement-PT-10240by05120__RC14 | unreachable | 387618046 | 5506587 | 70.3917 |
| CloudOpsManagement-PT-05120by02560__RC10 | reachable | 337770364 | 72847665 | 4.63667 |
| JoinFreeModules-PT-5000__RC05 | reachable | 20203358070 | 13770796289 | 1.46712 |
| GPUForwardProgress-PT-40a__RC07 | reachable | 5263752269 | 31576128 | 166.7 |
| JoinFreeModules-PT-2000__RC11 | reachable | 8334718023 | 2772199143 | 3.00654 |
| CircularTrains-PT-384__RC15 | reachable | 527195541 | 73600982 | 7.16289 |
| Echo-PT-d04r03__RC04 | unreachable | 788248511 | 72673762 | 10.8464 |
| DLCflexbar-PT-8a__RC07 | unreachable | 8330034505 | 1254582216 | 6.63969 |
| CircularTrains-PT-384__RC00 | reachable | 480362176 | 71682148 | 6.70128 |
| CircularTrains-PT-768__RC08 | reachable | 733076300 | 132747896 | 5.52232 |
| JoinFreeModules-PT-1000__RC11 | reachable | 4590608832 | 1164451511 | 3.94229 |
| CircularTrains-PT-768__RC15 | reachable | 733044611 | 131332869 | 5.58158 |
| CloudOpsManagement-PT-10240by05120__RC00 | reachable | 1385606759 | 209993882 | 6.59832 |
| Echo-PT-d04r03__RC00 | reachable | 28830401675 | 688411184 | 41.8796 |
| CloudOpsManagement-PT-05120by02560__RC09 | reachable | 1397761877 | 139635586 | 10.0101 |
| JoinFreeModules-PT-2000__RC07 | reachable | 8741723634 | 7416369217 | 1.17871 |
| DLCflexbar-PT-8a__RC05 | unreachable | 8432848154 | 1132988597 | 7.44301 |
| CloudOpsManagement-PT-20480by10240__RC02 | reachable | 1929681574 | 983899867 | 1.96126 |
| CloudOpsManagement-PT-05120by02560__RC12 | reachable | 1522224758 | 230958632 | 6.5909 |
| CloudOpsManagement-PT-05120by02560__RC02 | unreachable | 381540758 | 5041761 | 75.6761 |
| CircularTrains-PT-384__RC01 | unreachable | 505390977 | 33322914 | 15.1665 |
| JoinFreeModules-PT-5000__RC08 | reachable | 20486423056 | 7548684424 | 2.71391 |
| CloudOpsManagement-PT-10240by05120__RC07 | reachable | 1497796670 | 169407135 | 8.8414 |
| DLCflexbar-PT-8a__RC10 | unreachable | 9124022191 | 1132990229 | 8.05305 |
| GPUForwardProgress-PT-40a__RC13 | reachable | 18565897958 | 37717090 | 492.241 |
| CloudOpsManagement-PT-20480by10240__RC15 | reachable | 1878904760 | 796960809 | 2.35759 |
| CloudOpsManagement-PT-05120by02560__RC15 | unreachable | 254660517 | 3309733 | 76.9429 |
| DLCflexbar-PT-8a__RC11 | unreachable | 10457104052 | 1255451961 | 8.32935 |
| CloudOpsManagement-PT-10240by05120__RC15 | unreachable | 255515059 | 3917361 | 65.2263 |
| CircularTrains-PT-768__RC03 | reachable | 758145205 | 192262843 | 3.94327 |
| GPUForwardProgress-PT-40a__RC06 | reachable | 9555000591 | 21736320 | 439.587 |
| DLCflexbar-PT-8a__RC14 | unreachable | 8432670950 | 1255369911 | 6.71728 |
| JoinFreeModules-PT-1000__RC03 | reachable | 4580840699 | 1564464668 | 2.92806 |
| CloudOpsManagement-PT-05120by02560__RC05 | reachable | 14089584822 | 112956145 | 124.735 |
| CloudOpsManagement-PT-05120by02560__RC13 | unreachable | 318632269 | 3522515 | 90.4559 |
| CircularTrains-PT-768__RC06 | reachable | 740978756 | 170430734 | 4.34768 |
| DLCflexbar-PT-8a__RC04 | unreachable | 8404529350 | 1255373907 | 6.69484 |
| CircularTrains-PT-384__RC12 | reachable | 464821826 | 56292339 | 8.25728 |
| CloudOpsManagement-PT-05120by02560__RC11 | reachable | 1821182391 | 130758403 | 13.9278 |
| CircularTrains-PT-384__RC02 | reachable | 576202234 | 85789053 | 6.7165 |
| CloudOpsManagement-PT-10240by05120__RC13 | reachable | 359877225 | 101453698 | 3.54721 |
| CloudOpsManagement-PT-20480by10240__RC00 | unreachable | 320162993 | 4598701 | 69.6203 |
| CloudOpsManagement-PT-10240by05120__RC05 | reachable | 1870477372 | 439420147 | 4.25669 |
| CloudOpsManagement-PT-10240by05120__RC06 | unreachable | 256978488 | 3830339 | 67.0903 |
| GPUForwardProgress-PT-40a__RC14 | reachable | 9484973220 | 27910737 | 339.832 |
| CloudOpsManagement-PT-05120by02560__RC06 | unreachable | 254900548 | 3486340 | 73.1141 |
| CloudOpsManagement-PT-05120by02560__RC04 | reachable | 1398828239 | 65882142 | 21.2323 |
| Echo-PT-d04r03__RC09 | unreachable | 853240627 | 84457772 | 10.1026 |
| JoinFreeModules-PT-5000__RC06 | reachable | 21843675897 | 18390301622 | 1.18778 |
| CircularTrains-PT-384__RC13 | unreachable | 517546344 | 33438783 | 15.4774 |
| CloudOpsManagement-PT-20480by10240__RC04 | reachable | 1438790094 | 305685088 | 4.70677 |
| CloudOpsManagement-PT-05120by02560__RC08 | reachable | 1455498950 | 71815114 | 20.2673 |
| GPUForwardProgress-PT-40a__RC08 | unreachable | 9247010323 | 10785719 | 857.338 |
| CloudOpsManagement-PT-20480by10240__RC03 | unreachable | 253178699 | 3465822 | 73.0501 |
| JoinFreeModules-PT-2000__RC00 | reachable | 8516015044 | 7371963342 | 1.15519 |
| CircularTrains-PT-384__RC11 | unreachable | 505489204 | 33438220 | 15.1171 |
| CircularTrains-PT-768__RC01 | reachable | 732823477 | 131338514 | 5.57965 |
| JoinFreeModules-PT-1000__RC07 | reachable | 4825274546 | 2478210379 | 1.94708 |
| GPUForwardProgress-PT-40a__RC03 | reachable | 8109024358 | 38591056 | 210.127 |
| CloudOpsManagement-PT-05120by02560__RC14 | reachable | 1855990467 | 76249201 | 24.3411 |
| CloudOpsManagement-PT-10240by05120__RC01 | reachable | 952048256 | 747556785 | 1.27355 |
| CircularTrains-PT-768__RC00 | reachable | 734416812 | 132056065 | 5.5614 |
| CloudOpsManagement-PT-10240by05120__RC04 | reachable | 1483831013 | 149462384 | 9.92779 |
| CloudOpsManagement-PT-10240by05120__RC11 | reachable | 810618372 | 112079008 | 7.23256 |
| CloudOpsManagement-PT-20480by10240__RC07 | unreachable | 237988851 | 3122649 | 76.2138 |
| CloudOpsManagement-PT-20480by10240__RC11 | reachable | 1975252315 | 322009484 | 6.13414 |
| CloudOpsManagement-PT-20480by10240__RC01 | reachable | 2109624575 | 201286146 | 10.4807 |
| CloudOpsManagement-PT-10240by05120__RC10 | reachable | 402357909 | 178745722 | 2.25101 |
| JoinFreeModules-PT-5000__RC15 | reachable | 23898214310 | 19107408249 | 1.25073 |
| Echo-PT-d05r03__RC00 | unreachable | 3000715877 | 335942187 | 8.93224 |
| CircularTrains-PT-768__RC07 | reachable | 758209673 | 189789528 | 3.995 |
| CloudOpsManagement-PT-05120by02560__RC07 | reachable | 358862005 | 92521225 | 3.8787 |
| GPUForwardProgress-PT-40a__RC05 | reachable | 7299688291 | 39921497 | 182.851 |
| CloudOpsManagement-PT-20480by10240__RC14 | reachable | 3343368167 | 5365094337 | 0.62317 |
| Echo-PT-d04r03__RC07 | unreachable | 816018324 | 82028969 | 9.94793 |
| JoinFreeModules-PT-1000__RC08 | reachable | 4650082144 | 2023389946 | 2.29816 |
| JoinFreeModules-PT-2000__RC13 | reachable | 9141827168 | 6946084464 | 1.31611 |
| GPUForwardProgress-PT-40a__RC11 | reachable | 19129719968 | 28958372 | 660.594 |
| CloudOpsManagement-PT-20480by10240__RC08 | unreachable | 258653502 | 4610459 | 56.1015 |
| CircularTrains-PT-768__RC09 | reachable | 743681375 | 162243162 | 4.58375 |
| CloudOpsManagement-PT-05120by02560__RC00 | reachable | 1283087738 | 42268941 | 30.3553 |
| CloudOpsManagement-PT-10240by05120__RC03 | reachable | 1874138847 | 507059994 | 3.69609 |
| AutoFlight-PT-96a__RC13 | unreachable | 1663117738 | 206572389 | 8.05102 |
| DLCflexbar-PT-8a__RC01 | unreachable | 9216396213 | 1190595455 | 7.741 |
| GPUForwardProgress-PT-40a__RC01 | reachable | 16610941398 | 22897736 | 725.44 |
| JoinFreeModules-PT-5000__RC01 | reachable | 20432277015 | 7641292297 | 2.67393 |
| DLCflexbar-PT-8a__RC06 | unreachable | 10331480833 | 1190565854 | 8.67779 |
| JoinFreeModules-PT-2000__RC03 | reachable | 8797628341 | 2111861484 | 4.16582 |
| CloudOpsManagement-PT-10240by05120__RC12 | reachable | 840461081 | 112079657 | 7.49878 |
| JoinFreeModules-PT-5000__RC13 | reachable | 21402455217 | 21700841204 | 0.98625 |
| CloudOpsManagement-PT-20480by10240__RC06 | unreachable | 253943305 | 3326433 | 76.341 |
| DLCflexbar-PT-8a__RC03 | unreachable | 10392524569 | 1361147793 | 7.63512 |
| CloudOpsManagement-PT-20480by10240__RC09 | unreachable | 252738699 | 3465919 | 72.9211 |
| DLCflexbar-PT-8a__RC12 | unreachable | 8616578343 | 1254585963 | 6.86807 |
| JoinFreeModules-PT-1000__RC12 | reachable | 4905853166 | 1755527703 | 2.79452 |
| JoinFreeModules-PT-1000__RC09 | reachable | 4889608207 | 1164572137 | 4.19863 |
| CloudOpsManagement-PT-20480by10240__RC13 | unreachable | 315700417 | 3548619 | 88.9643 |
| JoinFreeModules-PT-2000__RC08 | reachable | 8328859018 | 2647014996 | 3.14651 |
| CircularTrains-PT-384__RC04 | reachable | 465328789 | 56109220 | 8.29327 |
| CloudOpsManagement-PT-20480by10240__RC10 | unreachable | 253105677 | 3465922 | 73.0269 |
| CloudOpsManagement-PT-05120by02560__RC03 | reachable | 359698531 | 92176933 | 3.90226 |
| JoinFreeModules-PT-2000__RC04 | reachable | 8338570994 | 1732838561 | 4.81209 |
| GPUForwardProgress-PT-40a__RC04 | reachable | 2870005435 | 30488240 | 94.1348 |
| JoinFreeModules-PT-1000__RC06 | reachable | 4513181197 | 729959064 | 6.18279 |

Excluded properties: 252.

## portfolio-local / verifypn-default

Geometric mean of per-property median instruction ratios: **4.56755** across **259** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| Echo-PT-d05r03__RC06 | reachable | 4805750948 | 14971581322 | 0.320992 |
| JoinFreeModules-PT-2000__RC09 | reachable | 11762576149 | 3328551155 | 3.53384 |
| AutoFlight-PT-96a__RC09 | unreachable | 849486674 | 146817145 | 5.78602 |
| JoinFreeModules-PT-2000__RC10 | reachable | 17262082952 | 2199672437 | 7.84757 |
| Echo-PT-d03r07__RC06 | reachable | 3911353413 | 3288505458 | 1.1894 |
| CircularTrains-PT-384__RC09 | unreachable | 347040657 | 38220143 | 9.08005 |
| CircularTrains-PT-768__RC13 | reachable | 537856058 | 177207936 | 3.03517 |
| JoinFreeModules-PT-1000__RC00 | reachable | 4431584754 | 1751209040 | 2.53059 |
| AutoFlight-PT-96b__RC06 | reachable | 6755302081 | 2137928752 | 3.15974 |
| GPUForwardProgress-PT-40b__RC07 | unreachable | 427393173 | 43542191 | 9.81561 |
| CloudOpsManagement-PT-10240by05120__RC08 | reachable | 225450847 | 8307275 | 27.139 |
| CircularTrains-PT-384__RC05 | unreachable | 345671613 | 33319215 | 10.3745 |
| CloudOpsManagement-PT-05120by02560__RC01 | unreachable | 196230001 | 5190673 | 37.8043 |
| CloudOpsManagement-PT-20480by10240__RC05 | unreachable | 195135096 | 3079715 | 63.3614 |
| CircularTrains-PT-768__RC14 | unreachable | 509243933 | 78237267 | 6.50897 |
| CloudOpsManagement-PT-10240by05120__RC09 | reachable | 219129804 | 166068580 | 1.31951 |
| Echo-PT-d03r07__RC01 | unreachable | 2079132246 | 2736225216 | 0.759854 |
| AutoFlight-PT-96a__RC07 | unreachable | 840382899 | 177758080 | 4.72768 |
| AutoFlight-PT-48b__RC08 | reachable | 1119627655 | 395187734 | 2.83315 |
| CANConstruction-PT-080__RC03 | reachable | 18881388247 | 11311709060 | 1.66919 |
| CANConstruction-PT-100__RC07 | reachable | 24994003264 | 26490462715 | 0.94351 |
| GPUForwardProgress-PT-36b__RC07 | unreachable | 436991516 | 87342557 | 5.00319 |
| CloudOpsManagement-PT-10240by05120__RC02 | unreachable | 195913906 | 4334747 | 45.1962 |
| CircularTrains-PT-768__RC05 | reachable | 549565486 | 205760162 | 2.6709 |
| Echo-PT-d05r03__RC07 | unreachable | 1877882848 | 305570026 | 6.14551 |
| CloudOpsManagement-PT-10240by05120__RC14 | unreachable | 201604204 | 5506587 | 36.6115 |
| GPUForwardProgress-PT-40b__RC04 | reachable | 448296231 | 162796505 | 2.75372 |
| AutoFlight-PT-96b__RC03 | unreachable | 3506729048 | 1435933796 | 2.44212 |
| CloudOpsManagement-PT-05120by02560__RC10 | reachable | 209473237 | 72847665 | 2.8755 |
| GPUForwardProgress-PT-36b__RC02 | reachable | 395182037 | 87990375 | 4.4912 |
| GPUForwardProgress-PT-40a__RC07 | reachable | 249249332 | 31576128 | 7.8936 |
| Echo-PT-d05r03__RC03 | unreachable | 2134064715 | 535668495 | 3.98393 |
| JoinFreeModules-PT-2000__RC11 | reachable | 24924492525 | 2772199143 | 8.99087 |
| CircularTrains-PT-384__RC15 | reachable | 354225757 | 73600982 | 4.81279 |
| Echo-PT-d05r03__RC05 | reachable | 3793816915 | 9388169238 | 0.404106 |
| Echo-PT-d03r07__RC05 | reachable | 4006245980 | 6135687768 | 0.652942 |
| Echo-PT-d04r03__RC04 | unreachable | 587212384 | 72673762 | 8.08012 |
| DLCflexbar-PT-8a__RC15 | unreachable | 7988294816 | 1411232036 | 5.66051 |
| AutoFlight-PT-48b__RC07 | reachable | 3533198422 | 559333963 | 6.3168 |
| DLCflexbar-PT-8a__RC07 | unreachable | 7954029472 | 1254582216 | 6.33998 |
| GPUForwardProgress-PT-36b__RC15 | reachable | 537950880 | 83233353 | 6.46316 |
| CircularTrains-PT-384__RC00 | reachable | 360893540 | 71682148 | 5.03464 |
| CircularTrains-PT-768__RC08 | reachable | 513020098 | 132747896 | 3.86462 |
| JoinFreeModules-PT-1000__RC11 | reachable | 9080202446 | 1164451511 | 7.79784 |
| CircularTrains-PT-768__RC15 | reachable | 514224985 | 131332869 | 3.91543 |
| Echo-PT-d03r07__RC13 | reachable | 7209952309 | 4399683350 | 1.63874 |
| AutoFlight-PT-96a__RC08 | unreachable | 1010580718 | 166456486 | 6.07114 |
| JoinFreeModules-PT-1000__RC04 | reachable | 7103150523 | 3133874695 | 2.26657 |
| Echo-PT-d03r07__RC00 | unreachable | 1883911363 | 600273671 | 3.13842 |
| GPUForwardProgress-PT-36b__RC05 | reachable | 546366837 | 133101293 | 4.1049 |
| CloudOpsManagement-PT-10240by05120__RC00 | reachable | 223520792 | 209993882 | 1.06442 |
| CANConstruction-PT-080__RC13 | unreachable | 13092702269 | 2762529155 | 4.73939 |
| GPUForwardProgress-PT-40a__RC15 | unreachable | 244320608 | 11796850 | 20.7107 |
| GPUForwardProgress-PT-40b__RC13 | reachable | 495002474 | 156819363 | 3.15651 |
| GPUForwardProgress-PT-40b__RC01 | reachable | 963955509 | 98589912 | 9.77743 |
| Echo-PT-d05r03__RC15 | reachable | 7468178344 | 11805195737 | 0.632618 |
| Echo-PT-d04r03__RC00 | reachable | 715902261 | 688411184 | 1.03993 |
| CloudOpsManagement-PT-05120by02560__RC09 | reachable | 222305070 | 139635586 | 1.59204 |
| CircularTrains-PT-768__RC12 | unreachable | 548972100 | 98661000 | 5.56423 |
| GPUForwardProgress-PT-40b__RC09 | reachable | 485915282 | 174203267 | 2.78936 |
| DLCflexbar-PT-8a__RC05 | unreachable | 7854665931 | 1132988597 | 6.9327 |
| AutoFlight-PT-96b__RC13 | unreachable | 2088220149 | 739773523 | 2.82278 |
| AutoFlight-PT-96a__RC14 | reachable | 1232247186 | 313720443 | 3.92785 |
| CloudOpsManagement-PT-20480by10240__RC02 | reachable | 5099381763 | 983899867 | 5.18283 |
| AutoFlight-PT-96a__RC06 | reachable | 1914914094 | 481684744 | 3.97545 |
| CloudOpsManagement-PT-05120by02560__RC12 | reachable | 220904649 | 230958632 | 0.956468 |
| CloudOpsManagement-PT-05120by02560__RC02 | unreachable | 201684182 | 5041761 | 40.0027 |
| AutoFlight-PT-48b__RC13 | reachable | 3832274518 | 1528881199 | 2.50659 |
| DLCflexbar-PT-8a__RC13 | unreachable | 8967110267 | 1255497004 | 7.14228 |
| CircularTrains-PT-384__RC01 | unreachable | 345165891 | 33322914 | 10.3582 |
| CircularTrains-PT-384__RC10 | unreachable | 389890494 | 62332453 | 6.25502 |
| CANConstruction-PT-090__RC14 | reachable | 20002614914 | 18519318645 | 1.08009 |
| JoinFreeModules-PT-5000__RC08 | reachable | 62574088886 | 7548684424 | 8.2894 |
| CloudOpsManagement-PT-10240by05120__RC07 | reachable | 216329986 | 169407135 | 1.27698 |
| DLCflexbar-PT-8a__RC10 | unreachable | 7859670474 | 1132990229 | 6.9371 |
| CANConstruction-PT-090__RC04 | unreachable | 17272619759 | 4423208947 | 3.905 |
| GPUForwardProgress-PT-40a__RC13 | reachable | 2643580727 | 37717090 | 70.0897 |
| AutoFlight-PT-96a__RC02 | unreachable | 845165898 | 130130431 | 6.49476 |
| GPUForwardProgress-PT-36b__RC03 | unreachable | 519860499 | 91842340 | 5.66036 |
| CloudOpsManagement-PT-20480by10240__RC15 | reachable | 5547465341 | 796960809 | 6.96078 |
| AutoFlight-PT-96b__RC01 | unreachable | 2495925272 | 958471560 | 2.60407 |
| Echo-PT-d03r07__RC14 | reachable | 6755826450 | 4073503263 | 1.65848 |
| AutoFlight-PT-48b__RC06 | reachable | 2406145260 | 1410792496 | 1.70553 |
| CloudOpsManagement-PT-05120by02560__RC15 | unreachable | 195949819 | 3309733 | 59.2041 |
| DLCflexbar-PT-8a__RC11 | unreachable | 8824735884 | 1255451961 | 7.02913 |
| Echo-PT-d04r03__RC11 | unreachable | 593653288 | 79152559 | 7.50011 |
| CloudOpsManagement-PT-10240by05120__RC15 | unreachable | 195517684 | 3917361 | 49.9106 |
| CircularTrains-PT-768__RC02 | unreachable | 545638534 | 83077521 | 6.56782 |
| CircularTrains-PT-768__RC03 | reachable | 542776868 | 192262843 | 2.8231 |
| GPUForwardProgress-PT-40a__RC06 | reachable | 246032574 | 21736320 | 11.319 |
| GPUForwardProgress-PT-36b__RC14 | unreachable | 387816033 | 45441566 | 8.53439 |
| GPUForwardProgress-PT-36b__RC04 | unreachable | 374606954 | 129989114 | 2.88183 |
| AutoFlight-PT-96a__RC10 | unreachable | 829168326 | 169279956 | 4.89821 |
| Echo-PT-d03r07__RC02 | unreachable | 1886254479 | 926422560 | 2.03606 |
| Echo-PT-d04r03__RC12 | unreachable | 591605440 | 69069227 | 8.5654 |
| AutoFlight-PT-96a__RC04 | unreachable | 999374347 | 173519046 | 5.75945 |
| DLCflexbar-PT-8a__RC14 | unreachable | 7984190484 | 1255369911 | 6.36003 |
| AutoFlight-PT-48b__RC05 | unreachable | 1314610054 | 232734480 | 5.64854 |
| Echo-PT-d05r03__RC01 | reachable | 6739319387 | 5441114221 | 1.23859 |
| CANConstruction-PT-080__RC15 | reachable | 14907227913 | 12147645928 | 1.22717 |
| GPUForwardProgress-PT-40b__RC00 | reachable | 406650391 | 87488053 | 4.64807 |
| Echo-PT-d03r07__RC07 | unreachable | 1852188037 | 513856506 | 3.60448 |
| Echo-PT-d03r07__RC11 | unreachable | 1859607626 | 1384110027 | 1.34354 |
| JoinFreeModules-PT-1000__RC03 | reachable | 6420511021 | 1564464668 | 4.10397 |
| GPUForwardProgress-PT-36b__RC10 | unreachable | 362265256 | 38194655 | 9.48471 |
| CloudOpsManagement-PT-05120by02560__RC13 | unreachable | 198227905 | 3522515 | 56.2745 |
| Echo-PT-d04r03__RC14 | reachable | 715510780 | 589069502 | 1.21465 |
| CircularTrains-PT-768__RC06 | reachable | 533364644 | 170430734 | 3.12951 |
| DLCflexbar-PT-8a__RC04 | unreachable | 7964883452 | 1255373907 | 6.34463 |
| DLCflexbar-PT-8a__RC09 | unreachable | 8932866176 | 1604994394 | 5.56567 |
| GPUForwardProgress-PT-40a__RC10 | unreachable | 257411288 | 10942931 | 23.5231 |
| CircularTrains-PT-384__RC12 | reachable | 350795711 | 56292339 | 6.23168 |
| JoinFreeModules-PT-1000__RC15 | reachable | 20444050083 | 1961282707 | 10.4238 |
| Echo-PT-d05r03__RC13 | unreachable | 2136020178 | 17937092823 | 0.119084 |
| Echo-PT-d03r07__RC15 | reachable | 6438618054 | 8716842646 | 0.738641 |
| Echo-PT-d03r07__RC12 | reachable | 9005454033 | 4629268028 | 1.94533 |
| Echo-PT-d05r03__RC02 | unreachable | 2325866814 | 997140429 | 2.33254 |
| AutoFlight-PT-96a__RC01 | unreachable | 780951106 | 121302176 | 6.43806 |
| Echo-PT-d05r03__RC14 | reachable | 7539172682 | 33249875642 | 0.226743 |
| GPUForwardProgress-PT-40b__RC06 | reachable | 598650735 | 142974049 | 4.18713 |
| Echo-PT-d04r03__RC06 | unreachable | 653489001 | 87119911 | 7.50103 |
| AutoFlight-PT-48b__RC00 | unreachable | 1637630640 | 1188697169 | 1.37767 |
| CloudOpsManagement-PT-05120by02560__RC11 | reachable | 219896467 | 130758403 | 1.6817 |
| GPUForwardProgress-PT-40a__RC02 | unreachable | 244253733 | 11757688 | 20.774 |
| CircularTrains-PT-384__RC02 | reachable | 363235902 | 85789053 | 4.23406 |
| GPUForwardProgress-PT-40b__RC14 | unreachable | 468306446 | 77782457 | 6.02072 |
| GPUForwardProgress-PT-40b__RC02 | reachable | 461780331 | 118527348 | 3.89598 |
| CloudOpsManagement-PT-10240by05120__RC13 | reachable | 232965616 | 101453698 | 2.29628 |
| CANConstruction-PT-100__RC14 | reachable | 23383188493 | 27020917317 | 0.865374 |
| CloudOpsManagement-PT-20480by10240__RC00 | unreachable | 198729571 | 4598701 | 43.2143 |
| CloudOpsManagement-PT-10240by05120__RC05 | reachable | 5629057784 | 439420147 | 12.8102 |
| Echo-PT-d04r03__RC08 | reachable | 746210873 | 886960211 | 0.841313 |
| CloudOpsManagement-PT-10240by05120__RC06 | unreachable | 196104161 | 3830339 | 51.1976 |
| Echo-PT-d05r03__RC11 | reachable | 3319899765 | 4388055881 | 0.756576 |
| GPUForwardProgress-PT-36b__RC09 | reachable | 473447875 | 158791947 | 2.98156 |
| GPUForwardProgress-PT-40b__RC12 | unreachable | 530043481 | 52022711 | 10.1887 |
| GPUForwardProgress-PT-36b__RC00 | reachable | 406110174 | 89751065 | 4.52485 |
| CANConstruction-PT-090__RC00 | reachable | 22395416214 | 17018213737 | 1.31597 |
| Echo-PT-d04r03__RC10 | reachable | 5740061066 | 1410763744 | 4.06876 |
| AutoFlight-PT-96b__RC08 | reachable | 15094606611 | 1554418531 | 9.71077 |
| GPUForwardProgress-PT-40a__RC14 | reachable | 247081855 | 27910737 | 8.85257 |
| CloudOpsManagement-PT-05120by02560__RC06 | unreachable | 195468715 | 3486340 | 56.067 |
| CloudOpsManagement-PT-05120by02560__RC04 | reachable | 206938380 | 65882142 | 3.14104 |
| Echo-PT-d04r03__RC09 | unreachable | 593537667 | 84457772 | 7.02763 |
| JoinFreeModules-PT-5000__RC06 | reachable | 33585464612 | 18390301622 | 1.82626 |
| CircularTrains-PT-384__RC13 | unreachable | 345652044 | 33438783 | 10.3369 |
| CloudOpsManagement-PT-20480by10240__RC04 | reachable | 197202353 | 305685088 | 0.645116 |
| GPUForwardProgress-PT-40a__RC00 | unreachable | 265553732 | 21894093 | 12.129 |
| GPUForwardProgress-PT-40b__RC10 | unreachable | 394631422 | 154491474 | 2.55439 |
| CANConstruction-PT-090__RC10 | unreachable | 17249327941 | 4327067279 | 3.98638 |
| AutoFlight-PT-96b__RC14 | reachable | 28736857020 | 3945263340 | 7.28389 |
| AutoFlight-PT-96a__RC12 | reachable | 1656111859 | 361220580 | 4.58477 |
| AutoFlight-PT-96a__RC11 | unreachable | 841857737 | 177773467 | 4.73556 |
| CircularTrains-PT-768__RC11 | unreachable | 506542543 | 83445527 | 6.07034 |
| CloudOpsManagement-PT-05120by02560__RC08 | reachable | 197481822 | 71815114 | 2.74986 |
| GPUForwardProgress-PT-40a__RC08 | unreachable | 244332896 | 10785719 | 22.6534 |
| AutoFlight-PT-48b__RC10 | unreachable | 1169977084 | 288420149 | 4.0565 |
| CloudOpsManagement-PT-20480by10240__RC03 | unreachable | 195429017 | 3465822 | 56.3875 |
| JoinFreeModules-PT-2000__RC00 | reachable | 9719397945 | 7371963342 | 1.31843 |
| CircularTrains-PT-384__RC11 | unreachable | 345121120 | 33438220 | 10.3212 |
| CircularTrains-PT-768__RC01 | reachable | 513742836 | 131338514 | 3.91159 |
| Echo-PT-d04r03__RC02 | unreachable | 665930969 | 381426668 | 1.7459 |
| JoinFreeModules-PT-1000__RC07 | reachable | 5090850038 | 2478210379 | 2.05424 |
| GPUForwardProgress-PT-40b__RC15 | unreachable | 384221692 | 69294002 | 5.5448 |
| GPUForwardProgress-PT-36b__RC08 | unreachable | 364073714 | 37474485 | 9.71524 |
| GPUForwardProgress-PT-36b__RC11 | reachable | 409975446 | 78269829 | 5.23798 |
| GPUForwardProgress-PT-40a__RC03 | reachable | 279107904 | 38591056 | 7.23245 |
| CloudOpsManagement-PT-05120by02560__RC14 | reachable | 232370250 | 76249201 | 3.04751 |
| AutoFlight-PT-48b__RC09 | reachable | 1173074694 | 1443588023 | 0.81261 |
| CircularTrains-PT-768__RC04 | reachable | 546020486 | 188270505 | 2.90019 |
| CloudOpsManagement-PT-10240by05120__RC01 | reachable | 198160265 | 747556785 | 0.265077 |
| CircularTrains-PT-768__RC00 | reachable | 513886868 | 132056065 | 3.89143 |
| Echo-PT-d03r07__RC04 | reachable | 7182255967 | 9383598915 | 0.765405 |
| AutoFlight-PT-96b__RC04 | reachable | 23328560182 | 1997077361 | 11.6814 |
| CircularTrains-PT-384__RC07 | reachable | 413551160 | 94865250 | 4.35935 |
| AutoFlight-PT-48b__RC14 | unreachable | 1151728932 | 396854482 | 2.90214 |
| Echo-PT-d05r03__RC04 | reachable | 7072579337 | 15294119208 | 0.462438 |
| CloudOpsManagement-PT-10240by05120__RC04 | reachable | 228105576 | 149462384 | 1.52617 |
| CloudOpsManagement-PT-10240by05120__RC11 | reachable | 196589054 | 112079008 | 1.75402 |
| AutoFlight-PT-96a__RC03 | reachable | 840553630 | 516647829 | 1.62694 |
| CloudOpsManagement-PT-20480by10240__RC07 | unreachable | 195059135 | 3122649 | 62.4659 |
| Echo-PT-d03r07__RC08 | reachable | 3358673119 | 6326185439 | 0.530916 |
| CloudOpsManagement-PT-20480by10240__RC11 | reachable | 2176923829 | 322009484 | 6.76043 |
| CloudOpsManagement-PT-20480by10240__RC01 | reachable | 2265899269 | 201286146 | 11.2571 |
| Echo-PT-d03r07__RC10 | unreachable | 2510322274 | 1409271694 | 1.78129 |
| CloudOpsManagement-PT-10240by05120__RC10 | reachable | 2232827964 | 178745722 | 12.4916 |
| JoinFreeModules-PT-5000__RC15 | reachable | 24568082224 | 19107408249 | 1.28579 |
| Echo-PT-d05r03__RC00 | unreachable | 1887356374 | 335942187 | 5.6181 |
| CircularTrains-PT-768__RC07 | reachable | 539931176 | 189789528 | 2.84489 |
| CloudOpsManagement-PT-05120by02560__RC07 | reachable | 219544220 | 92521225 | 2.37291 |
| GPUForwardProgress-PT-40a__RC09 | unreachable | 244774901 | 10828836 | 22.604 |
| GPUForwardProgress-PT-36b__RC13 | reachable | 9686542634 | 179585683 | 53.9383 |
| CANConstruction-PT-090__RC15 | reachable | 23353027849 | 18288846713 | 1.2769 |
| Echo-PT-d05r03__RC08 | unreachable | 1890074895 | 538101608 | 3.51249 |
| GPUForwardProgress-PT-40a__RC05 | reachable | 250560448 | 39921497 | 6.27633 |
| CloudOpsManagement-PT-20480by10240__RC14 | reachable | 7693363150 | 5365094337 | 1.43397 |
| Echo-PT-d04r03__RC07 | unreachable | 586770625 | 82028969 | 7.15321 |
| AutoFlight-PT-96b__RC10 | reachable | 5820655521 | 1281106771 | 4.54346 |
| JoinFreeModules-PT-1000__RC08 | reachable | 9397149150 | 2023389946 | 4.64426 |
| JoinFreeModules-PT-2000__RC13 | reachable | 10091940524 | 6946084464 | 1.4529 |
| GPUForwardProgress-PT-40a__RC11 | reachable | 271966028 | 28958372 | 9.39162 |
| CloudOpsManagement-PT-20480by10240__RC08 | unreachable | 196469994 | 4610459 | 42.614 |
| AutoFlight-PT-48b__RC11 | unreachable | 1199077477 | 423492166 | 2.8314 |
| CircularTrains-PT-768__RC09 | reachable | 520108332 | 162243162 | 3.20573 |
| CircularTrains-PT-384__RC06 | unreachable | 366354946 | 39143436 | 9.35929 |
| GPUForwardProgress-PT-36b__RC12 | reachable | 410374373 | 82237560 | 4.99011 |
| CloudOpsManagement-PT-05120by02560__RC00 | reachable | 208521908 | 42268941 | 4.93322 |
| CloudOpsManagement-PT-10240by05120__RC03 | reachable | 5513207944 | 507059994 | 10.8729 |
| CircularTrains-PT-384__RC03 | unreachable | 365932952 | 32619375 | 11.2183 |
| GPUForwardProgress-PT-40b__RC03 | reachable | 424381809 | 88016131 | 4.82164 |
| AutoFlight-PT-96a__RC13 | unreachable | 842029081 | 206572389 | 4.07619 |
| DLCflexbar-PT-8a__RC01 | unreachable | 8831197581 | 1190595455 | 7.41746 |
| CANConstruction-PT-080__RC07 | reachable | 21882994056 | 12177510262 | 1.797 |
| DLCflexbar-PT-8a__RC08 | unreachable | 7945120589 | 1201226903 | 6.61417 |
| GPUForwardProgress-PT-40a__RC01 | reachable | 1677760095 | 22897736 | 73.2719 |
| CANConstruction-PT-100__RC13 | reachable | 29346898709 | 25452799013 | 1.15299 |
| JoinFreeModules-PT-5000__RC01 | reachable | 28761655174 | 7641292297 | 3.76398 |
| DLCflexbar-PT-8a__RC06 | unreachable | 8938676561 | 1190565854 | 7.50792 |
| DLCflexbar-PT-8a__RC00 | unreachable | 8921502589 | 1371722528 | 6.50387 |
| CircularTrains-PT-384__RC14 | unreachable | 350136371 | 33539287 | 10.4396 |
| GPUForwardProgress-PT-40b__RC05 | reachable | 407884038 | 87805432 | 4.64532 |
| JoinFreeModules-PT-2000__RC03 | reachable | 11173701460 | 2111861484 | 5.29093 |
| CloudOpsManagement-PT-10240by05120__RC12 | reachable | 196919892 | 112079657 | 1.75696 |
| JoinFreeModules-PT-5000__RC13 | reachable | 36931252526 | 21700841204 | 1.70184 |
| AutoFlight-PT-96b__RC02 | reachable | 27671643571 | 3562394366 | 7.76771 |
| CloudOpsManagement-PT-20480by10240__RC06 | unreachable | 195758543 | 3326433 | 58.8494 |
| AutoFlight-PT-48b__RC04 | unreachable | 1517979162 | 319440650 | 4.75199 |
| DLCflexbar-PT-8a__RC03 | unreachable | 8943574203 | 1361147793 | 6.57061 |
| GPUForwardProgress-PT-40b__RC08 | reachable | 394801676 | 85211001 | 4.63322 |
| DLCflexbar-PT-8a__RC02 | unreachable | 9923065392 | 1424439784 | 6.96629 |
| CloudOpsManagement-PT-20480by10240__RC09 | unreachable | 195750841 | 3465919 | 56.4788 |
| DLCflexbar-PT-8a__RC12 | unreachable | 7975620806 | 1254585963 | 6.35717 |
| JoinFreeModules-PT-1000__RC12 | reachable | 27273647820 | 1755527703 | 15.5359 |
| Echo-PT-d05r03__RC09 | reachable | 7520369727 | 3588113010 | 2.09591 |
| JoinFreeModules-PT-1000__RC09 | reachable | 9083978801 | 1164572137 | 7.80027 |
| Echo-PT-d05r03__RC10 | reachable | 8157477864 | 14151831796 | 0.576426 |
| CloudOpsManagement-PT-20480by10240__RC13 | unreachable | 198495453 | 3548619 | 55.936 |
| CircularTrains-PT-384__RC08 | reachable | 365178938 | 83304634 | 4.38366 |
| AutoFlight-PT-96a__RC00 | reachable | 1560205125 | 451542040 | 3.45528 |
| JoinFreeModules-PT-2000__RC08 | reachable | 12173161000 | 2647014996 | 4.59883 |
| GPUForwardProgress-PT-36b__RC06 | reachable | 375967259 | 73904027 | 5.08724 |
| CircularTrains-PT-384__RC04 | reachable | 351048085 | 56109220 | 6.25651 |
| CloudOpsManagement-PT-20480by10240__RC10 | unreachable | 195523451 | 3465922 | 56.4131 |
| GPUForwardProgress-PT-36b__RC01 | reachable | 437936605 | 409157575 | 1.07034 |
| CloudOpsManagement-PT-05120by02560__RC03 | reachable | 227831289 | 92176933 | 2.47167 |
| Echo-PT-d03r07__RC03 | unreachable | 2089541652 | 382677117 | 5.46033 |
| JoinFreeModules-PT-2000__RC04 | reachable | 12831730963 | 1732838561 | 7.40504 |
| AutoFlight-PT-96a__RC05 | unreachable | 1090795600 | 168195559 | 6.48528 |
| GPUForwardProgress-PT-40a__RC04 | reachable | 250527347 | 30488240 | 8.21718 |
| JoinFreeModules-PT-5000__RC14 | reachable | 38414174482 | 6424811894 | 5.97903 |
| GPUForwardProgress-PT-40b__RC11 | unreachable | 525325146 | 81983099 | 6.40772 |
| AutoFlight-PT-96a__RC15 | unreachable | 866448898 | 291843649 | 2.96888 |
| JoinFreeModules-PT-1000__RC06 | reachable | 6632454619 | 729959064 | 9.08606 |
| GPUForwardProgress-PT-40a__RC12 | unreachable | 246761161 | 15451621 | 15.9699 |
| Echo-PT-d03r07__RC09 | reachable | 3702287666 | 14290833365 | 0.259067 |
| Echo-PT-d04r03__RC15 | unreachable | 593610627 | 80501801 | 7.37388 |
| AutoFlight-PT-96b__RC00 | reachable | 15929560283 | 1905325863 | 8.36054 |
| CANConstruction-PT-090__RC09 | reachable | 21356797640 | 17273768485 | 1.23637 |
| CircularTrains-PT-768__RC10 | reachable | 523787832 | 165900666 | 3.15724 |

Excluded properties: 109.

## Repeat variability

| Method | Eligible properties | Median max/min | Largest max/min |
|---|---:|---:|---:|
| frozen-v2 | 117 | unavailable | unavailable |
| portfolio-local | 266 | unavailable | unavailable |
| verifypn-default | 341 | unavailable | unavailable |

Definitive disagreements: [].

- Instructions count user-space work in the measured process tree; they are not wall-time speedups.
- Timeout and OOM runs remain in failure counts. Their counters never enter ratios; elapsed-time censoring still depends on machine load.
- Each pair uses its own stable, matching, fully scheduled common-solved subset; inspect the case list and denominator.
- Instruction variability uses stable solved properties with positive counters at 100% time_running_percent in every repeat; it is unavailable with one repetition.
- Definitive verdict agreement does not independently validate external solver answers.
- Frontend and preprocessing scope remain those recorded in environment.json; this analysis does not establish matched input scopes.
