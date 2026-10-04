Implement opt-in portfolio-walk in main.rs only plus meaningful CLI tests.
The completed local9-query/3-seed pilot recovered27/27walk witnesses, baseline0/9.
Keep direct walk and every existing method unchanged. New method receives same
capacity preprocessing as portfolio-batched and same optional buffer/reduction
wrappers. In solve_problem_inner, spend min(timeout/10,100ms) on seeded walk with
same max_states and restart setting, then if Unknown run the existing relevant
portfolio LocalBatched with deadline remaining. Preserve final Outcome/witness/
proof checking behavior; no wrapper should label unchecked answers definitive.
Update method allowlist and zero restart validation for the new method. Do not
change default method. Test positive warmup, negative fallback with checked proof,
resource limit Unknown, and zero restart rejection. No build/format/test while
root coordinates work; report code ready. Main/lib source is separate from
raw_negative.rs, which may receive exact compressed control storage independently.
