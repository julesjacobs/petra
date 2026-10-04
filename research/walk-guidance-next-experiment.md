# Next general-solver experiment: target-guided enabled walks

The full ordinary comparison is running with immutable binaries. No change here
alters that experiment. The user selected a general Petri-net solver as the
publication target, with serializability as an application.

A bounded follow-up hypothesis is to reuse the incremental enabled-transition
kernel for noisy target-guided walks. Uniform walk remains the control. The new
mode would sample eight enabled transitions and prefer the smallest sum of
linear-target violations, with one in five steps chosen uniformly. Plateau ties
remain random. Constants and seeds must be fixed before benchmark outcomes.
All positive answers still require original-net replay; no negative conclusions
follow from failure. Weighted guards, read arcs and u64 overflow retain existing
semantics. Any score approximation affects only selection.

This is a proposal, not an implemented algorithm or novelty claim. Before a
broad implementation, inspect the full ordinary comparison for remaining
positive-search gaps. Evaluate on complete parent cohorts and preserve losses;
selected survivor results are development evidence. Incremental target-value
maintenance and candidate scoring should be measured separately from changing
the walk policy, with existing uniform behavior kept available.
