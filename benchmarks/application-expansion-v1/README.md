# Application expansion v1

Collected all **192/192 properties** from 12 models in six preregistered development families: BART, CircadianClock, IOTPpurchase, NoC3x3, RobotManipulation, and SmallOperatingSystem. No collection failures. Solver difficulty is **unmeasured**.

Original PNML and all 16 ReachabilityCardinality properties per instance are retained. No net preprocessing or decomposition was performed during import. Canonical branches and Tina inputs support checking and tool interfaces; original PNML/XML must be used for timed comparisons, with each solver's own parsing and preprocessing included.

Selection preceded acquisition and solver execution, taking published ordinals ceil(3N/4) and N in each family. Published order is not evidence of difficulty. All 22 recorded reserved/evaluation families were excluded. This suite is development data.

The collection audited 892 unique input files (174,726,804 bytes) and all 12 archive checksums. Five exact ordered-branch-hash duplicate pairs leave 187 representatives. Report both the full 192-property denominator and the 187-representative sensitivity analysis. Hash differences do not prove semantic independence.

Per-model collection limits:120s,2GiB sampled RSS,256MiB compressed archive,1GiB expanded archive and1GiB retained artifacts. Collection completed on macOS; collection wall time is not solver time. Failures and partial artifacts would have remained in the denominator.

Selection and collector identities are saved in selection.json and collector-provenance.json; acquisition hashes in archive-checksums.json; all outcomes in collection-outcomes.json. The independent collection audit is research/application-expansion-v1-verification.json. Timed competitor evaluation is pending the current Linux measurement window.
