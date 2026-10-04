//! Exact feasibility of capacitated flows with `outflow - inflow = demand`.
use num_bigint::BigInt;
use num_traits::{Signed, Zero};
use std::{collections::VecDeque, time::Instant};

pub struct Edge {
    pub source: usize,
    pub target: usize,
    pub capacity: Option<BigInt>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Answer {
    Feasible,
    Cut(Vec<usize>),
    Unknown,
}

struct Arc {
    target: usize,
    residual: BigInt,
}

fn add_arc(
    adjacency: &mut [Vec<usize>],
    arcs: &mut Vec<Arc>,
    source: usize,
    target: usize,
    capacity: BigInt,
) {
    let forward = arcs.len();
    arcs.push(Arc {
        target,
        residual: capacity,
    });
    arcs.push(Arc {
        target: source,
        residual: BigInt::zero(),
    });
    adjacency[source].push(forward);
    adjacency[target].push(forward + 1);
}

/// A returned cut has strictly more demand than finite outgoing capacity.
/// Invalid inputs, expired deadlines, and unchecked cuts return `Unknown`.
pub fn separate(nodes: usize, edges: &[Edge], demands: &[BigInt], deadline: Instant) -> Answer {
    if demands.len() != nodes || Instant::now() >= deadline {
        return Answer::Unknown;
    }
    let Some(vertices) = nodes.checked_add(2) else {
        return Answer::Unknown;
    };
    let mut total = BigInt::zero();
    let mut supply = BigInt::zero();
    for demand in demands {
        if Instant::now() >= deadline {
            return Answer::Unknown;
        }
        total += demand;
        if demand.is_positive() {
            supply += demand;
        }
    }
    if !total.is_zero() {
        return Answer::Unknown;
    }
    for edge in edges {
        if Instant::now() >= deadline
            || edge.source >= nodes
            || edge.target >= nodes
            || edge.capacity.as_ref().is_some_and(Signed::is_negative)
        {
            return Answer::Unknown;
        }
    }
    if supply.is_zero() {
        return Answer::Feasible;
    }

    let source = nodes;
    let sink = nodes + 1;
    let mut adjacency = vec![Vec::new(); vertices];
    let mut arcs = Vec::new();
    // This candidate-dependent replacement cannot saturate in a minimum cut
    // of capacity below the supply. It is never exported as a symbolic bound.
    let infinity = &supply + 1;
    for edge in edges {
        if Instant::now() >= deadline {
            return Answer::Unknown;
        }
        add_arc(
            &mut adjacency,
            &mut arcs,
            edge.source,
            edge.target,
            edge.capacity.as_ref().unwrap_or(&infinity).clone(),
        );
    }
    for (vertex, demand) in demands.iter().enumerate() {
        if Instant::now() >= deadline {
            return Answer::Unknown;
        }
        if demand.is_positive() {
            add_arc(&mut adjacency, &mut arcs, source, vertex, demand.clone());
        } else if demand.is_negative() {
            add_arc(&mut adjacency, &mut arcs, vertex, sink, -demand);
        }
    }

    let mut remaining = supply;
    let mut predecessor = vec![usize::MAX; vertices];
    let mut queue = VecDeque::new();
    loop {
        if Instant::now() >= deadline {
            return Answer::Unknown;
        }
        predecessor.fill(usize::MAX);
        // The supersource has no predecessor, but must count as visited.
        predecessor[source] = 0;
        queue.clear();
        queue.push_back(source);
        'search: while let Some(vertex) = queue.pop_front() {
            for &index in &adjacency[vertex] {
                if Instant::now() >= deadline {
                    return Answer::Unknown;
                }
                let arc = &arcs[index];
                if arc.residual.is_positive() && predecessor[arc.target] == usize::MAX {
                    predecessor[arc.target] = index;
                    if arc.target == sink {
                        break 'search;
                    }
                    queue.push_back(arc.target);
                }
            }
        }
        if predecessor[sink] == usize::MAX {
            break;
        }
        let mut amount = remaining.clone();
        let mut vertex = sink;
        while vertex != source {
            if Instant::now() >= deadline {
                return Answer::Unknown;
            }
            let index = predecessor[vertex];
            if arcs[index].residual < amount {
                amount = arcs[index].residual.clone();
            }
            vertex = arcs[index ^ 1].target;
        }
        vertex = sink;
        while vertex != source {
            if Instant::now() >= deadline {
                return Answer::Unknown;
            }
            let index = predecessor[vertex];
            arcs[index].residual -= &amount;
            arcs[index ^ 1].residual += &amount;
            vertex = arcs[index ^ 1].target;
        }
        remaining -= amount;
        if remaining.is_zero() {
            return Answer::Feasible;
        }
    }

