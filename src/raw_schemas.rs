//! Budgeted discovery of certified serial path-schema candidates.
use crate::raw_diagnostics::Diagnostics;
use crate::raw_schema::{Schema, Segment};
use crate::raw_target::SerialAutomaton;
use anyhow::{Result, ensure};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::time::Instant;

type Vector = Vec<(usize, u64)>;

struct Budget {
    deadline: Instant,
    remaining: usize,
    diagnostics: Diagnostics,
    stop: &'static str,
}
impl Budget {
    fn spend(&mut self, amount: usize) -> Option<()> {
        if Instant::now() >= self.deadline {
            self.stop = "deadline";
            return None;
        }
        let Some(remaining) = self.remaining.checked_sub(amount) else {
            self.stop = "work-limit";
            return None;
        };
        self.remaining = remaining;
        self.diagnostics.work(amount);
        Some(())
    }
}

#[derive(Clone)]
struct Cycle {
    vector: Vector,
    edges: Vec<usize>,
}
#[derive(Clone)]
struct Generator {
    cycle: Cycle,
    position: usize,
}
#[derive(Clone)]
struct Node {
    state: usize,
    path: Vec<usize>,
    base: Vector,
    generators: Vec<Generator>,
}

fn difference(a: &Vector, b: &Vector, budget: &mut Budget) -> Option<Option<Vector>> {
    budget.spend(a.len().saturating_add(b.len()))?;
    let mut residual: BTreeMap<_, _> = a.iter().copied().collect();
    for &(p, w) in b {
        let old = residual.get(&p).copied().unwrap_or(0);
        if old < w {
            return Some(None);
        }
        if old == w {
            residual.remove(&p);
        } else {
            residual.insert(p, old - w);
        }
    }
    Some(Some(residual.into_iter().collect()))
}

/// Only a completed decomposition permits pruning; an incomplete search keeps
/// the candidate. The per-call cap bounds effort spent simplifying candidates.
fn generated(vector: &Vector, periods: &[Vector], budget: &mut Budget) -> Option<bool> {
    budget.spend(vector.len().max(1))?;
    if vector.is_empty() {
        return Some(true);
    }
    budget.diagnostics.add("generator_membership_calls", 1);
    let mut todo = vec![vector.clone()];
    let mut seen = BTreeSet::new();
    while let Some(residual) = todo.pop() {
        budget.diagnostics.add("generator_membership_nodes", 1);
        budget.spend(residual.len().max(1))?;
        if residual.is_empty() {
            return Some(true);
        }
        if !seen.insert(residual.clone()) {
            continue;
        }
        if seen.len() > 4096 {
            budget.diagnostics.add("generator_membership_local_caps", 1);
            return Some(false);
        }
        for period in periods {
            budget.spend(period.len().max(1))?;
            if period == &residual {
                return Some(true);
            }
            if let Some(next) = difference(&residual, period, budget)? {
                todo.push(next);
            }
        }
    }
    Some(false)
}

fn vector(a: &SerialAutomaton, path: &[usize], budget: &mut Budget) -> Option<Vector> {
    let mut counts = BTreeMap::new();
    for &index in path {
        budget.spend(1)?;
        let count = counts.entry(a.edges[index].response).or_insert(0u64);
        *count = count.checked_add(1)?;
    }
    Some(counts.into_iter().collect())
}

fn shortest_paths(
    a: &SerialAutomaton,
    anchor: usize,
    adjacency: &[Vec<usize>],
    reverse: bool,
    budget: &mut Budget,
) -> Option<Vec<Option<Vec<usize>>>> {
    budget.spend(a.states)?;
    let mut paths = vec![None; a.states];
    paths[anchor] = Some(vec![]);
    let mut todo = VecDeque::from([anchor]);
    while let Some(state) = todo.pop_front() {
        for &index in &adjacency[state] {
            budget.spend(1)?;
            let edge = &a.edges[index];
            let next = if reverse { edge.source } else { edge.target };
            if paths[next].is_none() {
                let previous = paths[state].as_ref()?;
                budget.spend(previous.len().saturating_add(1))?;
                let mut path = Vec::with_capacity(previous.len() + 1);
                if reverse {
                    path.push(index);
                    path.extend(previous);
                } else {
                    path.extend(previous);
                    path.push(index);
                }
                paths[next] = Some(path);
                todo.push_back(next);
            }
        }
    }
    Some(paths)
}

