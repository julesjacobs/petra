Evidence and proposed implementation: transfer phase audit shows dense retained
control markings dominate a large product (560/726/1126 coordinates, mostly
distinct controls); schema generation is already quick. Reuse existing exact
StoredMarking sparse/dense representation behind interned Rc controls. Maintain
full-u64 semantics, position identity, dimensions, initial/component identity,
weighted enabling and firing, immutable keys, existing certificate format and
independent checker. Restore a dense transient marking for expansion/diagnostics
and certificate extraction; retained graph controls should stay compressed.
Charge conversion/interning work conservatively and document any work-accounting
change. Do not alter projection choice, transfer maps, graph semantics, current
JSON proofs, Python checkers, src/main.rs or src/walk*.rs. Small meaningful tests
should cover sparse/dense identity, zero padding, u64MAX, weighted successors,
nonaliasing and checked known proofs. No build/test/benchmark until root authorizes;
local session28720 is measuring the frozen walk binary now. Root will run complete
checks and a separate matched raw pilot after this measurement finishes.
