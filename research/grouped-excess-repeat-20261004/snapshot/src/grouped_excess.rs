//! Inductive bounds from sums of positive excess above a group threshold.
use crate::{model::Problem, search::Outcome};
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_traits::{Signed, Zero};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::BTreeMap,
    time::{Duration, Instant},
};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub groups: Vec<Vec<usize>>,
    pub thresholds: Vec<u64>,
    pub target_row: usize,
    pub sign: i8,
}

struct Work {
    deadline: Instant,
    remaining: usize,
}

impl Work {
    fn take(&mut self, amount: usize) -> Result<()> {
        ensure!(Instant::now() < self.deadline, "grouped excess deadline");
        self.remaining = self
            .remaining
            .checked_sub(amount)
            .context("grouped excess work limit")?;
        Ok(())
    }
}

fn positive(value: BigInt) -> BigInt {
    value.max(BigInt::zero())
}

fn upper_change(pre: &BigInt, post: &BigInt, threshold: u64) -> BigInt {
    let delta = post - pre;
    if delta.is_negative() {
        -((-delta).min(positive(pre - BigInt::from(threshold))))
    } else {
        delta
    }
}

fn invariant(problem: &Problem, certificate: &Certificate, work: &mut Work) -> Result<BigInt> {
    work.take(
        problem
            .places
            .len()
            .saturating_add(certificate.groups.len()),
    )?;
    ensure!(
        certificate.kind == "grouped-excess-v1",
        "invalid grouped excess kind"
    );
    ensure!(
        certificate.groups.len() == certificate.thresholds.len(),
        "group threshold dimension mismatch"
    );
    let mut owner = vec![None; problem.places.len()];
    let mut budget = BigInt::zero();
    for (group, (places, &threshold)) in certificate
        .groups
        .iter()
        .zip(&certificate.thresholds)
        .enumerate()
    {
        work.take(places.len().saturating_add(1))?;
        ensure!(!places.is_empty(), "empty place group");
        let mut initial = BigInt::zero();
        for &place in places {
            let slot = owner.get_mut(place).context("invalid group place")?;
            ensure!(slot.replace(group).is_none(), "duplicate group place");
            initial += problem.initial[place];
        }
        budget += positive(initial - BigInt::from(threshold));
    }
    ensure!(
        owner.iter().all(Option::is_some),
        "place partition is incomplete"
    );
    for transition in &problem.transitions {
        work.take(
            transition
                .pre
                .len()
                .saturating_add(transition.post.len())
                .saturating_add(1),
        )?;
        let mut arcs = BTreeMap::<usize, (BigInt, BigInt)>::new();
        for &(place, weight) in &transition.pre {
            arcs.entry(owner[place].unwrap()).or_default().0 += weight;
        }
        for &(place, weight) in &transition.post {
            arcs.entry(owner[place].unwrap()).or_default().1 += weight;
        }
        let mut change = BigInt::zero();
        for (group, (pre, post)) in arcs {
            work.take(1)?;
            change += upper_change(&pre, &post, certificate.thresholds[group]);
        }
        ensure!(!change.is_positive(), "grouped excess can increase");
    }
    Ok(budget)
}

fn target_bound(
    problem: &Problem,
    certificate: &Certificate,
    budget: &BigInt,
    work: &mut Work,
) -> Result<(BigInt, BigInt)> {
    let target = problem
        .target
        .get(certificate.target_row)
        .context("invalid target row")?;
    ensure!(
        certificate.sign == 1 || (certificate.sign == -1 && target.equality),
        "invalid target sign"
    );
    let mut upper = BigInt::zero();
    let mut maximum = BigInt::zero();
    for (places, &threshold) in certificate.groups.iter().zip(&certificate.thresholds) {
        work.take(places.len().saturating_add(1))?;
        let weight = places.iter().fold(BigInt::zero(), |weight, &place| {
            weight.max(BigInt::from(target.coefficients[place]) * certificate.sign)
        });
        upper += &weight * threshold;
        maximum = maximum.max(weight);
    }
    upper += maximum * budget;
    Ok((upper, BigInt::from(target.bound) * certificate.sign))
}

pub fn verify(problem: &Problem, proof: &Value, deadline: Instant) -> Result<()> {
    problem.validate()?;
    let certificate: Certificate = serde_json::from_value(proof.clone())?;
    let mut work = Work {
        deadline,
        remaining: usize::MAX,
    };
    let budget = invariant(problem, &certificate, &mut work)?;
    let (upper, required) = target_bound(problem, &certificate, &budget, &mut work)?;
    ensure!(upper < required, "grouped excess does not exclude target");
    work.take(0)
}

fn find(parent: &mut [usize], mut place: usize) -> usize {
    while parent[place] != place {
        parent[place] = parent[parent[place]];
        place = parent[place];
    }
    place
}

fn groups(problem: &Problem, work: &mut Work) -> Result<Vec<Vec<usize>>> {
    work.take(problem.places.len())?;
    let mut parent: Vec<_> = (0..problem.places.len()).collect();
    for transition in &problem.transitions {
        work.take(1)?;
        if let ([(source, 1)], [(destination, 1)]) =
            (transition.pre.as_slice(), transition.post.as_slice())
        {
            let source = find(&mut parent, *source);
            let destination = find(&mut parent, *destination);
            if source != destination {
                parent[source] = destination;
            }
        }
    }
    let mut partition = BTreeMap::<usize, Vec<usize>>::new();
    for place in 0..problem.places.len() {
        work.take(1)?;
        partition
            .entry(find(&mut parent, place))
            .or_default()
            .push(place);
    }
    Ok(partition.into_values().collect())
}

