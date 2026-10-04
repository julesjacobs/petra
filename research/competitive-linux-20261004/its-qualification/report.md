# ITS-Tools runtime qualification

The official native portfolio is qualified with limitations. The final receipt is `qualification-final.json`; `freeze-fields.json` contains the runtime configuration and file hashes for the campaign freeze.

The command uses the pinned upstream `BenchKit_head.sh` and `runeclipse.sh`, with `-its -order META -manyOrder -smt` and GreatSPN. It selects the upstream-preferred native image; Java is not invoked. The native image SHA-256 is `a84feea4726890be2d0beb07031147703d8ff6e1da52f3742fcbff7cfea1abda`. The product downloaded alongside it exactly matches the earlier product pin, `faef344a641ca190e34eedee71a5cc44ac7051003841a431da4edfdf0bb7ae5f`. Native/source correspondence remains unverified.

The two verified native qualification batches produced 16 accepted answers, all correct. Together they cover both EF/AG polarities, equality, signed token comparison, weighted ordinary read arcs, and selection from a multiple-property document. Every invocation used CPU 8, a 2 GiB process-tree limit, and a five-second outer deadline. Oversized integer inputs and constant arithmetic return unknown before tool execution.

Known limitations remain in the denominator:

- Some negative cases print the correct answer but do not terminate, including a separate diagnostic with a 15-second outer deadline. The five-second campaign records unknown.
- A negative-product expression raises `UnsupportedOperationException` after printing an answer. The wrapper records unknown.
- A repeated read-arc case produced auxiliary GAL lexer errors after printing an answer. The wrapper records unknown; an earlier invocation of the same case completed cleanly.
- The integer guard checks input values and constant arithmetic. It does not establish that arbitrary reachable intermediate arithmetic fits signed 32-bit integers.

The ITS reachability binary, embedded Z3, and GreatSPN `RGMEDD2` launch successfully. Their dependency closure is recorded in `ldd.json` and `external-files-sha256.json`. The unused `RGMEDD3` has a missing library; the pinned product's `MultiOrderRunner` references `RGMEDD2`. All portfolio workers inherit the one-CPU affinity and cgroup limits.

Earlier trials are preserved. Default Java 21 often exceeded the short startup budget; a documented C1 JVM setting did not resolve the negative-case behavior. The first native installation was accidentally copied before its transfer completed, producing a truncated binary and SIGBUS. That installation's hash differs from the official download. The replacement was verified before execution; those preliminary failures are not attributed to upstream native ITS.

The wrapper is `../runner-source/scripts/its_original.py`. Its CLI is:

```text
python its_original.py --runtime-config runtime-native-config.json --pnml MODEL --xml PROPERTIES --property-id ID --artifacts FRESH_DIRECTORY --seconds 5
```

Run the entire wrapper through `linux_runner.run(..., seconds=5, memory_bytes=2147483648, cpus=[8], perf=True)`. Input staging, startup, frontend work, result parsing, and process exit all count toward the outer deadline. The wrapper records stage, tool, parse, and total timing plus exact commands and tool logs. The campaign harness applies the final admission rules and enforces process-tree cleanup.

`qualification-evidence.tar.gz` and `collection.json` preserve the trial evidence. Runtime executables remain on the Linux host and are pinned by 228 workspace file hashes and 19 external dependency hashes. Generated OSGi caches are unused by the native route and excluded from immutable executable pins. All qualification processes were terminal before the measurement gate was released.