fn cycles(
    a: &SerialAutomaton,
    anchor: usize,
    adjacency: &[Vec<usize>],
    reversed: &[Vec<usize>],
    budget: &mut Budget,
) -> Option<Vec<Cycle>> {
    budget.diagnostics.add("cycle_anchors", 1);
    let forward = shortest_paths(a, anchor, adjacency, false, budget)?;
    let backward = shortest_paths(a, anchor, reversed, true, budget)?;
    let mut found = BTreeMap::new();
    for (index, edge) in a.edges.iter().enumerate() {
        budget.spend(1)?;
        // A remote self-loop is added when its own anchor is visited. Folding
        // it into a return tour creates many weak, redundant period vectors.
        if edge.source == edge.target && edge.source != anchor {
            continue;
        }
        let (Some(prefix), Some(suffix)) = (&forward[edge.source], &backward[edge.target]) else {
            continue;
        };
        budget.spend(prefix.len().saturating_add(suffix.len()).saturating_add(1))?;
        let mut edges = prefix.clone();
        edges.push(index);
        edges.extend(suffix);
        let counts = vector(a, &edges, budget)?;
        found.entry(counts).or_insert(edges);
    }
    Some(
        found
            .into_iter()
            .map(|(vector, edges)| Cycle { vector, edges })
            .collect(),
    )
}

fn extend_generators(node: &mut Node, cycles: &[Cycle], budget: &mut Budget) -> Option<()> {
    for cycle in cycles {
        budget.spend(cycle.edges.len().saturating_add(cycle.vector.len()).max(1))?;
        node.generators.push(Generator {
            cycle: cycle.clone(),
            position: node.path.len(),
        });
    }
    budget.spend(node.generators.len())?;
    node.generators.sort_by(|a, b| {
        let weight = |g: &Generator| {
            g.cycle
                .vector
                .iter()
                .map(|(_, w)| u128::from(*w))
                .sum::<u128>()
        };
        weight(a)
            .cmp(&weight(b))
            .then_with(|| a.cycle.vector.cmp(&b.cycle.vector))
            .then_with(|| a.position.cmp(&b.position))
    });
    let mut retained = vec![];
    let mut periods = vec![];
    for generator in node.generators.drain(..) {
        if !generated(&generator.cycle.vector, &periods, budget)? {
            periods.push(generator.cycle.vector.clone());
            retained.push(generator);
        }
    }
    node.generators = retained;
    Some(())
}

fn schema(node: &Node, budget: &mut Budget) -> Option<Schema> {
    budget.spend(node.path.len().saturating_add(1))?;
    let mut segments = vec![Segment {
        path: vec![],
        cycles: vec![],
    }];
    segments.extend(node.path.iter().map(|&index| Segment {
        path: vec![index],
        cycles: vec![],
    }));
    for generator in &node.generators {
        budget.spend(generator.cycle.edges.len().max(1))?;
        segments[generator.position]
            .cycles
            .push(generator.cycle.edges.clone());
    }
    Some(Schema { segments })
}

