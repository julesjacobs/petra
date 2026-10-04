use super::*;
use std::collections::BTreeSet;

const MAX_REFINEMENTS: usize = 8;
const MAX_OBLIGATIONS: usize = 32;

#[derive(Default)]
pub(super) struct Obligations {
    // Each layer contains distinct (original transition, source component) pairs.
    layers: BTreeMap<usize, BTreeSet<(usize, usize)>>,
}

pub(super) fn obligations(
    game: &[GameNode],
    losses: &[Option<Loss>],
    initial: &[(usize, Coefficients)],
    budget: &mut Budget,
) -> Result<Obligations> {
    budget.diagnostics.phase("causal-obligations");
    budget.spend(game.len())?;
    let mut seen = vec![false; game.len()];
    let mut todo = Vec::new();
    for &(node, _) in initial {
        budget.tick()?;
        ensure!(
            losses[node].is_some(),
            "winning initial node in losing explanation"
        );
        if !seen[node] {
            seen[node] = true;
            todo.push(node);
        }
    }
    let mut cursor = 0;
    while cursor < todo.len() {
        budget.tick()?;
        let node = todo[cursor];
        let loss = losses[node].unwrap();
        for &target in &game[node].edges[loss.edge].targets {
            budget.tick()?;
            ensure!(
                losses[target].is_some_and(|l| l.rank < loss.rank),
                "noncausal losing edge"
            );
            if !seen[target] {
                seen[target] = true;
                todo.push(target);
            }
        }
        cursor += 1;
    }
    // Elimination ranks topologically order every alternative of a cause edge.
    budget.spend(
        todo.len()
            .saturating_mul(todo.len().max(1).ilog2() as usize + 1),
    )?;
    todo.sort_unstable_by_key(|&node| losses[node].unwrap().rank);
    budget.spend(game.len())?;
    let mut distance = vec![0usize; game.len()];
    let mut result = Obligations::default();
    let mut earlier_count = 0;
    for node in todo {
        budget.tick()?;
        let edge = &game[node].edges[losses[node].unwrap().edge];
        budget.spend(edge.targets.len())?;
        let depth = edge
            .targets
            .iter()
            .map(|&n| distance[n] + 1)
            .min()
            .unwrap_or(0);
        distance[node] = depth;
        let layer = result.layers.entry(depth).or_default();
        let inserted = layer.insert((edge.transition, game[node].component));
        if depth == 0 {
            if layer.len() > MAX_OBLIGATIONS {
                layer.pop_last();
                budget.diagnostics.add("causal_obligations_truncated", 1);
            }
        } else {
            earlier_count += usize::from(inserted);
            if earlier_count > MAX_OBLIGATIONS {
                let mut last = result.layers.last_entry().unwrap();
                last.get_mut().pop_last();
                if last.get().is_empty() {
                    last.remove();
                }
                earlier_count -= 1;
                budget.diagnostics.add("causal_obligations_truncated", 1);
            }
        }
    }
    budget.diagnostics.add("causal_layers", result.layers.len());
    Ok(result)
}

struct Preparation {
    eligible: Vec<usize>,
    degree: Vec<usize>,
    setup_lower_bound: usize,
}

fn prepare(q: &RawQuery, budget: &mut Budget) -> Result<Preparation> {
    budget.tick()?;
    q.validate()?;
    ensure!(
        q.target.excluded_automaton.is_none(),
        "component invariants require a semilinear target"
    );
    let credits = credits(q, budget)?;
    budget.spend(q.places.len())?;
    let mut eligible = vec![true; q.places.len()];
    for p in q
        .target
        .response_places
        .iter()
        .copied()
        .chain(credits.iter().map(|c| c.place))
    {
        budget.tick()?;
        eligible[p] = false;
    }
    let mut degree = vec![0usize; q.places.len()];
    let mut arcs = 0usize;
    for tr in &q.transitions {
        budget.tick()?;
        for &(p, _) in tr.pre.iter().chain(&tr.post) {
            budget.tick()?;
            degree[p] = degree[p].saturating_add(1);
            arcs = arcs.saturating_add(1);
        }
        if tr.pre.is_empty() {
            for &(p, _) in &tr.post {
                eligible[p] = false;
            }
        }
    }
    Ok(Preparation {
        eligible: eligible
            .iter()
            .enumerate()
            .filter_map(|(p, &ok)| ok.then_some(p))
            .collect(),
        degree,
        setup_lower_bound: q
            .places
            .len()
            .saturating_add(q.transitions.len().saturating_mul(2))
            .saturating_add(arcs)
            .saturating_add(1),
    })
}

