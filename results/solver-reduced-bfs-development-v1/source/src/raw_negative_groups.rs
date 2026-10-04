use super::*;

const MAX_SUPPORT: usize = 32;
const MAX_PROPOSALS: usize = 128;

fn transition_mass(
    arcs: &[(usize, u64)],
    support: &[usize],
    budget: &mut Budget,
) -> Result<BigInt> {
    let mut mass = BigInt::zero();
    for &(place, weight) in arcs {
        budget.tick()?;
        if support.binary_search(&place).is_ok() {
            mass += weight;
        }
    }
    Ok(mass)
}

fn first_increase(q: &RawQuery, support: &[usize], budget: &mut Budget) -> Result<Option<usize>> {
    for (index, transition) in q.transitions.iter().enumerate() {
        budget.tick()?;
        let pre = transition_mass(&transition.pre, support, budget)?;
        let post = transition_mass(&transition.post, support, budget)?;
        if post > pre {
            return Ok(Some(index));
        }
    }
    Ok(None)
}

fn verify_support(
    q: &RawQuery,
    eligible: &[usize],
    guard: usize,
    support: &[usize],
    budget: &mut Budget,
) -> Result<BigInt> {
    budget.diagnostics.phase("bounded-group-validation");
    budget.spend(support.len().saturating_add(1))?;
    ensure!(
        support.windows(2).all(|w| w[0] < w[1]),
        "potential support must be sorted and unique"
    );
    ensure!(
        support.binary_search(&guard).is_ok(),
        "potential omits causal guard"
    );
    let mut initial_mass = BigInt::zero();
    for &place in support {
        budget.tick()?;
        ensure!(
            place < q.places.len() && eligible.binary_search(&place).is_ok(),
            "potential contains ineligible place"
        );
        initial_mass += q.initial[place];
    }
    ensure!(
        first_increase(q, support, budget)?.is_none(),
        "place potential increases on an original transition"
    );
    Ok(initial_mass)
}