pub fn solve(problem: &Problem, timeout: Duration, max_work: usize) -> Outcome {
    let deadline = Instant::now() + timeout;
    let mut work = Work {
        deadline,
        remaining: max_work,
    };
    let unknown = |reason: &str| Outcome::unknown("grouped-excess", reason, 0);
    if problem.validate().is_err() {
        return unknown("invalid problem");
    }
    let Ok(groups) = groups(problem, &mut work) else {
        return unknown("group discovery resource limit");
    };
    let mut certificate = Certificate {
        kind: "grouped-excess-v1".into(),
        thresholds: vec![1; groups.len()],
        groups,
        target_row: 0,
        sign: 1,
    };
    let budget = match invariant(problem, &certificate, &mut work) {
        Ok(budget) => budget,
        Err(error) => return unknown(&error.to_string()),
    };
    for (row, constraint) in problem.target.iter().enumerate() {
        for sign in if constraint.equality {
            &[1, -1][..]
        } else {
            &[1][..]
        } {
            certificate.target_row = row;
            certificate.sign = *sign;
            match target_bound(problem, &certificate, &budget, &mut work) {
                Ok((upper, required)) if upper < required => {
                    let Ok(proof) = serde_json::to_value(&certificate) else {
                        return unknown("certificate serialization failed");
                    };
                    if let Err(error) = verify(problem, &proof, deadline) {
                        return unknown(&error.to_string());
                    }
                    let mut out = unknown("nonincreasing grouped excess excludes target");
                    out.verdict = "unreachable";
                    out.proof = Some(proof);
                    return out;
                }
                Ok(_) => {}
                Err(error) => return unknown(&error.to_string()),
            }
        }
    }
    unknown("grouped excess bound does not exclude target")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};

    fn transfer() -> Problem {
        Problem {
            places: vec!["source".into(), "destination".into(), "reserve".into()],
            initial: vec![2, 0, 1],
            transitions: vec![
                Transition {
                    name: "release".into(),
                    pre: vec![(2, 1)],
                    post: vec![(1, 1)],
                },
                Transition {
                    name: "move".into(),
                    pre: vec![(0, 2), (1, 1)],
                    post: vec![(1, 2)],
                },
            ],
            target: vec![Constraint {
                coefficients: vec![0, 1, 0],
                bound: 3,
                equality: false,
            }],
        }
    }

    #[test]
    fn release_and_double_token_transfer_are_certified() {
        let p = transfer();
        let out = solve(&p, Duration::from_secs(1), 1000);
        assert_eq!(out.verdict, "unreachable", "{}", out.reason);
        verify(
            &p,
            out.proof.as_ref().unwrap(),
            Instant::now() + Duration::from_secs(1),
        )
        .unwrap();
    }

    #[test]
    fn reachable_target_and_increasing_transition_are_not_refuted() {
        let mut p = transfer();
        p.target[0].bound = 2;
        assert_eq!(solve(&p, Duration::from_secs(1), 1000).verdict, "unknown");
        p.target[0].bound = 3;
        p.transitions[1].pre[0].1 = 1;
        assert_eq!(solve(&p, Duration::from_secs(1), 1000).verdict, "unknown");
    }

    #[test]
    fn change_formula_bounds_all_small_firings() {
        for pre in 0..5 {
            for post in 0..5 {
                for threshold in 0..5 {
                    let upper = upper_change(&pre.into(), &post.into(), threshold);
                    for marking in pre..10 {
                        let before = positive(BigInt::from(marking) - threshold);
                        let after = positive(BigInt::from(marking - pre + post) - threshold);
                        assert!(after - before <= upper);
                    }
                }
            }
        }
    }

    #[test]
    fn corrupted_partition_and_invalid_sign_are_rejected() {
        let p = transfer();
        let out = solve(&p, Duration::from_secs(1), 1000);
        let original: Certificate = serde_json::from_value(out.proof.unwrap()).unwrap();
        let mut changes = vec![];
        let mut duplicate = original.clone();
        let place = duplicate.groups[0][0];
        duplicate.groups[0].push(place);
        changes.push(duplicate);
        let mut missing = original.clone();
        missing.groups[0].pop();
        changes.push(missing);
        let mut sign = original.clone();
        sign.sign = -1;
        changes.push(sign);
        let mut threshold = original;
        threshold.thresholds.pop();
        changes.push(threshold);
        for certificate in changes {
            assert!(
                verify(
                    &p,
                    &serde_json::to_value(certificate).unwrap(),
                    Instant::now() + Duration::from_secs(1)
                )
                .is_err()
            );
        }
    }

    #[test]
    fn equality_can_be_refuted_on_either_side_and_limits_are_unknown() {
        let mut p = transfer();
        p.target[0].coefficients = vec![0, -1, 0];
        p.target[0].bound = -3;
        p.target[0].equality = true;
        assert_eq!(
            solve(&p, Duration::from_secs(1), 1000).verdict,
            "unreachable"
        );
        assert_eq!(solve(&p, Duration::ZERO, 1000).verdict, "unknown");
        assert_eq!(solve(&p, Duration::from_secs(1), 0).verdict, "unknown");
    }
}
