# Instruction-count comparison

Complete matrix: 256 properties × 2 methods × 2 repetitions.

| Method | Solved runs / total | Stable solved properties / total | Unstable outcomes | Timeout runs | OOM runs | Missing / invalid / multiplexed counters |
|---|---:|---:|---:|---:|---:|---:|
| portfolio-local | 512 / 512 | 256 / 256 | 0 | 0 | 0 | 0 / 0 / 0 |
| verifypn-default | 502 / 512 | 251 / 256 | 0 | 10 | 0 | 0 / 0 / 0 |

## portfolio-local / verifypn-default

Geometric mean of per-property median instruction ratios: **16.16** across **251** eligible properties.

A ratio below 1 means fewer instructions for the numerator.

| Property | Verdict | Numerator median | Denominator median | Ratio |
|---|---|---:|---:|---:|
| CANConstruction-PT-040__RC11 | reachable | 8748207200.5 | 1232326424.5 | 7.09894 |
| JoinFreeModules-PT-0005__RC13 | reachable | 211160079.5 | 17684326.0 | 11.9405 |
| CloudOpsManagement-PT-00010by00005__RC11 | unreachable | 195294753.5 | 3439673.5 | 56.7771 |
| CircularTrains-PT-192__RC15 | unreachable | 298318325.0 | 15703807.0 | 18.9966 |
| DLCflexbar-PT-3a__RC13 | unreachable | 1094969195.0 | 139988399.5 | 7.82186 |
| AutoFlight-PT-02a__RC04 | unreachable | 202133306.0 | 4575837.5 | 44.1741 |
| JoinFreeModules-PT-0005__RC07 | unreachable | 215622738.0 | 9656170.0 | 22.33 |
| DLCflexbar-PT-3a__RC10 | unreachable | 1323927325.0 | 177655787.0 | 7.4522 |
| CANConstruction-PT-040__RC13 | unreachable | 3623232315.0 | 573330988.5 | 6.31962 |
| AutoFlight-PT-03a__RC08 | reachable | 213546791.0 | 10896652.0 | 19.5975 |
| CloudOpsManagement-PT-00010by00005__RC13 | reachable | 197497031.5 | 7871412.5 | 25.0904 |
| DLCflexbar-PT-4a__RC10 | unreachable | 1967263762.5 | 405454674.0 | 4.85199 |
| CANConstruction-PT-040__RC14 | reachable | 12859416871.5 | 1425879598.5 | 9.01859 |
| GPUForwardProgress-PT-08a__RC10 | unreachable | 204505370.5 | 4293557.5 | 47.6308 |
| CloudOpsManagement-PT-00040by00020__RC15 | reachable | 197841598.0 | 39126126.5 | 5.05651 |
| JoinFreeModules-PT-0020__RC14 | reachable | 274389134.5 | 19660653.5 | 13.9563 |
| JoinFreeModules-PT-0020__RC00 | unreachable | 265770652.5 | 9668028.0 | 27.4896 |
| JoinFreeModules-PT-0020__RC09 | reachable | 290500600.0 | 28917788.5 | 10.0457 |
| GPUForwardProgress-PT-08a__RC13 | unreachable | 205823781.5 | 7253513.0 | 28.3757 |
| GPUForwardProgress-PT-12a__RC03 | unreachable | 205686000.5 | 5112468.5 | 40.2322 |
| AutoFlight-PT-03a__RC13 | reachable | 1147235036.0 | 12987123.0 | 88.3363 |
| JoinFreeModules-PT-0005__RC05 | reachable | 209792125.0 | 21167543.0 | 9.91103 |
| CANConstruction-PT-020__RC02 | unreachable | 1095821153.0 | 138242328.0 | 7.92681 |
| CANConstruction-PT-040__RC12 | unreachable | 3622454014.0 | 573470841.5 | 6.31672 |
| DLCflexbar-PT-4a__RC07 | unreachable | 2196383134.5 | 383872372.0 | 5.72165 |
| DLCflexbar-PT-3a__RC02 | unreachable | 1095372474.0 | 139891879.5 | 7.83014 |
| JoinFreeModules-PT-0020__RC15 | reachable | 284350298.5 | 54948295.0 | 5.17487 |
| DLCflexbar-PT-3a__RC00 | unreachable | 1093265596.5 | 138475731.0 | 7.895 |
| DLCflexbar-PT-4a__RC06 | unreachable | 1740179205.5 | 211928257.0 | 8.21117 |
| AutoFlight-PT-02a__RC09 | unreachable | 202668889.5 | 4559353.0 | 44.4512 |
| AutoFlight-PT-03a__RC01 | reachable | 211858050.0 | 10776151.5 | 19.6599 |
| CANConstruction-PT-020__RC07 | reachable | 1902018680.5 | 294519591.5 | 6.45804 |
| CircularTrains-PT-192__RC14 | reachable | 271308707.5 | 33811422.5 | 8.02417 |
| GPUForwardProgress-PT-12a__RC13 | unreachable | 206525759.5 | 6903957.0 | 29.9141 |
| CircularTrains-PT-048__RC03 | unreachable | 206882724.0 | 5201171.5 | 39.7762 |
| CircularTrains-PT-192__RC03 | reachable | 274623503.0 | 35369684.0 | 7.76438 |
| Echo-PT-d02r15__RC10 | unreachable | 873032818.0 | 245185329.0 | 3.56071 |
| DLCflexbar-PT-4a__RC08 | unreachable | 1763693166.5 | 223864383.0 | 7.8784 |
| CANConstruction-PT-040__RC09 | unreachable | 3608150771.5 | 594682436.0 | 6.06736 |
| GPUForwardProgress-PT-08a__RC04 | unreachable | 200960614.0 | 4006035.0 | 50.1645 |
| CloudOpsManagement-PT-00040by00020__RC10 | reachable | 197223936.0 | 6823821.0 | 28.9023 |
| GPUForwardProgress-PT-08a__RC02 | unreachable | 200088816.5 | 3695293.5 | 54.1469 |
| CANConstruction-PT-040__RC05 | reachable | 14742138615.0 | 1352831394.5 | 10.8972 |
| JoinFreeModules-PT-0005__RC12 | reachable | 209659285.0 | 20864218.5 | 10.0487 |
| CloudOpsManagement-PT-00010by00005__RC14 | reachable | 197302080.0 | 33773798.0 | 5.84187 |
| Echo-PT-d03r03__RC03 | unreachable | 297755608.5 | 55077322.0 | 5.40614 |
| CANConstruction-PT-020__RC13 | unreachable | 1057798090.0 | 175175482.5 | 6.03851 |
| DLCflexbar-PT-3a__RC06 | unreachable | 1096090032.5 | 149196366.0 | 7.34663 |
| Echo-PT-d03r03__RC15 | unreachable | 275450963.0 | 19994390.5 | 13.7764 |
| Echo-PT-d02r15__RC07 | unreachable | 962134926.0 | 377486687.0 | 2.54879 |
| AutoFlight-PT-03a__RC09 | unreachable | 216200423.5 | 6506947.5 | 33.2261 |
| AutoFlight-PT-02a__RC14 | unreachable | 201847655.0 | 4252825.5 | 47.462 |
| CircularTrains-PT-192__RC04 | unreachable | 278060539.5 | 19695263.0 | 14.1181 |
| AutoFlight-PT-02a__RC00 | unreachable | 206660662.0 | 4709076.5 | 43.8856 |
| DLCflexbar-PT-3a__RC15 | unreachable | 1325954539.0 | 159669949.0 | 8.30435 |
| CloudOpsManagement-PT-00040by00020__RC08 | reachable | 197000124.0 | 5871541.5 | 33.5517 |
| JoinFreeModules-PT-0005__RC09 | unreachable | 979153016.0 | 7192311045.5 | 0.136139 |
| Echo-PT-d02r15__RC00 | reachable | 8849915820.5 | 862906994.5 | 10.2559 |
| AutoFlight-PT-02a__RC15 | unreachable | 207084404.0 | 5143834.0 | 40.2588 |
| AutoFlight-PT-02a__RC05 | unreachable | 204204931.0 | 5089605.0 | 40.122 |
| JoinFreeModules-PT-0005__RC10 | reachable | 216448069.0 | 18213160.0 | 11.8842 |
| CircularTrains-PT-048__RC12 | unreachable | 206535397.0 | 6455770.0 | 31.9924 |
| Echo-PT-d02r15__RC13 | reachable | 8255415340.5 | 1334081428.0 | 6.18809 |
| CircularTrains-PT-048__RC11 | unreachable | 217480025.5 | 7600680.5 | 28.6132 |
| CircularTrains-PT-192__RC08 | unreachable | 267453788.0 | 20220354.5 | 13.227 |
| CloudOpsManagement-PT-00010by00005__RC10 | unreachable | 195670595.5 | 3324990.0 | 58.8485 |
| Echo-PT-d02r15__RC11 | unreachable | 964885572.0 | 185792389.5 | 5.19335 |
| Echo-PT-d03r03__RC05 | unreachable | 285027359.5 | 19992335.0 | 14.2568 |
| CANConstruction-PT-020__RC12 | reachable | 2322212376.0 | 232130763.0 | 10.0039 |
| Echo-PT-d02r15__RC04 | unreachable | 967096559.5 | 1886969924.5 | 0.512513 |
| CANConstruction-PT-040__RC06 | unreachable | 3621863068.5 | 793844732.5 | 4.56243 |
| CloudOpsManagement-PT-00040by00020__RC00 | unreachable | 195549414.0 | 3466943.5 | 56.404 |
| CloudOpsManagement-PT-00040by00020__RC13 | reachable | 196874311.0 | 5205693.5 | 37.819 |
| GPUForwardProgress-PT-08a__RC15 | unreachable | 200549404.5 | 3960045.5 | 50.6432 |
| Echo-PT-d02r15__RC02 | reachable | 4673770081.5 | 4661805105.0 | 1.00257 |
| GPUForwardProgress-PT-08a__RC08 | unreachable | 200064696.0 | 3648772.0 | 54.8307 |
| CloudOpsManagement-PT-00040by00020__RC04 | reachable | 196473253.0 | 6805384.5 | 28.8703 |
| CloudOpsManagement-PT-00010by00005__RC08 | reachable | 196688821.5 | 5058926.5 | 38.8796 |
| AutoFlight-PT-03a__RC00 | unreachable | 208984427.0 | 5915512.0 | 35.3282 |
| GPUForwardProgress-PT-08a__RC12 | unreachable | 200522607.0 | 4577755.0 | 43.8037 |
| CloudOpsManagement-PT-00010by00005__RC04 | reachable | 199324885.0 | 6325660.5 | 31.5105 |
| GPUForwardProgress-PT-08a__RC05 | unreachable | 200432472.0 | 4161192.0 | 48.1671 |
| CircularTrains-PT-048__RC06 | unreachable | 210265546.5 | 6413503.5 | 32.7848 |
| JoinFreeModules-PT-0005__RC11 | reachable | 210028304.5 | 10242636.5 | 20.5053 |
| JoinFreeModules-PT-0020__RC06 | reachable | 275717232.0 | 35423037.0 | 7.78356 |
| Echo-PT-d02r15__RC15 | reachable | 2017369777.5 | 1333395907.0 | 1.51296 |
| CloudOpsManagement-PT-00040by00020__RC11 | unreachable | 195834797.0 | 3480276.5 | 56.2699 |
| GPUForwardProgress-PT-12a__RC10 | unreachable | 205625340.5 | 5112307.0 | 40.2216 |
| CANConstruction-PT-020__RC04 | unreachable | 1051811921.5 | 137853201.5 | 7.62994 |
| CircularTrains-PT-192__RC11 | reachable | 276071642.0 | 34909321.5 | 7.90825 |
| DLCflexbar-PT-4a__RC15 | unreachable | 1744104996.0 | 211998686.5 | 8.22696 |
| CircularTrains-PT-192__RC07 | reachable | 271006283.5 | 32670384.5 | 8.29517 |
| CANConstruction-PT-040__RC01 | unreachable | 3772401093.5 | 594487131.5 | 6.34564 |
| CircularTrains-PT-048__RC13 | unreachable | 214239028.5 | 5662572.5 | 37.8342 |
| AutoFlight-PT-02a__RC11 | unreachable | 202315726.0 | 4650494.5 | 43.5041 |
| AutoFlight-PT-02a__RC06 | unreachable | 202241578.0 | 4622650.5 | 43.7501 |
| CloudOpsManagement-PT-00040by00020__RC09 | reachable | 199193831.0 | 6437478.5 | 30.9428 |
| CANConstruction-PT-020__RC09 | reachable | 2048629581.5 | 281700780.0 | 7.27236 |
| GPUForwardProgress-PT-08a__RC01 | unreachable | 201913294.0 | 4276734.0 | 47.212 |
| CANConstruction-PT-040__RC10 | reachable | 15799917701.5 | 1550034297.5 | 10.1933 |
| CloudOpsManagement-PT-00010by00005__RC12 | reachable | 196858494.5 | 4953451.0 | 39.7417 |
| JoinFreeModules-PT-0020__RC05 | reachable | 322837774.0 | 43186446.0 | 7.47544 |
| GPUForwardProgress-PT-08a__RC11 | unreachable | 200455836.5 | 4181120.5 | 47.9431 |
| Echo-PT-d03r03__RC07 | unreachable | 275561010.5 | 21567413.5 | 12.7767 |
| CircularTrains-PT-192__RC06 | unreachable | 266602883.5 | 16987274.0 | 15.6943 |
| Echo-PT-d02r15__RC14 | reachable | 6433037553.0 | 2493745541.5 | 2.57967 |
| Echo-PT-d03r03__RC00 | unreachable | 272048800.0 | 15132069.0 | 17.9783 |
| JoinFreeModules-PT-0020__RC13 | reachable | 277023072.5 | 64644778.5 | 4.28531 |
| CloudOpsManagement-PT-00010by00005__RC01 | reachable | 196565752.5 | 4907593.0 | 40.0534 |
| Echo-PT-d03r03__RC02 | unreachable | 272044691.0 | 16220503.5 | 16.7717 |
| GPUForwardProgress-PT-08a__RC14 | unreachable | 204381984.5 | 4582124.5 | 44.6042 |
| CloudOpsManagement-PT-00040by00020__RC14 | reachable | 197126377.5 | 6193420.5 | 31.8284 |
| CANConstruction-PT-020__RC05 | reachable | 1881255173.0 | 269635448.5 | 6.97703 |
| CircularTrains-PT-048__RC04 | unreachable | 207067154.0 | 6668498.0 | 31.0515 |
| JoinFreeModules-PT-0020__RC10 | reachable | 271451394.0 | 14257985.0 | 19.0386 |
| AutoFlight-PT-03a__RC05 | unreachable | 209198490.0 | 5985257.0 | 34.9523 |
| JoinFreeModules-PT-0020__RC08 | unreachable | 265133608.5 | 9680178.5 | 27.3893 |
| CircularTrains-PT-192__RC10 | reachable | 286050278.0 | 39980808.5 | 7.15469 |
| Echo-PT-d03r03__RC08 | unreachable | 272784902.5 | 20014520.0 | 13.6294 |
| GPUForwardProgress-PT-12a__RC14 | unreachable | 205688529.5 | 5113174.5 | 40.2272 |
| AutoFlight-PT-02a__RC02 | unreachable | 201765536.0 | 4564551.0 | 44.2027 |
| CircularTrains-PT-048__RC07 | unreachable | 206564244.0 | 5555597.5 | 37.1813 |
| CircularTrains-PT-048__RC00 | unreachable | 206382004.0 | 5572963.5 | 37.0327 |
| AutoFlight-PT-02a__RC10 | unreachable | 201629160.5 | 4579878.5 | 44.025 |
| CANConstruction-PT-020__RC08 | unreachable | 1063873673.0 | 138076374.5 | 7.70497 |
| DLCflexbar-PT-3a__RC04 | unreachable | 1095255155.0 | 139891891.0 | 7.8293 |
| CANConstruction-PT-020__RC15 | reachable | 2613022437.0 | 289234965.0 | 9.03426 |
| CircularTrains-PT-048__RC09 | unreachable | 214028094.5 | 5630817.5 | 38.0101 |
| GPUForwardProgress-PT-12a__RC06 | unreachable | 205934012.5 | 4790867.5 | 42.9847 |
| DLCflexbar-PT-4a__RC00 | unreachable | 1916579190.5 | 238309660.0 | 8.04239 |
| GPUForwardProgress-PT-08a__RC06 | unreachable | 200493482.5 | 4196459.0 | 47.7768 |
| Echo-PT-d03r03__RC10 | unreachable | 274502882.5 | 20108712.0 | 13.6509 |
| CircularTrains-PT-192__RC13 | reachable | 270768859.0 | 32331484.5 | 8.37477 |
| GPUForwardProgress-PT-12a__RC05 | unreachable | 210516382.0 | 5222863.5 | 40.3067 |
| DLCflexbar-PT-4a__RC09 | unreachable | 1740984897.0 | 211967471.0 | 8.21345 |
| GPUForwardProgress-PT-12a__RC01 | unreachable | 211066043.5 | 8563317.5 | 24.6477 |
| GPUForwardProgress-PT-08a__RC07 | unreachable | 200943243.5 | 5335842.0 | 37.6591 |
| AutoFlight-PT-02a__RC08 | unreachable | 208639990.0 | 7624830.5 | 27.3632 |
| JoinFreeModules-PT-0020__RC11 | reachable | 273814254.5 | 27727901.0 | 9.87504 |
| Echo-PT-d02r15__RC12 | unreachable | 964601985.0 | 981122792.0 | 0.983161 |
| CANConstruction-PT-040__RC08 | reachable | 14717910269.0 | 1304700247.0 | 11.2807 |
| AutoFlight-PT-02a__RC01 | unreachable | 201655176.5 | 4499092.5 | 44.8213 |
| GPUForwardProgress-PT-12a__RC00 | unreachable | 205724377.5 | 5113881.0 | 40.2286 |
| CloudOpsManagement-PT-00040by00020__RC07 | reachable | 197054826.5 | 6282405.0 | 31.3661 |
| AutoFlight-PT-03a__RC15 | unreachable | 207972013.5 | 5003525.0 | 41.5651 |
| CloudOpsManagement-PT-00040by00020__RC05 | reachable | 197081774.0 | 7010368.5 | 28.1129 |
| DLCflexbar-PT-4a__RC13 | reachable | 1764816555.0 | 301574081.5 | 5.85202 |
| GPUForwardProgress-PT-08a__RC00 | unreachable | 204445673.5 | 4761613.5 | 42.9362 |
| CloudOpsManagement-PT-00010by00005__RC06 | unreachable | 195610903.5 | 3888597.0 | 50.3037 |
| CloudOpsManagement-PT-00010by00005__RC15 | unreachable | 195755241.5 | 3464511.0 | 56.503 |
| AutoFlight-PT-03a__RC04 | reachable | 214179964.5 | 11831491.5 | 18.1025 |
| CircularTrains-PT-192__RC02 | reachable | 270511054.0 | 26898208.0 | 10.0568 |
| AutoFlight-PT-02a__RC03 | unreachable | 202149058.5 | 4259434.5 | 47.4591 |
| CANConstruction-PT-040__RC07 | unreachable | 3605108820.5 | 593949396.5 | 6.06972 |
| CircularTrains-PT-192__RC05 | reachable | 271121309.0 | 31940093.5 | 8.48843 |
| CANConstruction-PT-020__RC11 | unreachable | 1074207612.5 | 186146994.0 | 5.77075 |
| DLCflexbar-PT-4a__RC04 | unreachable | 1960698044.0 | 259018608.0 | 7.56972 |
| JoinFreeModules-PT-0005__RC06 | reachable | 212665958.5 | 57755962.5 | 3.68215 |
| Echo-PT-d03r03__RC04 | reachable | 302537524.5 | 91079079.5 | 3.3217 |
| GPUForwardProgress-PT-08a__RC09 | unreachable | 205419206.0 | 5041581.0 | 40.745 |
| CloudOpsManagement-PT-00010by00005__RC07 | unreachable | 195403664.0 | 3289100.5 | 59.4095 |
| CloudOpsManagement-PT-00010by00005__RC00 | unreachable | 195910411.0 | 3920536.5 | 49.9703 |
| CircularTrains-PT-048__RC05 | unreachable | 207201261.0 | 8245584.5 | 25.1288 |
| GPUForwardProgress-PT-12a__RC15 | unreachable | 210280943.0 | 5209667.0 | 40.3636 |
| CANConstruction-PT-040__RC04 | reachable | 15146219849.0 | 1244371532.5 | 12.1718 |
| AutoFlight-PT-03a__RC11 | unreachable | 208641473.5 | 7261844.0 | 28.7312 |
| JoinFreeModules-PT-0020__RC12 | reachable | 272469446.0 | 45111168.5 | 6.03996 |
| JoinFreeModules-PT-0020__RC03 | reachable | 285253813.0 | 20132395.5 | 14.1689 |
| Echo-PT-d02r15__RC03 | reachable | 10139363230.5 | 1609167273.0 | 6.301 |
| DLCflexbar-PT-3a__RC05 | unreachable | 1081265795.0 | 123376422.0 | 8.76396 |
| CloudOpsManagement-PT-00040by00020__RC06 | reachable | 195916661.0 | 4736047.0 | 41.3671 |
| Echo-PT-d03r03__RC01 | unreachable | 273991666.5 | 25101864.0 | 10.9152 |
| AutoFlight-PT-03a__RC06 | unreachable | 207937980.5 | 5629415.0 | 36.9378 |
| JoinFreeModules-PT-0020__RC01 | reachable | 273371702.5 | 16314450.5 | 16.7564 |
| GPUForwardProgress-PT-12a__RC02 | unreachable | 206102482.0 | 5147912.5 | 40.0361 |
| CircularTrains-PT-048__RC14 | unreachable | 206618194.5 | 5567027.5 | 37.1146 |
| CANConstruction-PT-020__RC06 | reachable | 2505595527.0 | 212780574.0 | 11.7755 |
| CANConstruction-PT-040__RC15 | reachable | 15887048228.5 | 1309273220.5 | 12.1342 |
| AutoFlight-PT-03a__RC02 | reachable | 213850269.0 | 14039893.5 | 15.2316 |
| DLCflexbar-PT-4a__RC05 | unreachable | 1766926621.0 | 237291218.0 | 7.44624 |
| AutoFlight-PT-03a__RC03 | unreachable | 209036917.0 | 5832446.5 | 35.8403 |
| Echo-PT-d03r03__RC09 | unreachable | 298898721.0 | 20037227.5 | 14.9172 |
| DLCflexbar-PT-3a__RC12 | unreachable | 1093689013.0 | 139944885.0 | 7.81514 |
| CloudOpsManagement-PT-00040by00020__RC12 | reachable | 197975191.5 | 9499344.0 | 20.8409 |
| Echo-PT-d02r15__RC06 | reachable | 9178834794.0 | 1524700864.0 | 6.02009 |
| CloudOpsManagement-PT-00040by00020__RC02 | reachable | 196200728.5 | 4736176.5 | 41.426 |
| JoinFreeModules-PT-0005__RC08 | reachable | 210093945.0 | 12722670.0 | 16.5134 |
| DLCflexbar-PT-3a__RC11 | unreachable | 1092966686.0 | 139945029.5 | 7.80997 |
| DLCflexbar-PT-3a__RC08 | unreachable | 1208816264.0 | 200640163.5 | 6.0248 |
| JoinFreeModules-PT-0020__RC07 | reachable | 273014595.0 | 14251290.0 | 19.1572 |
| GPUForwardProgress-PT-12a__RC04 | reachable | 1565810016.5 | 9824004.5 | 159.386 |
| CloudOpsManagement-PT-00010by00005__RC03 | unreachable | 195520578.5 | 3501498.0 | 55.8391 |
| JoinFreeModules-PT-0005__RC01 | reachable | 209085389.5 | 6311858.5 | 33.1258 |
| Echo-PT-d03r03__RC06 | unreachable | 273611481.0 | 36898367.5 | 7.41527 |
| JoinFreeModules-PT-0005__RC03 | reachable | 209760573.5 | 18175968.0 | 11.5405 |
| GPUForwardProgress-PT-12a__RC09 | unreachable | 205557354.0 | 5114263.5 | 40.193 |
| JoinFreeModules-PT-0005__RC14 | unreachable | 209055224.5 | 3917384.0 | 53.366 |
| DLCflexbar-PT-3a__RC07 | unreachable | 1094254677.0 | 138475495.0 | 7.90215 |
| CircularTrains-PT-192__RC01 | unreachable | 266780640.0 | 16860289.0 | 15.823 |
| Echo-PT-d03r03__RC11 | unreachable | 274709809.5 | 16559555.5 | 16.5892 |
| CircularTrains-PT-048__RC02 | reachable | 209200502.0 | 10840358.0 | 19.2983 |
| JoinFreeModules-PT-0005__RC00 | reachable | 216801499.5 | 19411765.5 | 11.1686 |
| CloudOpsManagement-PT-00040by00020__RC01 | reachable | 196984566.0 | 5185564.0 | 37.9871 |
| GPUForwardProgress-PT-12a__RC08 | unreachable | 211275443.0 | 5310428.5 | 39.785 |
| CANConstruction-PT-040__RC00 | reachable | 12651337490.0 | 1393482446.0 | 9.07894 |
| DLCflexbar-PT-3a__RC09 | unreachable | 1095057628.5 | 156699041.5 | 6.98829 |
| Echo-PT-d03r03__RC12 | unreachable | 289312326.5 | 45834246.5 | 6.31214 |
| DLCflexbar-PT-3a__RC14 | unreachable | 1095846607.5 | 204016694.0 | 5.37136 |
| GPUForwardProgress-PT-12a__RC12 | unreachable | 206440440.0 | 5188915.0 | 39.7849 |
| AutoFlight-PT-02a__RC12 | unreachable | 205132289.5 | 6525407.0 | 31.4359 |
| DLCflexbar-PT-4a__RC12 | reachable | 1765947545.0 | 301569171.5 | 5.85586 |
| AutoFlight-PT-02a__RC13 | unreachable | 202254266.5 | 4681938.5 | 43.1988 |
| CloudOpsManagement-PT-00010by00005__RC05 | unreachable | 195062455.0 | 3081262.0 | 63.306 |
| Echo-PT-d03r03__RC14 | unreachable | 285533927.5 | 20278194.0 | 14.0808 |
| JoinFreeModules-PT-0020__RC04 | reachable | 276311496.5 | 24001362.0 | 11.5123 |
| CircularTrains-PT-048__RC08 | unreachable | 207459995.0 | 6157685.0 | 33.6912 |
| DLCflexbar-PT-4a__RC01 | reachable | 1766186454.5 | 303130287.0 | 5.82649 |
| JoinFreeModules-PT-0005__RC04 | unreachable | 207078951.0 | 11231157.5 | 18.4379 |
| Echo-PT-d02r15__RC01 | reachable | 11215017328.0 | 1468713973.5 | 7.63594 |
| DLCflexbar-PT-3a__RC03 | unreachable | 1093280921.5 | 130472206.5 | 8.37942 |
| CANConstruction-PT-020__RC03 | reachable | 2304654808.0 | 208020008.0 | 11.079 |
| JoinFreeModules-PT-0020__RC02 | reachable | 273929180.0 | 14443272.0 | 18.9659 |
| Echo-PT-d03r03__RC13 | unreachable | 286496412.0 | 20033852.5 | 14.3006 |
| CANConstruction-PT-020__RC00 | unreachable | 1123094829.0 | 142742495.0 | 7.86798 |
| GPUForwardProgress-PT-08a__RC03 | unreachable | 200320096.5 | 3900064.0 | 51.3633 |
| CloudOpsManagement-PT-00010by00005__RC02 | reachable | 198659461.0 | 6295929.0 | 31.5536 |
| Echo-PT-d02r15__RC09 | reachable | 3190300260.5 | 1320926550.5 | 2.4152 |
| CloudOpsManagement-PT-00040by00020__RC03 | reachable | 196648575.0 | 5157220.5 | 38.1307 |
| CircularTrains-PT-192__RC09 | unreachable | 268801125.0 | 25174441.5 | 10.6775 |
| JoinFreeModules-PT-0005__RC02 | unreachable | 206247021.5 | 3819142.5 | 54.0035 |
| DLCflexbar-PT-3a__RC01 | unreachable | 1098295206.0 | 158524873.5 | 6.92822 |
| CircularTrains-PT-048__RC01 | unreachable | 207096276.5 | 7309451.5 | 28.3327 |
| CircularTrains-PT-048__RC10 | unreachable | 208089417.0 | 7620774.5 | 27.3055 |
| AutoFlight-PT-03a__RC07 | unreachable | 213727775.0 | 10240148.5 | 20.8716 |
| CANConstruction-PT-020__RC10 | unreachable | 1308056119.5 | 199371163.0 | 6.56091 |
| CloudOpsManagement-PT-00010by00005__RC09 | reachable | 197207786.0 | 7636296.0 | 25.8251 |
| JoinFreeModules-PT-0005__RC15 | reachable | 209208043.5 | 12672387.0 | 16.509 |
| GPUForwardProgress-PT-12a__RC11 | reachable | 1171290641.5 | 11394731.5 | 102.792 |
| CircularTrains-PT-048__RC15 | reachable | 208164020.0 | 10175717.0 | 20.4569 |
| DLCflexbar-PT-4a__RC11 | reachable | 2430073959.5 | 352958644.0 | 6.88487 |
| CANConstruction-PT-020__RC14 | reachable | 2220128643.5 | 295743561.0 | 7.50694 |
| CircularTrains-PT-192__RC12 | unreachable | 282022975.0 | 20040936.5 | 14.0723 |
| GPUForwardProgress-PT-12a__RC07 | unreachable | 210057726.0 | 5187795.5 | 40.4907 |
| AutoFlight-PT-02a__RC07 | unreachable | 202115276.0 | 4631011.0 | 43.6439 |
| AutoFlight-PT-03a__RC14 | unreachable | 212410779.5 | 8773698.5 | 24.2099 |
| DLCflexbar-PT-4a__RC03 | unreachable | 1763804176.5 | 237428110.0 | 7.42879 |
| DLCflexbar-PT-4a__RC02 | unreachable | 1960988112.0 | 274924049.0 | 7.13284 |
| DLCflexbar-PT-4a__RC14 | unreachable | 2361561896.0 | 389030604.5 | 6.07038 |
| CircularTrains-PT-192__RC00 | reachable | 269886103.5 | 26780421.0 | 10.0777 |
| AutoFlight-PT-03a__RC12 | unreachable | 208123125.5 | 5751036.5 | 36.1888 |
| AutoFlight-PT-03a__RC10 | unreachable | 209062074.5 | 5567679.0 | 37.5492 |

Excluded properties: 5.

## Repeat variability

| Method | Eligible properties | Median max/min | Largest max/min |
|---|---:|---:|---:|
| portfolio-local | 256 | 1.00093 | 1.50845 |
| verifypn-default | 251 | 1 | 1.00017 |

Definitive disagreements: [].

- Instructions count user-space work in the measured process tree; they are not wall-time speedups.
- Timeout and OOM runs remain in failure counts. Their counters never enter ratios; elapsed-time censoring still depends on machine load.
- Each pair uses its own stable, matching, fully scheduled common-solved subset; inspect the case list and denominator.
- Instruction variability uses stable solved properties with positive counters at 100% time_running_percent in every repeat; it is unavailable with one repetition.
- Definitive verdict agreement does not independently validate external solver answers.
- Frontend and preprocessing scope remain those recorded in environment.json; this analysis does not establish matched input scopes.