fn search(
    a: &SerialAutomaton,
    max_schemas: usize,
    budget: &mut Budget,
    result: &mut Vec<Schema>,
) -> Option<()> {
    budget.spend(a.states.saturating_add(a.edges.len()))?;
    let mut adjacency = vec![vec![]; a.states];
    let mut reversed = vec![vec![]; a.states];
    for (index, edge) in a.edges.iter().enumerate() {
        budget.spend(1)?;
        adjacency[edge.source].push(index);
        reversed[edge.target].push(index);
    }
    let accepting: BTreeSet<_> = a.accepting.iter().copied().collect();
    let mut cached = BTreeMap::new();
    let mut seen: BTreeMap<(usize, Vec<Vector>), Vec<Vector>> = BTreeMap::new();
    let mut emitted = BTreeSet::new();
    let mut todo = VecDeque::from([Node {
        state: a.initial,
        path: vec![],
        base: vec![],
        generators: vec![],
    }]);
    budget.diagnostics.phase("schema-search");
    while let Some(mut node) = todo.pop_front() {
        budget.diagnostics.add("skeleton_candidates", 1);
        budget
            .diagnostics
            .maximum("schema_queue_high_water", todo.len().saturating_add(1));
        budget.spend(1)?;
        if let std::collections::btree_map::Entry::Vacant(entry) = cached.entry(node.state) {
            let previous = budget.diagnostics.activity("schema-cycles");
            let found = cycles(a, node.state, &adjacency, &reversed, budget)?;
            budget.diagnostics.add("cycle_candidates", found.len());
            entry.insert(found);
            budget.diagnostics.restore_activity(previous);
        }
        let state = node.state;
        let previous = budget.diagnostics.activity("schema-generator-pruning");
        extend_generators(&mut node, &cached[&state], budget)?;
        budget.diagnostics.restore_activity(previous);
        budget
            .diagnostics
            .maximum("schema_periods_high_water", node.generators.len());
        let mut periods: Vec<_> = node
            .generators
            .iter()
            .map(|g| g.cycle.vector.clone())
            .collect();
        periods.sort();
        let bases = seen.entry((node.state, periods.clone())).or_default();
        let mut redundant = false;
        for old in bases.iter() {
            if let Some(residual) = difference(&node.base, old, budget)?
                && generated(&residual, &periods, budget)?
            {
                redundant = true;
                break;
            }
        }
        if redundant {
            continue;
        }
        budget.spend(node.base.len().saturating_add(1))?;
        bases.push(node.base.clone());
        budget.diagnostics.add("retained_bases", 1);
        if accepting.contains(&node.state) && emitted.insert((node.base.clone(), periods)) {
            result.push(schema(&node, budget)?);
            budget.diagnostics.add("completed_schemas", 1);
            if result.len() >= max_schemas {
                budget.stop = "schema-cap";
                return Some(());
            }
        }
        for &index in &adjacency[node.state] {
            budget.spend(1)?;
            let edge = &a.edges[index];
            if edge.source == edge.target {
                continue;
            }
            let copy_work = node
                .path
                .len()
                .saturating_add(node.base.len())
                .saturating_add(
                    node.generators
                        .iter()
                        .map(|g| g.cycle.edges.len().saturating_add(g.cycle.vector.len()))
                        .fold(0usize, usize::saturating_add),
                );
            budget.spend(copy_work.saturating_add(1))?;
            let mut next = node.clone();
            next.path.push(index);
            next.state = edge.target;
            match next.base.binary_search_by_key(&edge.response, |&(p, _)| p) {
                Ok(position) => next.base[position].1 = next.base[position].1.checked_add(1)?,
                Err(position) => next.base.insert(position, (edge.response, 1)),
            }
            todo.push_back(next);
        }
    }
    Some(())
}

