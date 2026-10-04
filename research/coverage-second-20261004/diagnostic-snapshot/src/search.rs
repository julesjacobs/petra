use crate::{marking::StoredMarking, model::Problem, successors::TransitionIndex};
use serde::Serialize;
use std::{
    cmp::Reverse,
    collections::{BinaryHeap, HashMap, VecDeque},
    sync::Arc,
    time::{Duration, Instant},
};

#[derive(Clone, Debug, Serialize)]
pub struct Outcome {
    pub verdict: &'static str,
    pub method: String,
    pub reason: String,
    pub states: usize,
    pub trace: Vec<usize>,
    pub marking: Option<Vec<u64>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub certificate: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub proof: Option<serde_json::Value>,
}
impl Outcome {
    pub fn unknown(method: &str, reason: &str, states: usize) -> Self {
        Self {
            verdict: "unknown",
            method: method.into(),
            reason: reason.into(),
            states,
            trace: vec![],
            marking: None,
            certificate: None,
            proof: None,
        }
    }
}
struct Entry {
    marking: Arc<StoredMarking>,
    parent: Option<(usize, usize)>,
}
fn score(p: &Problem, m: &[u64]) -> u128 {
    p.target
        .iter()
        .map(|c| {
            let value = c.coefficients.iter().zip(m).fold(0i128, |a, (&x, &y)| {
                a.saturating_add(i128::from(x) * i128::from(y))
            });
            let gap = i128::from(c.bound).saturating_sub(value);
            if c.equality {
                gap.unsigned_abs()
            } else {
                gap.max(0) as u128
            }
        })
        .fold(0u128, u128::saturating_add)
}
pub fn solve(p: &Problem, best_first: bool, timeout: Duration, max_states: usize) -> Outcome {
    let method = if best_first { "best-first" } else { "bfs" };
    let start = Instant::now();
    let index = TransitionIndex::new(p);
    let initial = Arc::new(StoredMarking::new(&p.initial));
    let mut nodes = vec![Entry {
        marking: Arc::clone(&initial),
        parent: None,
    }];
    let mut seen = HashMap::from([(initial, 0)]);
    let mut queue = VecDeque::from([0]);
    let mut heap = BinaryHeap::from([Reverse((score(p, &p.initial), 0usize))]);
    let mut marking = vec![0; p.places.len()];
    let mut candidates = Vec::new();
    loop {
        if start.elapsed() >= timeout {
            return Outcome::unknown(method, "time limit", nodes.len());
        }
        let next = if best_first {
            heap.pop().map(|Reverse((_, i))| i)
        } else {
            queue.pop_front()
        };
        let Some(id) = next else {
            let mut out = Outcome::unknown(
                method,
                "finite reachable state space exhausted",
                nodes.len(),
            );
            out.verdict = "unreachable";
            return out;
        };
        nodes[id].marking.write_to(&mut marking);
        match p.accepts(&marking) {
            Ok(true) => {
                let mut trace = Vec::new();
                let mut back = id;
                while let Some((prev, t)) = nodes[back].parent {
                    trace.push(t);
                    back = prev;
                }
                trace.reverse();
                match p.check_witness(&trace) {
                    Ok(marking) => {
                        return Outcome {
                            verdict: "reachable",
                            method: method.into(),
                            reason: "replayed witness".into(),
                            states: nodes.len(),
                            trace,
                            marking: Some(marking),
                            certificate: None,
                            proof: None,
                        };
                    }
                    Err(e) => {
                        return Outcome::unknown(
                            method,
                            &format!("witness check failed: {e}"),
                            nodes.len(),
                        );
                    }
                }
            }
            Ok(false) => {}
            Err(e) => return Outcome::unknown(method, &e.to_string(), nodes.len()),
        }
        index.candidates(&marking, &mut candidates);
        for (candidate, &t) in candidates.iter().enumerate() {
            if candidate % 256 == 0 && start.elapsed() >= timeout {
                return Outcome::unknown(method, "time limit", nodes.len());
            }
            let successor = match p.fire(&marking, t) {
                Ok(Some(m)) => m,
                Ok(None) => continue,
                Err(e) => return Outcome::unknown(method, &e.to_string(), nodes.len()),
            };
            let stored = StoredMarking::new(&successor);
            if seen.contains_key(&stored) {
                continue;
            }
            if nodes.len() >= max_states {
                return Outcome::unknown(method, "state limit", nodes.len());
            }
            let child = nodes.len();
            if best_first {
                heap.push(Reverse((score(p, &successor), child)));
            } else {
                queue.push_back(child);
            }
            let stored = Arc::new(stored);
            seen.insert(Arc::clone(&stored), child);
            nodes.push(Entry {
                marking: stored,
                parent: Some((id, t)),
            });
        }
    }
}
