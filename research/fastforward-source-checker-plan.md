Proposed integration scope: add only new files, preserving the harness currently being frozen.

- Independent source LoLA parser and direct formula evaluator; no converter imports.
- Arbitrary-precision replay of canonical transition-ID witnesses via checked bijective source mappings.
- Original source/acquisition/canonical hashes verified; canonical net arcs and initial marking checked against source mappings.
- New standalone bounded worker/driver, compatible with process_runner.run but no edits to existing runner/checker files.
- Supports one backend outcome or an original-property-v1 wrapper. Positive witnesses only; negative and unknown outcomes are not promoted.
- Tests include exact-zero targets, forged mappings/net translation, disabled traces, integer overflow boundaries, and malformed formula scope.
