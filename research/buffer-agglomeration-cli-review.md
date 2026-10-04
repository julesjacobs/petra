# Buffer agglomeration review and integration fixtures

No defect found in the proposal's eager/delayed equivalence argument under its
stated restrictions. This is a source/argument review, not a new theorem proof or
performance result. The saved finite prototype reports 49,248 cases on its
three-place, nonincreasing-total grid; that grid observes one coordinate and does
not establish the general conjunction claim. I did not rerun it.

For the general claim, treat each uniform-weight production as one labelled
packet. Initial emptiness and nonnegative markings let every consumption match a
distinct earlier packet. Disjoint producer/consumer sets prevent a firing from
both producing and consuming such a packet.

In the eager orientation, append one arbitrary consumer for each unmatched
packet. These firings are enabled because consumers require only that buffer;
their outputs and the buffer are outside every target row's support. Commute
each consumer to its matched producer. Its earlier outputs can only increase
other intermediate markings. Packet matching ensures other consumers retain
their own packets. Thus all retained firings stay enabled, and the final queried
coordinates are exactly unchanged. Every resulting pair has guard `f.pre` and
postset `(f.post without p)+c.post`.

In the delayed orientation, commute each matched producer to immediately before
its consumer, and postpone unmatched producers until after all matched firings.
Postponement retains the producer's pre-tokens on other places; it removes only
its own unused buffer packet from intermediate markings. Delete the postponed
unmatched producers. Only unqueried coordinates change. A pair requires the
sum of producer inputs and nonbuffer consumer inputs because the producer adds
no other tokens; its postset is `c.post`. Shared inputs and weighted self-loops
must remain in those guards rather than being cancelled against outputs.

These arguments preserve the entire vector of queried coordinates, so arbitrary
signed linear conjunctions and exact equalities are covered. They do not rely on
target upward closure. Repeated valid steps compose; reverse DAG expansion and
original-net replay establish the positive witness boundary. A negative answer
still requires independent reconstruction of every step and its inner proof.

Prepared `tests/buffer_agglomeration_cli.rs` contains nine test groups covering:

- Eager-only and delayed-only weighted macro expansion, original IDs/markings,
  and rejection of reversed witness order.
- Cyclic producer/consumer dependencies and exact signed conjunctions.
- Repeated reductions with nested recipe expansion.
- Queried consumer outputs, producer inputs, and signed buffer support that must
  prevent the corresponding rewrite.
- Nonuniform packet weights, initially marked buffers, and buffer self-loops.
- Reconstructed negative step sequences, malformed/empty steps, unsupported
  inner proofs, extra certificate fields, and reuse against a reachable target.
- Uncertified reduced exhaustion remaining Unknown.
- Trap + potential + buffer flags, original transition reindexing and nested
  trap/buffer negative proof validation.
- Raw/unlimited flag conflicts before input access.

The current wrapper order is trap -> potential -> buffer. The current potential
candidate needs a target upper-bound row for every place; buffer agglomeration
requires an unqueried place. Consequently the composed fixture correctly checks
potential fallback followed by an actual buffer reduction, rather than claiming
both transformations apply. A future buffer -> potential pass could expose new
applicability but is not implemented or tested here.

The tests are prepared but **not run by this reviewer**. Request the root's
centralized `cargo test --test buffer_agglomeration_cli` after the core API and
CLI integration are complete. No production file, frozen artifact, measurement,
or Linux state was changed by this task.