fn choose_coordinate(
    q: &RawQuery,
    prepared: &Preparation,
    selected: &[usize],
    obligations: &Obligations,
    budget: &mut Budget,
) -> Result<Option<usize>> {
    budget.diagnostics.phase("coordinate-choice");
    for layer in obligations.layers.values() {
        let mut counts = BTreeMap::<usize, usize>::new();
        for &(transition, _) in layer {
            for &(p, _) in &q.transitions[transition].pre {
                budget.tick()?;
                if prepared.eligible.binary_search(&p).is_ok()
                    && selected.binary_search(&p).is_err()
                {
                    *counts.entry(p).or_default() += 1;
                }
            }
        }
        if let Some((&place, _)) = counts
            .iter()
            .min_by_key(|&(&p, &count)| (std::cmp::Reverse(count), prepared.degree[p], p))
        {
            return Ok(Some(place));
        }
    }
    Ok(None)
}

fn attempt(
    q: &RawQuery,
    selected: &[usize],
    deadline: Instant,
    reservation: usize,
    operation: &'static str,
) -> Result<Attempt> {
    let check_reserve = reservation / 4;
    let mut budget = Budget {
        deadline,
        remaining: reservation - check_reserve,
        diagnostics: Diagnostics::new(operation),
    };
    budget.diagnostics.add("attempt_reserved_work", reservation);
    budget
        .diagnostics
        .add("attempt_check_reservation", check_reserve);
    let result = attempt_projection(
        q,
        &mut budget,
        Projection::Selected(selected, check_reserve),
    );
    budget.diagnostics.add("attempt_debited_work", reservation);
    budget.diagnostics.add(
        "attempt_discovery_used_work",
        reservation - check_reserve - budget.remaining,
    );
    let status = match &result {
        Ok(Attempt::Checked(_)) => "checked",
        Ok(Attempt::InitialOutside) => "initial-outside",
        Ok(Attempt::Losing(_)) => "losing-game",
        Err(_) => "limited-or-invalid",
    };
    budget.diagnostics.finish(status);
    result
}

/// Opt-in bounded projection refinement. Only an independently checked invariant
/// proves exclusion; a losing abstract game merely suggests the next coordinate.
pub fn discover_adaptive(q: &RawQuery, deadline: Instant, max_work: usize) -> Result<Certificate> {
    discover_adaptive_inner(q, deadline, max_work, false)
}

/// Refines only by complete supports of verified nonincreasing 0/1 potentials.
pub fn discover_adaptive_groups(
    q: &RawQuery,
    deadline: Instant,
    max_work: usize,
) -> Result<Certificate> {
    discover_adaptive_inner(q, deadline, max_work, true)
}

