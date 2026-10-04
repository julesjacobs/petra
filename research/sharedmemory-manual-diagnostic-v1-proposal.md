# SharedMemory survivor diagnosis: unverified candidate answers

Inspection of the canonical inputs found40601places,80200transitions and401initial
tokens:200Memory tokens,200Active tokens and one Ext_Bus token. Each external
access consumes Ext_Bus and creates one Ext_Mem_Acc token; completion reverses
that movement. Own-memory operations and requests leave this sum unchanged.
This suggests Ext_Bus + sum(Ext_Mem_Acc) =1as an inductive invariant.

RC04 has two target branches. In both, row0requires sum(Active)>=2and row2
requires Ext_Bus-sum(Active)>=0. Adding them gives Ext_Bus>=2, contradicting the
candidate invariant and nonnegativity. The proposed sparse Farkas certificate
uses weight1on every Ext_Mem_Acc nonnegativity row and target rows0and2.
No new proof format or inference rule is needed.

RC03 branch3requires sum(OwnMemAcc)<=1, Ext_Bus<=2,
sum(Ext_Mem_Acc)<=1and sum(Active)<=2(with a repeated OwnMemAcc row).
The200Req_Ext_Acc transitions each move an initial Active token to its Queue;
a proposed200-step execution therefore reaches this branch. This would be a
counterexample to its AG property. Guards and the complete target still need replay.

`check-sharedmemory-manual-v1.py` is prepared but not yet run. It uses explicit
model names to propose answers, then demands Rust branch verification and the
frozen independent Python original-PNML/XML translator/checker. This is manual
diagnosis, never automatic-solver coverage or discovery timing. It is gated on
terminal completion of the active local ablation, session6596.

If verified, the engineering gaps differ: target-guided positive search for RC03,
and cheap combinations of target rows with certified capacities for RC04.
`capacity.rs::refute` currently tries one target row at a time; `target_places`
keeps the first64positive coordinates, so a200-coordinate first row can consume
its entire seed budget before it reaches the bus row. These code facts suggest
missed opportunities but do not establish which phase caused the earlier failures.
The Pro consultation is independently reviewing general research direction.