    let mut cut = Vec::new();
    let mut excess = BigInt::zero();
    for (vertex, demand) in demands.iter().enumerate() {
        if Instant::now() >= deadline {
            return Answer::Unknown;
        }
        if predecessor[vertex] != usize::MAX {
            cut.push(vertex);
            excess += demand;
        }
    }
    // Check the obstruction directly against the original capacities, including
    // actual infinity, without relying on residual capacity arithmetic.
    for edge in edges {
        if Instant::now() >= deadline {
            return Answer::Unknown;
        }
        if predecessor[edge.source] != usize::MAX && predecessor[edge.target] == usize::MAX {
            let Some(capacity) = &edge.capacity else {
                return Answer::Unknown;
            };
            excess -= capacity;
        }
    }
    if excess.is_positive() {
        Answer::Cut(cut)
    } else {
        Answer::Unknown
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn edge(source: usize, target: usize, capacity: Option<i64>) -> Edge {
        Edge {
            source,
            target,
            capacity: capacity.map(BigInt::from),
        }
    }

    fn solve(nodes: usize, edges: &[Edge], demands: &[i64]) -> Answer {
        separate(
            nodes,
            edges,
            &demands
                .iter()
                .copied()
                .map(BigInt::from)
                .collect::<Vec<_>>(),
            Instant::now() + Duration::from_secs(5),
        )
    }

    #[test]
    fn finite_capacity_feasibility_and_cut() {
        assert_eq!(solve(2, &[edge(0, 1, Some(3))], &[3, -3]), Answer::Feasible);
        assert_eq!(
            solve(2, &[edge(0, 1, Some(2))], &[3, -3]),
            Answer::Cut(vec![0])
        );
        assert_eq!(
            solve(3, &[edge(0, 2, None), edge(2, 1, Some(1))], &[2, -2, 0]),
            Answer::Cut(vec![0, 2])
        );
    }

    #[test]
    fn nonzero_total_demand_is_unknown() {
        assert_eq!(solve(1, &[], &[-1]), Answer::Unknown);
        assert_eq!(solve(1, &[], &[1]), Answer::Unknown);
    }

    #[test]
    fn unbounded_edge_keeps_capacity_when_count_would_be_zero() {
        assert_eq!(solve(2, &[edge(0, 1, None)], &[1, -1]), Answer::Feasible);
        assert_eq!(
            solve(2, &[edge(0, 1, Some(0))], &[1, -1]),
            Answer::Cut(vec![0])
        );
    }

    #[test]
    fn self_loops_and_zero_demands() {
        assert_eq!(solve(0, &[], &[]), Answer::Feasible);
        assert_eq!(solve(1, &[edge(0, 0, None)], &[0]), Answer::Feasible);
        assert_eq!(
            solve(
                2,
                &[edge(0, 0, None), edge(0, 1, Some(1)), edge(1, 1, None)],
                &[1, -1]
            ),
            Answer::Feasible
        );
        assert_eq!(
            solve(2, &[edge(0, 0, None)], &[1, -1]),
            Answer::Cut(vec![0])
        );
    }

    #[test]
    fn residual_reverse_arcs_reroute_flow() {
        assert_eq!(
            solve(
                6,
                &[
                    edge(0, 1, Some(1)),
                    edge(0, 2, Some(1)),
                    edge(1, 3, Some(1)),
                    edge(1, 4, Some(1)),
                    edge(2, 3, Some(1)),
                    edge(3, 5, Some(1)),
                    edge(4, 5, Some(1)),
                ],
                &[2, 0, 0, 0, 0, -2],
            ),
            Answer::Feasible
        );
    }

    #[test]
    fn capacities_and_demands_exceed_u64() {
        let amount = BigInt::from(1_u8) << 100usize;
        let demands = vec![amount.clone(), -&amount];
        let deadline = Instant::now() + Duration::from_secs(5);
        assert_eq!(
            separate(
                2,
                &[Edge {
                    source: 0,
                    target: 1,
                    capacity: Some(amount.clone())
                }],
                &demands,
                deadline
            ),
            Answer::Feasible
        );
        assert_eq!(
            separate(
                2,
                &[Edge {
                    source: 0,
                    target: 1,
                    capacity: Some(amount - 1)
                }],
                &demands,
                deadline
            ),
            Answer::Cut(vec![0])
        );
    }

    #[test]
    fn invalid_inputs_and_expired_deadlines() {
        assert_eq!(solve(1, &[], &[]), Answer::Unknown);
        assert_eq!(solve(1, &[edge(0, 1, Some(0))], &[0]), Answer::Unknown);
        assert_eq!(solve(1, &[edge(0, 0, Some(-1))], &[0]), Answer::Unknown);
        assert_eq!(separate(0, &[], &[], Instant::now()), Answer::Unknown);
    }
}
