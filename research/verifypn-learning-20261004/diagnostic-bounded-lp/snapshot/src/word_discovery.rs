//! Budgeted transition-dependency cycles proposed as acceleration words.
use crate::model::Problem;
use anyhow::{Result, ensure};
use serde::Serialize;
use std::{
    collections::{BTreeSet, VecDeque},
    time::Instant,
};

#[derive(Clone, Copy)]
pub struct Limits {
    pub max_work: usize,
    pub max_length: usize,
    pub extra_words: usize,
}

#[derive(Debug, Serialize)]
pub struct Discovery {
    pub words: Vec<Vec<usize>>,
    pub work: usize,
    pub truncated: bool,
}

struct Budget {
    remaining: usize,
    deadline: Instant,
    exhausted: bool,
}
impl Budget {
    fn charge(&mut self) -> bool {
        self.spend(1)
    }
    fn spend(&mut self, amount: usize) -> bool {
        if self.remaining < amount || Instant::now() >= self.deadline {
            self.exhausted = true;
            false
        } else {
            self.remaining -= amount;
            true
        }
    }
}

/// Every singleton is retained. Dependency cycles are proposals, not reachability facts.
pub fn discover(problem: &Problem, limits: Limits, deadline: Instant) -> Result<Discovery> {
    problem.validate()?;
    ensure!(limits.max_length > 0, "word length limit must be positive");
    ensure!(
        problem.transitions.len() <= limits.max_work,
        "insufficient work for singleton vocabulary"
    );
    let mut budget = Budget {
        remaining: limits.max_work,
        deadline,
        exhausted: false,
    };
    let mut words = Vec::with_capacity(problem.transitions.len());
    for t in 0..problem.transitions.len() {
        ensure!(budget.charge(), "singleton vocabulary deadline");
        words.push(vec![t]);
    }
    if limits.max_length == 1 || limits.extra_words == 0 {
        return Ok(Discovery {
            words,
            work: limits.max_work - budget.remaining,
            truncated: false,
        });
    }
    if !budget.spend(
        problem
            .places
            .len()
            .saturating_add(problem.transitions.len()),
    ) {
        return Ok(Discovery {
            words,
            work: limits.max_work - budget.remaining,
            truncated: true,
        });
    }
    let mut consumers = vec![Vec::new(); problem.places.len()];
    'consumers: for (t, tr) in problem.transitions.iter().enumerate() {
        for &(p, _) in &tr.pre {
            if !budget.charge() {
                break 'consumers;
            }
            consumers[p].push(t);
        }
    }
    let mut graph = vec![BTreeSet::new(); problem.transitions.len()];
    'edges: for (t, tr) in problem.transitions.iter().enumerate() {
        if !budget.spend(
            tr.pre
                .len()
                .saturating_mul(2 + tr.pre.len().checked_ilog2().unwrap_or(0) as usize),
        ) {
            break 'edges;
        }
        let pre: std::collections::BTreeMap<_, _> = tr.pre.iter().copied().collect();
        for &(p, post) in &tr.post {
            if !budget.charge() {
                break 'edges;
            }
            if post <= pre.get(&p).copied().unwrap_or(0) {
                continue;
            }
            for &next in &consumers[p] {
                if !budget.charge() {
                    break 'edges;
                }
                if next != t {
                    graph[t].insert(next);
                }
            }
        }
    }
    let initial_words = words.len();
    let mut hit_word_limit = false;
    for root in 0..graph.len() {
        if !budget.charge() {
            break;
        }
        if words.len() - initial_words >= limits.extra_words {
            hit_word_limit = true;
            break;
        }
        if !budget.spend(graph.len().saturating_mul(2)) {
            break;
        }
        let mut parents = vec![None; graph.len()];
        let mut distances = vec![usize::MAX; graph.len()];
        distances[root] = 0;
        let mut queue = VecDeque::from([root]);
        'search: while let Some(current) = queue.pop_front() {
            for &next in &graph[current] {
                if !budget.charge() {
                    break 'search;
                }
                if next == root && current != root {
                    let mut word = vec![current];
                    let mut back = current;
                    while back != root {
                        back = parents[back].unwrap();
                        word.push(back);
                    }
                    word.reverse();
                    words.push(word);
                    break 'search;
                }
                if distances[current] + 1 < limits.max_length && distances[next] == usize::MAX {
                    parents[next] = Some(current);
                    distances[next] = distances[current] + 1;
                    queue.push_back(next);
                }
            }
        }
    }
    Ok(Discovery {
        words,
        work: limits.max_work - budget.remaining,
        truncated: budget.exhausted || hit_word_limit,
    })
}