/// Proposes small 0/1 nonincreasing potentials containing the causal guard.
/// Failure supplies no boundedness conclusion; accepted supports are rescanned
/// exactly before any of their coordinates enter the projection.
pub(super) fn discover(
    q: &RawQuery,
    eligible: &[usize],
    guard: usize,
    budget: &mut Budget,
) -> Result<Option<Vec<usize>>> {
    budget.diagnostics.phase("bounded-group-discovery");
    budget.tick()?;
    ensure!(
        guard < q.places.len() && eligible.binary_search(&guard).is_ok(),
        "ineligible causal guard"
    );
    let mut seen = HashSet::from([vec![guard]]);
    let mut queue = VecDeque::from([vec![guard]]);
    while let Some(support) = queue.pop_front() {
        budget.tick()?;
        budget.diagnostics.add("group_proposals_examined", 1);
        let Some(transition) = first_increase(q, &support, budget)? else {
            verify_support(q, eligible, guard, &support, budget)?;
            budget
                .diagnostics
                .add("certified_group_places", support.len());
            return Ok(Some(support));
        };
        if support.len() == MAX_SUPPORT {
            budget.diagnostics.add("group_support_cap", 1);
            continue;
        }
        let transition = &q.transitions[transition];
        let mut delta = Vector::new();
        for (sign, arcs) in [(-1i32, &transition.pre), (1i32, &transition.post)] {
            for &(place, weight) in arcs {
                budget.tick()?;
                add(&mut delta, place, BigInt::from(weight) * sign);
            }
        }
        // Any 0/1 extension repairing this increase includes a negative column.
        for (place, change) in delta {
            budget.tick()?;
            if !change.is_negative() || eligible.binary_search(&place).is_err() {
                continue;
            }
            let Err(index) = support.binary_search(&place) else {
                continue;
            };
            budget.spend(support.len().saturating_add(1).saturating_mul(2))?;
            let mut candidate = support.clone();
            candidate.insert(index, place);
            if seen.contains(&candidate) {
                continue;
            }
            if seen.len() == MAX_PROPOSALS {
                budget.diagnostics.add("group_proposal_cap", 1);
                continue;
            }
            seen.insert(candidate.clone());
            queue.push_back(candidate);
        }
    }
    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Transition;
    use std::time::Duration;

    fn budget() -> Budget {
        Budget {
            deadline: Instant::now() + Duration::from_secs(5),
            remaining: 100_000,
            diagnostics: Diagnostics::disabled(),
        }
    }

    type Arcs<'a> = &'a [(usize, u64)];

    fn query(initial: &[u64], arcs: &[(Arcs<'_>, Arcs<'_>)]) -> RawQuery {
        let q = RawQuery {
            format: "ser-raw-v1".into(),
            places: (0..initial.len()).map(|p| format!("p{p}")).collect(),
            initial: initial.to_vec(),
            transitions: arcs
                .iter()
                .map(|(pre, post)| Transition {
                    name: "anonymous".into(),
                    pre: pre.to_vec(),
                    post: post.to_vec(),
                })
                .collect(),
            target: crate::raw_target::RawTarget {
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![],
                response_places: vec![],
                excluded_automaton: None,
                excluded_semilinear: vec![crate::raw_target::LinearSet {
                    base: vec![],
                    periods: vec![],
                }],
            },
        };
        q.validate().unwrap();
        q
    }

    #[test]
    fn conserved_swap_needs_both_places_and_zero_mass_is_valid() {
        for initial in [[1, 0], [0, 0], [u64::MAX, u64::MAX]] {
            let q = query(&initial, &[(&[(0, 1)], &[(1, 1)]), (&[(1, 1)], &[(0, 1)])]);
            let support = discover(&q, &[0, 1], 0, &mut budget()).unwrap().unwrap();
            assert_eq!(support, [0, 1]);
            assert_eq!(
                verify_support(&q, &[0, 1], 0, &support, &mut budget()).unwrap(),
                BigInt::from(initial[0]) + initial[1]
            );
            assert!(verify_support(&q, &[0, 1], 0, &[0], &mut budget()).is_err());
        }
    }

    #[test]
    fn unbounded_source_and_growth_have_no_proposed_support() {
        for q in [
            query(&[0], &[(&[], &[(0, 1)])]),
            query(&[1], &[(&[(0, 1)], &[(0, 2)])]),
        ] {
            assert!(discover(&q, &[0], 0, &mut budget()).unwrap().is_none());
            assert!(verify_support(&q, &[0], 0, &[0], &mut budget()).is_err());
        }
    }

    #[test]
    fn weighted_arcs_are_checked_exactly_above_float_precision() {
        let weight = (1u64 << 53) + 17;
        let mut q = query(
            &[1, 0],
            &[(&[(0, weight)], &[(1, weight)]), (&[(1, 1)], &[(0, 1)])],
        );
        assert_eq!(
            discover(&q, &[0, 1], 0, &mut budget()).unwrap(),
            Some(vec![0, 1])
        );
        q.transitions[0].post[0].1 += 1;
        assert!(discover(&q, &[0, 1], 0, &mut budget()).unwrap().is_none());
        assert!(verify_support(&q, &[0, 1], 0, &[0, 1], &mut budget()).is_err());
    }

    #[test]
    fn overlapping_potentials_need_no_union_indicator_potential() {
        let q = query(&[0, 1, 0], &[(&[(1, 1)], &[(0, 1), (2, 1)])]);
        assert_eq!(
            discover(&q, &[0, 1, 2], 0, &mut budget()).unwrap(),
            Some(vec![0, 1])
        );
        assert_eq!(
            discover(&q, &[0, 1, 2], 2, &mut budget()).unwrap(),
            Some(vec![1, 2])
        );
        assert!(verify_support(&q, &[0, 1, 2], 0, &[0, 1, 2], &mut budget()).is_err());
    }

    #[test]
    fn forged_and_ineligible_supports_are_rejected_without_truncation() {
        let q = query(&[1, 0], &[(&[(0, 1)], &[(1, 1)]), (&[(1, 1)], &[(0, 1)])]);
        for support in [vec![], vec![0], vec![1], vec![0, 0], vec![1, 0], vec![0, 2]] {
            assert!(verify_support(&q, &[0, 1], 0, &support, &mut budget()).is_err());
        }
        assert!(verify_support(&q, &[0], 0, &[0, 1], &mut budget()).is_err());
        assert!(discover(&q, &[0], 0, &mut budget()).unwrap().is_none());
    }

    #[test]
    fn work_and_deadline_stops_do_not_supply_a_group() {
        let q = query(&[1, 0], &[(&[(0, 1)], &[(1, 1)]), (&[(1, 1)], &[(0, 1)])]);
        let mut limited = budget();
        limited.remaining = 0;
        assert!(discover(&q, &[0, 1], 0, &mut limited).is_err());
        let mut expired = budget();
        expired.deadline = Instant::now();
        assert!(discover(&q, &[0, 1], 0, &mut expired).is_err());
        let mut checking = budget();
        checking.remaining = 4;
        assert!(verify_support(&q, &[0, 1], 0, &[0, 1], &mut checking).is_err());
    }

    #[test]
    fn proposal_search_is_deterministic_and_support_capped() {
        let mut q = query(&[0, 1, 1], &[(&[(2, 1), (1, 1)], &[(0, 1)])]);
        assert_eq!(
            discover(&q, &[0, 1, 2], 0, &mut budget()).unwrap(),
            Some(vec![0, 1])
        );
        q.transitions[0].pre.reverse();
        assert_eq!(
            discover(&q, &[0, 1, 2], 0, &mut budget()).unwrap(),
            Some(vec![0, 1])
        );
        let mut cycle = query(&[0; MAX_SUPPORT + 1], &[]);
        cycle.transitions = (0..=MAX_SUPPORT)
            .map(|p| Transition {
                name: "cycle".into(),
                pre: vec![(p, 1)],
                post: vec![((p + 1) % (MAX_SUPPORT + 1), 1)],
            })
            .collect();
        assert!(
            discover(
                &cycle,
                &(0..=MAX_SUPPORT).collect::<Vec<_>>(),
                0,
                &mut budget()
            )
            .unwrap()
            .is_none()
        );
    }
}