/// Returns only candidate sublanguages, possibly a prefix when resources are
/// exhausted. Each candidate still requires the independent schema checker.
/// This is not an exhaustive construction of the automaton's Parikh image.
pub fn discover(
    a: &SerialAutomaton,
    deadline: Instant,
    max_work: usize,
    max_schemas: usize,
) -> Result<Vec<Schema>> {
    ensure!(
        a.states > 0 && a.initial < a.states,
        "invalid serial initial state"
    );
    ensure!(
        a.accepting.iter().all(|&s| s < a.states),
        "invalid serial accepting state"
    );
    ensure!(
        a.edges
            .iter()
            .all(|e| e.source < a.states && e.target < a.states),
        "invalid serial edge"
    );
    let mut result = vec![];
    let mut budget = Budget {
        deadline,
        remaining: max_work,
        diagnostics: Diagnostics::new("serial-schema-candidates"),
        stop: "queue-exhausted",
    };
    if max_schemas == 0 {
        budget.diagnostics.finish("schema-cap");
        return Ok(result);
    }
    let completed = search(a, max_schemas, &mut budget, &mut result);
    if completed.is_none() && budget.stop == "queue-exhausted" {
        budget.stop = "incomplete";
    }
    budget.diagnostics.finish(budget.stop);
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::raw_target::{RawQuery, RawTarget, SerialEdge};
    use std::time::Duration;

    fn query(a: SerialAutomaton) -> RawQuery {
        let places = a.edges.iter().map(|e| e.response + 1).max().unwrap_or(1);
        RawQuery {
            format: "ser-raw-v2".into(),
            places: (0..places).map(|i| i.to_string()).collect(),
            initial: vec![0; places],
            transitions: vec![],
            target: RawTarget {
                kind: "completed-outside-automaton".into(),
                zero_places: vec![],
                response_places: (0..places).collect(),
                excluded_semilinear: vec![],
                excluded_automaton: Some(a),
            },
        }
    }

    #[test]
    fn cycle_prefixes_cover_residues_with_small_schemas() {
        let mut edges = vec![];
        for source in 0..7 {
            edges.push(SerialEdge {
                source,
                target: (source + 1) % 7,
                response: 0,
            });
            edges.push(SerialEdge {
                source,
                target: source,
                response: 1,
            });
        }
        let q = query(SerialAutomaton {
            states: 7,
            initial: 0,
            accepting: (0..7).collect(),
            edges,
        });
        let deadline = Instant::now() + Duration::from_secs(5);
        let schemas = discover(
            q.target.excluded_automaton.as_ref().unwrap(),
            deadline,
            2_000_000,
            32,
        )
        .unwrap();
        assert_eq!(schemas.len(), 7);
        let (subset, _) =
            crate::raw_schema::semilinear_query(&q, &schemas, deadline, 2_000_000).unwrap();
        for advances in 0..22 {
            for reads in 0..4 {
                assert!(
                    !subset
                        .accepts(&[advances, reads], deadline, 100_000)
                        .unwrap()
                );
            }
        }
    }

    #[test]
    fn return_to_earlier_anchor_retains_new_independent_periods() {
        let q = query(SerialAutomaton {
            states: 2,
            initial: 0,
            accepting: vec![0, 1],
            edges: vec![
                SerialEdge {
                    source: 0,
                    target: 1,
                    response: 0,
                },
                SerialEdge {
                    source: 1,
                    target: 0,
                    response: 1,
                },
                SerialEdge {
                    source: 1,
                    target: 1,
                    response: 2,
                },
            ],
        });
        let deadline = Instant::now() + Duration::from_secs(5);
        let schemas = discover(
            q.target.excluded_automaton.as_ref().unwrap(),
            deadline,
            1_000_000,
            32,
        )
        .unwrap();
        let (subset, _) =
            crate::raw_schema::semilinear_query(&q, &schemas, deadline, 1_000_000).unwrap();
        assert!(!subset.accepts(&[1, 1, 100], deadline, 100_000).unwrap());
        assert!(!subset.accepts(&[1, 0, 100], deadline, 100_000).unwrap());
        assert!(subset.accepts(&[0, 0, 1], deadline, 100_000).unwrap());
    }

    #[test]
    fn generated_candidates_are_members_of_original_small_automata() {
        let mut random = 73u64;
        for _ in 0..16 {
            let mut edges = vec![];
            for source in 0..3 {
                for target in 0..3 {
                    random = random.wrapping_mul(6364136223846793005).wrapping_add(1);
                    if random >> 62 != 0 {
                        edges.push(SerialEdge {
                            source,
                            target,
                            response: (random >> 60) as usize % 2,
                        });
                    }
                }
            }
            let q = query(SerialAutomaton {
                states: 3,
                initial: 0,
                accepting: vec![0, 2],
                edges,
            });
            let deadline = Instant::now() + Duration::from_secs(5);
            let schemas = discover(
                q.target.excluded_automaton.as_ref().unwrap(),
                deadline,
                500_000,
                16,
            )
            .unwrap();
            let (subset, _) =
                crate::raw_schema::semilinear_query(&q, &schemas, deadline, 500_000).unwrap();
            for component in &subset.target.excluded_semilinear {
                let mut base = vec![0u64; q.places.len()];
                for &(p, w) in &component.base {
                    base[p] = w;
                }
                assert!(!q.accepts(&base, deadline, 100_000).unwrap());
                for period in &component.periods {
                    let mut marking = base.clone();
                    for &(p, w) in period {
                        marking[p] += 2 * w;
                    }
                    assert!(!q.accepts(&marking, deadline, 100_000).unwrap());
                }
            }
        }
    }

    #[test]
    fn limits_return_only_completed_candidates_and_bad_edges_are_rejected() {
        let mut a = SerialAutomaton {
            states: 1,
            initial: 0,
            accepting: vec![0],
            edges: vec![SerialEdge {
                source: 0,
                target: 0,
                response: 0,
            }],
        };
        let deadline = Instant::now() + Duration::from_secs(5);
        assert!(discover(&a, deadline, 0, 10).unwrap().is_empty());
        assert!(discover(&a, Instant::now(), 1000, 10).unwrap().is_empty());
        assert!(discover(&a, deadline, 1000, 0).unwrap().is_empty());
        let q = query(a.clone());
        for allowance in [1, 20, 50, 100, 1000] {
            let schemas = discover(&a, deadline, allowance, 10).unwrap();
            crate::raw_schema::semilinear_query(&q, &schemas, deadline, 10_000).unwrap();
        }
        a.edges[0].target = 1;
        assert!(discover(&a, deadline, 1000, 10).is_err());
    }
}