fn discover_adaptive_inner(
    q: &RawQuery,
    deadline: Instant,
    max_work: usize,
    bounded_groups: bool,
) -> Result<Certificate> {
    let started = Instant::now();
    let duration = deadline.saturating_duration_since(started);
    let empty_deadline = started + duration / 8;
    let adaptive_deadline = started + duration / 2;
    let mut setup = Budget {
        deadline: empty_deadline,
        remaining: max_work / 8,
        diagnostics: Diagnostics::new(if bounded_groups {
            "raw-negative-groups-preparation"
        } else {
            "raw-negative-adaptive-preparation"
        }),
    };
    let preparation = prepare(q, &mut setup);
    setup.diagnostics.finish_result(&preparation);
    let setup_used = max_work / 8 - setup.remaining;
    let remaining = max_work - setup_used;
    let prepared = match preparation {
        Ok(prepared) => prepared,
        Err(_) => return discover_structural(q, deadline, remaining),
    };
    let empty_work = remaining / 8;
    let adaptive_work = remaining.saturating_mul(3) / 8;
    let mut fallback_work = remaining - empty_work - adaptive_work;
    let mut selected = vec![];
    let mut last = Some(attempt(
        q,
        &selected,
        empty_deadline,
        empty_work,
        if bounded_groups {
            "raw-negative-groups-empty"
        } else {
            "raw-negative-adaptive-empty"
        },
    ));
    let mut unused = adaptive_work;
    for iteration in 0..MAX_REFINEMENTS {
        let obligations = match last.take().unwrap() {
            Ok(Attempt::Checked(certificate)) => return Ok(certificate),
            Ok(Attempt::InitialOutside) => {
                return Err(anyhow!(
                    "initial credited marking outside candidate components"
                ));
            }
            Ok(Attempt::Losing(obligations)) => obligations,
            Err(_) => break,
        };
        let reservation = unused / (MAX_REFINEMENTS - iteration);
        let mut selection_budget = Budget {
            deadline: adaptive_deadline,
            remaining: reservation,
            diagnostics: Diagnostics::new(if bounded_groups {
                "raw-negative-groups-refinement"
            } else {
                "raw-negative-adaptive-refinement"
            }),
        };
        selection_budget
            .diagnostics
            .add("refinement_reserved_work", reservation);
        selection_budget
            .diagnostics
            .add("projection_setup_lower_bound", prepared.setup_lower_bound);
        if reservation - reservation / 4 < prepared.setup_lower_bound {
            selection_budget
                .diagnostics
                .finish("setup-reservation-too-small");
            break;
        }
        if Instant::now() >= adaptive_deadline {
            selection_budget.diagnostics.finish("deadline");
            break;
        }
        let next = choose_coordinate(q, &prepared, &selected, &obligations, &mut selection_budget)
            .and_then(|guard| match guard {
                Some(guard) if bounded_groups => {
                    groups::discover(q, &prepared.eligible, guard, &mut selection_budget)
                }
                Some(guard) => Ok(Some(vec![guard])),
                None => Ok(None),
            })
            .and_then(|support| {
                if bounded_groups && let Some(support) = &support {
                    let size = selected.len().saturating_add(support.len());
                    selection_budget
                        .spend(size.saturating_mul(size.max(1).ilog2() as usize + 2))?;
                }
                Ok(support)
            });
        if matches!(next, Ok(None)) {
            selection_budget
                .diagnostics
                .finish("no-refinement-candidate");
        } else {
            selection_budget.diagnostics.finish_result(&next);
        }
        let selection_used = reservation - selection_budget.remaining;
        unused -= selection_used;
        let Ok(Some(support)) = next else { break };
        selected.extend(support);
        selected.sort_unstable();
        selected.dedup();
        let attempt_work = reservation - selection_used;
        unused -= attempt_work;
        let slots_left = (MAX_REFINEMENTS - iteration) as u32;
        let now = Instant::now();
        let slot_deadline = now + adaptive_deadline.saturating_duration_since(now) / slots_left;
        last = Some(attempt(
            q,
            &selected,
            slot_deadline,
            attempt_work,
            if bounded_groups {
                "raw-negative-groups-projection"
            } else {
                "raw-negative-adaptive-projection"
            },
        ));
        if selected == prepared.eligible {
            break;
        }
    }
    match last {
        Some(Ok(Attempt::Checked(certificate))) => return Ok(certificate),
        Some(Ok(Attempt::InitialOutside)) => {
            return Err(anyhow!(
                "initial credited marking outside candidate components"
            ));
        }
        _ => {}
    }
    fallback_work += unused;
    attempt(
        q,
        &prepared.eligible,
        deadline,
        fallback_work,
        if bounded_groups {
            "raw-negative-groups-structural"
        } else {
            "raw-negative-adaptive-structural"
        },
    )?
    .certificate()
}

