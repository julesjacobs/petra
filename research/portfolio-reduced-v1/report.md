# Bounded reduced-BFS stage in the native portfolio

Added optional CLI `portfolio-reduced`: existing walk warmup, existing remaining-state
count-planning stage, then reduced BFS for one third of remaining time capped at one
second, followed by the unchanged relevant/causal/batched fallback. Reduced BFS may
return either a lifted original witness or a nested independently checkable negative
proof. It retains its 200,000-state bound. The existing methods and default remain
unchanged.

This allocation is a candidate to test over complete cohorts. The standalone
reduced-BFS screen added three DoubleExponent witnesses but missed 39 properties
solved by the count portfolio; that evidence argues for retaining both methods.
It does not establish that this particular allocation is optimal.

Eleven targeted Rust tests pass, including the combined portfolio's warmup,
negative-proof path, restart validation, budget handling and the underlying 1,176
weighted-net differential comparisons. Targeted Clippy and release build pass.

The combined method was tested against the same-build count portfolio on both
complete original-input diagnostic properties at five seconds with buffer
preprocessing. Both methods solve RefineWMG-PT-100101 RC11 with an independently
checked witness. On CloudReconfiguration-PT-311 RC06, the count portfolio remains
unknown and the combined method proves both branches unreachable. Bounded Python
validation independently translates the PNML/XML, checks canonical branch agreement
and reconstructs/rechecks every proof. The four-row artifact audit passes.

No speed claim: single-run timings varied even for the shared count stage on Refine.
The complete 192-property, 768-row matched comparison completed under
research/portfolio-reduced-development-v1, with candidate and three frozen native
controls. Source/binaries are frozen and eight capability cases passed before launch.
The candidate solves189/192 with three gains and no losses over the count portfolio;
all768rows pass audit. Strong Linux competitors, held-out results and a coherent research
contribution remain open. This is an engineering integration, without a novelty claim.
