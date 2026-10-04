//! Exact Karp–Miller coverability for pure-effect VASS.
//!
//! Coordinates here are the projection on the constrained coordinates. Other
//! coordinates impose no enabling conditions. This distinction is essential:
//! projecting an ordinary Petri net's pre-arcs is not this construction.
use num_bigint::BigInt;
use num_traits::{One, Zero};
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct Arc {
    pub source: usize,
    pub target: usize,
    pub effect: Vec<BigInt>,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Value {
    Finite(BigInt),
    Omega,
}

#[derive(Clone, Debug)]
pub struct Node {
    pub state: usize,
    pub label: Vec<Value>,
    pub parent: Option<usize>,
    pub via: Option<usize>,
    /// An exact ancestor fold; never a global visited-state pruning.
    pub duplicate_of: Option<usize>,
}

#[derive(Clone, Debug)]
pub struct CoverAnalysis {
    /// A run returns to `start` strictly increasing every coordinate.
    pub pumpable: bool,
    /// Present only after completing a tree with no all-omega node.
    /// Every run has a coordinate whose value never exceeds this bound.
    pub path_bound: Option<BigInt>,
    pub tree: Vec<Node>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CoverLimit {
    Deadline,
    NodeLimit,
    InvalidInput,
    /// A failed pump test can have an all-omega node outside the initial SCC.
    /// Such an input does not justify the path-bound refinement.
    UnboundedOutsideStart,
}

fn covers(label: &[Value], target: &[BigInt]) -> bool {
    label.iter().zip(target).all(|(x, y)| match x {
        Value::Finite(x) => x >= y,
        Value::Omega => true,
    })
}

fn fire(label: &[Value], effect: &[BigInt]) -> Option<Vec<Value>> {
    label
        .iter()
        .zip(effect)
        .map(|(x, d)| match x {
            Value::Omega => Some(Value::Omega),
            Value::Finite(x) => {
                let y = x + d;
                (y >= BigInt::zero()).then_some(Value::Finite(y))
            }
        })
        .collect()
}

/// Decide whether `(start, initial + 1)` is coverable, using a finite
/// Karp–Miller tree. Limits return an error, never a negative answer.
///
/// On a strongly connected input, failure gives Lasota's Claim 9 bound.
/// In a completed tree, follow any finite concrete run through child edges
/// and exact-ancestor folds, always below the extended marking. Omega sets
/// only grow along that path (folds preserve them). If its last node has a
/// finite coordinate, that coordinate was finite throughout the path and
/// stayed below the largest finite label. An all-omega node in an SCC would
/// cover arbitrarily large vectors; reserving the finite cost of a return
/// path to `start` would cover `initial + 1`, contradicting failure.
/// Thus the reported bound bounds one coordinate throughout each run.
///
/// Empty projections satisfy the pumping condition by the empty run.
/// `None` disables the corresponding resource limit.
pub fn analyze(
    states: usize,
    arcs: &[Arc],
    start: usize,
    initial: &[BigInt],
    deadline: Option<Instant>,
    max_nodes: Option<usize>,
) -> Result<CoverAnalysis, CoverLimit> {
    if start >= states
        || initial.iter().any(|x| x < &BigInt::zero())
        || arcs
            .iter()
            .any(|a| a.source >= states || a.target >= states || a.effect.len() != initial.len())
    {
        return Err(CoverLimit::InvalidInput);
    }
    let target: Vec<_> = initial.iter().map(|x| x + BigInt::one()).collect();
    let mut tree = vec![Node {
        state: start,
        label: initial.iter().cloned().map(Value::Finite).collect(),
        parent: None,
        via: None,
        duplicate_of: None,
    }];
    if initial.is_empty() {
        return Ok(CoverAnalysis {
            pumpable: true,
            path_bound: None,
            tree,
        });
    }
    let mut outgoing = vec![Vec::new(); states];
    for (i, a) in arcs.iter().enumerate() {
        outgoing[a.source].push(i);
    }
    let mut cursor = 0;
    while cursor < tree.len() {
        if deadline.is_some_and(|d| Instant::now() >= d) {
            return Err(CoverLimit::Deadline);
        }
        if tree[cursor].duplicate_of.is_some() {
            cursor += 1;
            continue;
        }
        for &arc_index in &outgoing[tree[cursor].state] {
            if deadline.is_some_and(|d| Instant::now() >= d) {
                return Err(CoverLimit::Deadline);
            }
            let arc = &arcs[arc_index];
            let Some(mut label) = fire(&tree[cursor].label, &arc.effect) else {
                continue;
            };
            // A newly introduced omega can make another ancestor comparable.
            // Repeat until no coordinate changes; at most d passes change one.
            loop {
                let mut changed = false;
                let mut ancestor = Some(cursor);
                while let Some(i) = ancestor {
                    if deadline.is_some_and(|d| Instant::now() >= d) {
                        return Err(CoverLimit::Deadline);
                    }
                    let old = &tree[i];
                    if old.state == arc.target && old.label.iter().zip(&label).all(|(a, b)| a <= b)
                    {
                        for (a, b) in old.label.iter().zip(&mut label) {
                            if a < b && *b != Value::Omega {
                                *b = Value::Omega;
                                changed = true;
                            }
                        }
                    }
                    ancestor = old.parent;
                }
                if !changed {
                    break;
                }
            }
            let mut duplicate_of = None;
            let mut ancestor = Some(cursor);
            while let Some(i) = ancestor {
                if tree[i].state == arc.target && tree[i].label == label {
                    duplicate_of = Some(i);
                    break;
                }
                ancestor = tree[i].parent;
            }
            if max_nodes.is_some_and(|limit| tree.len() >= limit) {
                return Err(CoverLimit::NodeLimit);
            }
            let pumpable = arc.target == start && covers(&label, &target);
            tree.push(Node {
                state: arc.target,
                label,
                parent: Some(cursor),
                via: Some(arc_index),
                duplicate_of,
            });
            if pumpable {
                return Ok(CoverAnalysis {
                    pumpable: true,
                    path_bound: None,
                    tree,
                });
            }
        }
        cursor += 1;
    }
    if tree
        .iter()
        .any(|n| n.label.iter().all(|x| *x == Value::Omega))
    {
        return Err(CoverLimit::UnboundedOutsideStart);
    }
    let bound = tree
        .iter()
        .flat_map(|n| &n.label)
        .filter_map(|x| match x {
            Value::Finite(x) => Some(x),
            Value::Omega => None,
        })
        .max()
        .cloned()
        .unwrap_or_default();
    Ok(CoverAnalysis {
        pumpable: false,
        path_bound: Some(bound),
        tree,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    fn arc(source: usize, target: usize, effect: &[i64]) -> Arc {
        Arc {
            source,
            target,
            effect: effect.iter().copied().map(BigInt::from).collect(),
        }
    }
    fn run(states: usize, arcs: &[Arc], initial: &[i64]) -> CoverAnalysis {
        analyze(
            states,
            arcs,
            0,
            &initial
                .iter()
                .copied()
                .map(BigInt::from)
                .collect::<Vec<_>>(),
            Some(Instant::now() + Duration::from_secs(5)),
            Some(100_000),
        )
        .unwrap()
    }
    #[test]
    fn simultaneous_pumping_requires_resources() {
        assert!(!run(1, &[arc(0, 0, &[-1, 2]), arc(0, 0, &[2, -1])], &[0, 0]).pumpable);
        assert!(run(1, &[arc(0, 0, &[-1, 2]), arc(0, 0, &[2, -1])], &[1, 0]).pumpable);
    }
    #[test]
    fn conservative_transfer_and_ancestor_fold() {
        let r = run(1, &[arc(0, 0, &[-1, 1]), arc(0, 0, &[1, -1])], &[7, 0]);
        assert!(!r.pumpable);
        assert_eq!(r.path_bound, Some(7.into()));
        assert!(r.tree.iter().any(|n| n.duplicate_of.is_some()));
    }
    #[test]
    fn unbounded_coordinate_does_not_make_all_pumpable() {
        let r = run(1, &[arc(0, 0, &[1, 0])], &[0, 5]);
        assert!(!r.pumpable);
        assert_eq!(r.path_bound, Some(5.into()));
        assert!(r.tree.iter().any(|n| n.label[0] == Value::Omega));
    }
    #[test]
    fn pump_can_need_expensive_return_to_initial_state() {
        let r = run(
            2,
            &[arc(0, 1, &[0]), arc(1, 1, &[1]), arc(1, 0, &[-100])],
            &[0],
        );
        assert!(r.pumpable);
    }
    #[test]
    fn disconnected_unbounded_branch_cannot_give_a_path_bound() {
        let r = analyze(
            2,
            &[arc(0, 1, &[0]), arc(1, 1, &[1])],
            0,
            &[0.into()],
            Some(Instant::now() + Duration::from_secs(1)),
            Some(100),
        );
        assert_eq!(r.unwrap_err(), CoverLimit::UnboundedOutsideStart);
    }
    #[test]
    fn counters_exceed_machine_word_and_limits_stay_unknown() {
        let huge = BigInt::one() << 200usize;
        let r = analyze(
            1,
            &[],
            0,
            std::slice::from_ref(&huge),
            Some(Instant::now() + Duration::from_secs(1)),
            Some(100),
        )
        .unwrap();
        assert_eq!(r.path_bound, Some(huge));
        let r = analyze(
            1,
            &[arc(0, 0, &[1])],
            0,
            &[0.into()],
            Some(Instant::now() + Duration::from_secs(1)),
            Some(1),
        );
        assert_eq!(r.unwrap_err(), CoverLimit::NodeLimit);
        let r = analyze(1, &[], 0, &[0.into()], Some(Instant::now()), Some(100));
        assert_eq!(r.unwrap_err(), CoverLimit::Deadline);
    }
    #[test]
    fn vacuous_projection() {
        assert!(run(1, &[], &[]).pumpable);
    }
}