fn discover_structural(q: &RawQuery, deadline: Instant, max_work: usize) -> Result<Certificate> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
        diagnostics: Diagnostics::new("raw-negative-adaptive-preparation-fallback"),
    };
    let result = discover_projection(q, &mut budget, true);
    budget.diagnostics.finish_result(&result);
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Transition;
    use crate::raw_target::{LinearSet, RawTarget};
    use std::io::Write;
    use std::process::{Command, Stdio};
    use std::time::Duration;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(10)
    }

    fn budget() -> Budget {
        Budget {
            deadline: deadline(),
            remaining: 100_000,
            diagnostics: Diagnostics::disabled(),
        }
    }

    fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
        Transition {
            name: "anonymous".into(),
            pre: pre.to_vec(),
            post: post.to_vec(),
        }
    }

    fn query(initial: &[u64], transitions: Vec<Transition>) -> RawQuery {
        RawQuery {
            format: "ser-raw-v1".into(),
            places: (0..initial.len()).map(|p| format!("p{p}")).collect(),
            initial: initial.to_vec(),
            transitions,
            target: RawTarget {
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![],
                response_places: vec![initial.len() - 1],
                excluded_semilinear: vec![LinearSet {
                    base: vec![],
                    periods: vec![],
                }],
                excluded_automaton: None,
            },
        }
    }

    fn enumerable_reaches_nonzero_response(q: &RawQuery) -> bool {
        let mut seen = HashSet::from([q.initial.clone()]);
        let mut todo = vec![q.initial.clone()];
        while let Some(marking) = todo.pop() {
            if *marking.last().unwrap() != 0 {
                return true;
            }
            for tr in &q.transitions {
                if tr.pre.iter().any(|&(p, w)| marking[p] < w) {
                    continue;
                }
                let mut successor = marking.clone();
                for &(p, w) in &tr.pre {
                    successor[p] -= w;
                }
                for &(p, w) in &tr.post {
                    successor[p] += w;
                }
                if seen.insert(successor.clone()) {
                    todo.push(successor);
                }
            }
            assert!(
                seen.len() < 100,
                "fixture must be finitely enumerable or reach its target"
            );
        }
        false
    }

    fn python_accepts(q: &RawQuery, c: &Certificate) -> bool {
        let mut child = Command::new("python3")
            .args(["-c", "import json,sys,time; sys.path.insert(0,'scripts'); from raw_invariant_check import verify; q,c=json.load(sys.stdin); verify(q,c,time.monotonic()+10)"])
            .current_dir(env!("CARGO_MANIFEST_DIR"))
            .stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::null())
            .spawn().unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(&serde_json::to_vec(&(q, c)).unwrap())
            .unwrap();
        child.wait().unwrap().success()
    }

    #[test]
    fn weighted_self_loop_guard_refines_and_unsafe_variant_never_certifies() {
        let mut q = query(&[1, 0], vec![transition(&[(0, 2)], &[(0, 2), (1, 1)])]);
        assert!(!enumerable_reaches_nonzero_response(&q));
        let certificate = discover_adaptive(&q, deadline(), 100_000).unwrap();
        assert_eq!(certificate.control_places, [0]);
        assert!(python_accepts(&q, &certificate));
        let mut forged = certificate.clone();
        forged.nodes[0].control[0] = 0;
        assert!(!python_accepts(&q, &forged));
        q.initial[0] = 2;
        assert!(enumerable_reaches_nonzero_response(&q));
        assert!(discover_adaptive(&q, deadline(), 100_000).is_err());
        assert!(!python_accepts(&q, &certificate));
    }

    #[test]
    fn limited_full_projection_refinement_keeps_the_structural_fallback() {
        let q = query(
            &[12, 0],
            vec![
                transition(&[(0, 1)], &[]),
                transition(&[(0, 13)], &[(0, 13), (1, 1)]),
            ],
        );
        assert!(!enumerable_reaches_nonzero_response(&q));
        assert!(attempt(&q, &[0], deadline(), 100, "test").is_err());
        let certificate = discover_adaptive(&q, deadline(), 2000).unwrap();
        assert_eq!(certificate.nodes.len(), 13);
        assert!(python_accepts(&q, &certificate));
    }

    #[test]
    fn bounded_group_closes_a_swap_whose_singleton_projection_is_unbounded() {
        let mut q = query(
            &[1, 0, 0],
            vec![
                transition(&[(0, 1)], &[(1, 1)]),
                transition(&[(1, 1)], &[(0, 1)]),
                transition(&[(0, 2)], &[(0, 2), (2, 1)]),
            ],
        );
        assert!(!enumerable_reaches_nonzero_response(&q));
        assert!(attempt(&q, &[0], deadline(), 1000, "test").is_err());
        let certificate = discover_adaptive_groups(&q, deadline(), 100_000).unwrap();
        assert_eq!(certificate.control_places, [0, 1]);
        assert_eq!(certificate.nodes.len(), 2);
        assert!(python_accepts(&q, &certificate));
        q.initial[0] = 2;
        assert!(enumerable_reaches_nonzero_response(&q));
        assert!(discover_adaptive_groups(&q, deadline(), 100_000).is_err());
        assert!(!python_accepts(&q, &certificate));
    }

    #[test]
    fn overlapping_group_union_is_a_bounded_projection() {
        let q = query(
            &[0, 1, 0, 0],
            vec![
                transition(&[(1, 1)], &[(0, 1), (2, 1)]),
                transition(&[(0, 2)], &[(0, 2), (3, 1)]),
                transition(&[(2, 2)], &[(2, 2), (3, 1)]),
            ],
        );
        assert!(!enumerable_reaches_nonzero_response(&q));
        let certificate = discover_adaptive_groups(&q, deadline(), 100_000).unwrap();
        assert_eq!(certificate.control_places, [0, 1, 2]);
        assert!(python_accepts(&q, &certificate));
        assert!(discover_adaptive_groups(&q, deadline(), 0).is_err());
        assert!(discover_adaptive_groups(&q, Instant::now(), 100_000).is_err());
    }

    #[test]
    fn an_old_stutter_gets_a_new_edge_and_the_checker_rejects_omission() {
        let q = query(&[1, 0, 0], vec![transition(&[(0, 1)], &[(1, 1)])]);
        assert!(!enumerable_reaches_nonzero_response(&q));
        let coarse = attempt(&q, &[], deadline(), 100_000, "test")
            .unwrap()
            .certificate()
            .unwrap();
        assert!(coarse.nodes[0].edges.is_empty());
        let mut refined = attempt(&q, &[0], deadline(), 100_000, "test")
            .unwrap()
            .certificate()
            .unwrap();
        assert_eq!(refined.nodes.len(), 2);
        assert_eq!(refined.nodes[0].edges[0].transition, 0);
        assert!(python_accepts(&q, &refined));
        refined.nodes[0].edges.clear();
        assert!(!python_accepts(&q, &refined));
        assert!(crate::raw_invariant::check(&q, &refined, deadline(), 100_000).is_err());
    }

    #[test]
    fn earlier_causal_guard_is_used_when_terminal_guard_is_already_selected() {
        let mut q = query(
            &[1, 0, 0, 0],
            vec![
                transition(&[(0, 1), (1, 1)], &[(1, 1), (2, 1)]),
                transition(&[(2, 1)], &[(2, 1), (3, 1)]),
            ],
        );
        assert!(!enumerable_reaches_nonzero_response(&q));
        let Attempt::Losing(obligations) =
            attempt(&q, &[0, 2], deadline(), 100_000, "test").unwrap()
        else {
            panic!("expected completed loss")
        };
        let mut work = budget();
        let prepared = prepare(&q, &mut work).unwrap();
        assert_eq!(
            choose_coordinate(&q, &prepared, &[0, 2], &obligations, &mut work).unwrap(),
            Some(1)
        );
        let certificate = attempt(&q, &[0, 1, 2], deadline(), 100_000, "test")
            .unwrap()
            .certificate()
            .unwrap();
        assert!(python_accepts(&q, &certificate));
        q.initial[1] = 1;
        assert!(enumerable_reaches_nonzero_response(&q));
        assert!(discover_adaptive(&q, deadline(), 100_000).is_err());
    }

    fn node(transition: usize, targets: &[usize]) -> GameNode {
        GameNode {
            control: Rc::new(StoredMarking::new(&[])),
            component: transition,
            edges: vec![GameEdge {
                transition,
                transfers: Rc::new(vec![]),
                targets: targets.to_vec(),
            }],
        }
    }

    #[test]
    fn explanation_follows_every_or_alternative_and_every_initial_choice() {
        let game = vec![
            node(0, &[1, 2]),
            node(1, &[]),
            node(2, &[]),
            node(3, &[]),
            node(4, &[]),
        ];
        let mut work = budget();
        let mut losses = vec![];
        assert_eq!(
            greatest_fixed_point_with_causes(&game, &mut work, Some(&mut losses)).unwrap(),
            [false; 5]
        );
        let explanation =
            obligations(&game, &losses, &[(0, vec![]), (3, vec![])], &mut work).unwrap();
        assert_eq!(
            explanation.layers[&0],
            BTreeSet::from([(1, 1), (2, 2), (3, 3)])
        );
        assert_eq!(explanation.layers[&1], BTreeSet::from([(0, 0)]));
        let supported = vec![node(0, &[1, 2]), node(1, &[]), node(2, &[2])];
        assert_eq!(
            greatest_fixed_point_with_causes(&supported, &mut work, Some(&mut vec![])).unwrap(),
            [true, false, true]
        );
    }

    #[test]
    fn terminal_obligations_are_bounded_and_stably_ordered() {
        let game: Vec<_> = (0..100).rev().map(|n| node(n, &[])).collect();
        let mut work = budget();
        let mut losses = vec![];
        greatest_fixed_point_with_causes(&game, &mut work, Some(&mut losses)).unwrap();
        let initial: Vec<_> = (0..game.len()).map(|n| (n, vec![])).collect();
        let explanation = obligations(&game, &losses, &initial, &mut work).unwrap();
        assert_eq!(
            explanation.layers[&0],
            (0..MAX_OBLIGATIONS).map(|n| (n, n)).collect()
        );
    }

    #[test]
    fn candidate_order_uses_obligation_count_degree_then_original_index() {
        let q = query(
            &[0, 0, 0, 0],
            vec![
                transition(&[(0, 1), (1, 1), (2, 1)], &[(0, 1)]),
                transition(&[(0, 1), (1, 1), (2, 1)], &[]),
            ],
        );
        let mut work = budget();
        let prepared = prepare(&q, &mut work).unwrap();
        let obligations = Obligations {
            layers: BTreeMap::from([(0, BTreeSet::from([(0, 0), (1, 0)]))]),
        };
        assert_eq!(
            choose_coordinate(&q, &prepared, &[], &obligations, &mut work).unwrap(),
            Some(1)
        );
        assert_eq!(
            choose_coordinate(&q, &prepared, &[1], &obligations, &mut work).unwrap(),
            Some(2)
        );
    }

    #[test]
    fn resource_overflow_and_dimension_stops_do_not_become_losing_games() {
        let q = query(&[1, 0], vec![transition(&[(0, 1)], &[(0, 2)])]);
        assert!(attempt(&q, &[0], deadline(), 1000, "test").is_err());
        assert!(discover_adaptive(&q, deadline(), 0).is_err());
        assert!(discover_adaptive(&q, Instant::now(), 100_000).is_err());
        let overflow = query(&[u64::MAX, 0], vec![transition(&[(0, 1)], &[(0, 2)])]);
        assert!(attempt(&overflow, &[0], deadline(), 100_000, "test").is_err());
        let component = Component {
            base: Vector::new(),
            periods: vec![vector(&[(1, 1)]); 129],
            exact: HashMap::new(),
        };
        assert!(coefficients(&vector(&[(1, 2)]), &component, &mut budget()).is_err());
    }

    #[test]
    fn explicit_projection_is_sorted_unique_and_initial_outside_stops_refinement() {
        let q = query(&[0, 0, 0], vec![]);
        assert!(attempt(&q, &[1, 0], deadline(), 1000, "test").is_err());
        assert!(attempt(&q, &[0, 0], deadline(), 1000, "test").is_err());
        assert!(attempt(&q, &[3], deadline(), 1000, "test").is_err());
        let outside = query(&[0, 1], vec![]);
        assert!(matches!(
            attempt(&outside, &[], deadline(), 1000, "test"),
            Ok(Attempt::InitialOutside)
        ));
        assert!(discover_adaptive(&outside, deadline(), 100_000).is_err());
    }

    #[test]
    fn completion_credits_remain_checked_across_adaptive_attempts() {
        let mut q = query(
            &[1, 1, 0],
            vec![
                transition(&[(0, 2)], &[(0, 2), (1, 1)]),
                transition(&[(1, 1)], &[(2, 1)]),
            ],
        );
        q.target.zero_places = vec![1];
        q.target.excluded_semilinear[0].base = vec![(2, 1)];
        let certificate = discover_adaptive(&q, deadline(), 100_000).unwrap();
        assert_eq!(certificate.control_places, [0]);
        assert_eq!(certificate.credits.len(), 1);
        assert!(python_accepts(&q, &certificate));
        q.initial[0] = 2;
        assert!(discover_adaptive(&q, deadline(), 100_000).is_err());
    }
}
