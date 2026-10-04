use crate::{marking::StoredMarking, model::Problem, search::Outcome};
use std::{
    cmp::Reverse,
    collections::{BinaryHeap, HashMap},
    time::{Duration, Instant},
};

struct Node {
    marking: StoredMarking,
    parent: Option<(usize, usize)>,
    depth: u64,
    expanded: bool,
}
struct Goal {
    terms: Vec<(usize, i64)>,
    bound: i64,
    equality: bool,
    up: u128,
    down: u128,
}
fn goals(p: &Problem) -> Vec<Goal> {
    p.target
        .iter()
        .map(|c| {
            let mut up = 1;
            let mut down = 1;
            for t in &p.transitions {
                let effect = t
                    .post
                    .iter()
                    .map(|&(i, w)| i128::from(c.coefficients[i]) * i128::from(w))
                    .fold(0i128, i128::saturating_add)
                    .saturating_sub(
                        t.pre
                            .iter()
                            .map(|&(i, w)| i128::from(c.coefficients[i]) * i128::from(w))
                            .fold(0i128, i128::saturating_add),
                    );
                if effect > 0 {
                    up = up.max(effect as u128)
                } else {
                    down = down.max(effect.unsigned_abs())
                }
            }
            Goal {
                terms: c
                    .coefficients
                    .iter()
                    .enumerate()
                    .filter(|(_, a)| **a != 0)
                    .map(|(i, &a)| (i, a))
                    .collect(),
                bound: c.bound,
                equality: c.equality,
                up,
                down,
            }
        })
        .collect()
}
fn scores(goals: &[Goal], marking: &[u64]) -> Result<(u128, u128, bool), &'static str> {
    let mut all = 0u128;
    let mut active = 0u128;
    let mut accepted = true;
    for g in goals {
        let v = g
            .terms
            .iter()
            .try_fold(0i128, |v, &(i, a)| {
                v.checked_add(i128::from(a) * i128::from(marking[i]))
            })
            .ok_or("target arithmetic overflow")?;
        accepted &= if g.equality {
            v == i128::from(g.bound)
        } else {
            v >= i128::from(g.bound)
        };
        let gap = i128::from(g.bound).saturating_sub(v);
        let cost = if gap > 0 {
            (gap as u128).div_ceil(g.up)
        } else if g.equality {
            gap.unsigned_abs().div_ceil(g.down)
        } else {
            0
        };
        all = all.saturating_add(cost);
        // Zero equalities describe cleanup; another queue prioritizes producing the requested observations.
        if !(g.equality && g.bound == 0 && g.terms.iter().all(|&(_, a)| a >= 0)) {
            active = active.saturating_add(cost)
        }
    }
    Ok((all, active, accepted))
}
fn witness(p: &Problem, nodes: &[Node], id: usize) -> Outcome {
    let mut trace = Vec::new();
    let mut back = id;
    while let Some((parent, t)) = nodes[back].parent {
        trace.push(t);
        back = parent
    }
    trace.reverse();
    match p.check_witness(&trace) {
        Ok(marking) => Outcome {
            verdict: "reachable",
            method: "guided".into(),
            reason: "independently replayed witness".into(),
            states: nodes.len(),
            trace,
            marking: Some(marking),
            certificate: None,
            proof: None,
        },
        Err(e) => Outcome::unknown("guided", &format!("witness check failed: {e}"), nodes.len()),
    }
}
/// Interleaves target-directed queues with an exact FIFO search. Heuristics only change order.
pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    run(p, timeout, max_states, false, None)
}
pub fn solve_quotient(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let mut out = run(p, timeout, max_states, true, None);
    out.method = "guided-quotient".into();
    if out.verdict == "unreachable" {
        out.verdict = "unknown";
        out.reason = "quotient exhausted; no exported closure proof".into();
    }
    out
}
pub fn solve_bounded(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    for cap in [1, 2, 3, 4] {
        let mut out = run(
            p,
            timeout.saturating_sub(start.elapsed()) / (5 - cap as u32),
            max_states,
            true,
            Some(cap),
        );
        if out.verdict == "reachable" {
            out.method = "bounded-guided".into();
            return out;
        }
    }
    Outcome::unknown(
        "bounded-guided",
        "bounded underapproximation exhausted or limited",
        0,
    )
}
fn run(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    quotient: bool,
    cap: Option<u64>,
) -> Outcome {
    let start = Instant::now();
    if let Err(e) = p.validate() {
        return Outcome::unknown("guided", &e.to_string(), 0);
    }
    match p.accepts(&p.initial) {
        Ok(true) => {
            return witness(
                p,
                &[Node {
                    marking: StoredMarking::new(&p.initial),
                    parent: None,
                    depth: 0,
                    expanded: false,
                }],
                0,
            );
        }
        Err(e) => return Outcome::unknown("guided", &e.to_string(), 0),
        _ => {}
    }
    let transitions = crate::successors::TransitionIndex::new(p);
    let mut candidates = Vec::new();
    let goals = goals(p);
    let mut marking = p.initial.clone();
    let projection = crate::quotient::Projection::new(p);
    let key = |m: &[u64]| {
        if quotient {
            projection.key(m)
        } else {
            Some(crate::quotient::Key::full(m))
        }
    };
    let Some(initial_key) = key(&marking) else {
        return Outcome::unknown("guided", "projection overflow", 0);
    };
    let mut seen = HashMap::from([(initial_key, 0usize)]);
    let mut nodes = vec![Node {
        marking: StoredMarking::new(&marking),
        parent: None,
        depth: 0,
        expanded: false,
    }];
    let mut heaps: [BinaryHeap<Reverse<(u128, u128, usize)>>; 3] =
        std::array::from_fn(|_| BinaryHeap::new());
    let (all, active, _) = match scores(&goals, &p.initial) {
        Ok(s) => s,
        Err(e) => return Outcome::unknown("guided", e, 1),
    };
    heaps[0].push(Reverse((all, 0, 0)));
    heaps[1].push(Reverse((active, all, 0)));
    heaps[2].push(Reverse((all.saturating_mul(4), 0, 0)));
    let mut fifo = 0;
    let mut iteration = 0usize;
    loop {
        if start.elapsed() >= timeout {
            return Outcome::unknown("guided", "time limit", nodes.len());
        }
        while fifo < nodes.len() && nodes[fifo].expanded {
            fifo += 1
        }
        if fifo == nodes.len() {
            let mut out = Outcome::unknown(
                "guided",
                "finite reachable state space exhausted",
                nodes.len(),
            );
            out.verdict = "unreachable";
            return out;
        }
        let queue = iteration % 8;
        iteration += 1;
        let id = if queue == 0 {
            fifo
        } else {
            let heap = &mut heaps[(queue - 1) % 3];
            loop {
                match heap.pop() {
                    Some(Reverse((_, _, id))) if !nodes[id].expanded => break id,
                    Some(_) => {}
                    None => break fifo,
                }
            }
        };
        nodes[id].expanded = true;
        nodes[id].marking.write_to(&mut marking);
        let depth = nodes[id].depth.saturating_add(1);
        transitions.candidates(&marking, &mut candidates);
        for (attempt, &t) in candidates.iter().enumerate() {
            if attempt % 256 == 0 && start.elapsed() >= timeout {
                return Outcome::unknown("guided", "time limit", nodes.len());
            }
            let next = match p.fire(&marking, t) {
                Ok(Some(next)) => next,
                Ok(None) => continue,
                Err(e) => return Outcome::unknown("guided", &e.to_string(), nodes.len()),
            };
            if cap.is_some_and(|c| {
                transitions
                    .active_places()
                    .iter()
                    .any(|&i| next[i] > c.max(p.initial[i]))
            }) {
                continue;
            }
            let Some(next_key) = key(&next) else {
                return Outcome::unknown("guided", "projection overflow", nodes.len());
            };
            if seen.contains_key(&next_key) {
                continue;
            }
            let (all, active, accepted) = match scores(&goals, &next) {
                Ok(s) => s,
                Err(e) => return Outcome::unknown("guided", e, nodes.len()),
            };
            // A generated goal is cheap to replay even when the storage budget has just been reached.
            if !accepted && nodes.len() >= max_states {
                return Outcome::unknown("guided", "state limit", nodes.len());
            }
            let child = nodes.len();
            let next = StoredMarking::new(&next);
            seen.insert(next_key, child);
            nodes.push(Node {
                marking: next,
                parent: Some((id, t)),
                depth,
                expanded: false,
            });
            if accepted {
                return witness(p, &nodes, child);
            }
            heaps[0].push(Reverse((all, u128::from(depth), child)));
            heaps[1].push(Reverse((
                active,
                all.saturating_add(u128::from(depth)),
                child,
            )));
            heaps[2].push(Reverse((
                all.saturating_mul(4).saturating_add(u128::from(depth)),
                active,
                child,
            )));
        }
    }
}
