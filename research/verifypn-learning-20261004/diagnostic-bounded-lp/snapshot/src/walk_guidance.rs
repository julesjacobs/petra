use super::{Index, Random, within};
use std::time::Instant;

pub(super) struct Guidance {
    users: Vec<Vec<(usize, i64)>>,
    values: Vec<i128>,
    delta: Vec<i128>,
}

impl Guidance {
    pub(super) fn new(
        index: &Index,
        initial: &[u64],
        deadline: Instant,
    ) -> Result<Self, &'static str> {
        let mut users = vec![Vec::new(); initial.len()];
        for (row, target) in index.targets.iter().enumerate() {
            for &(place, coefficient) in &target.terms {
                within(deadline)?;
                users[place].push((row, coefficient));
            }
        }
        let mut result = Self {
            users,
            values: vec![0; index.targets.len()],
            delta: vec![0; index.targets.len()],
        };
        result.reset(index, initial, deadline)?;
        Ok(result)
    }

    pub(super) fn reset(
        &mut self,
        index: &Index,
        initial: &[u64],
        deadline: Instant,
    ) -> Result<(), &'static str> {
        self.values.fill(0);
        for (value, target) in self.values.iter_mut().zip(&index.targets) {
            for &(place, coefficient) in &target.terms {
                within(deadline)?;
                *value = value
                    .checked_add(i128::from(coefficient) * i128::from(initial[place]))
                    .ok_or("target arithmetic overflow")?;
            }
        }
        Ok(())
    }

    fn effects(&mut self, index: &Index, t: usize, deadline: Instant) -> Result<(), &'static str> {
        self.delta.fill(0);
        for &(place, effect) in &index.effects[t] {
            for &(row, coefficient) in &self.users[place] {
                within(deadline)?;
                let change = effect
                    .checked_mul(i128::from(coefficient))
                    .ok_or("target arithmetic overflow")?;
                self.delta[row] = self.delta[row]
                    .checked_add(change)
                    .ok_or("target arithmetic overflow")?;
            }
        }
        Ok(())
    }

    pub(super) fn fired(
        &mut self,
        index: &Index,
        t: usize,
        deadline: Instant,
    ) -> Result<(), &'static str> {
        self.effects(index, t, deadline)?;
        for (value, delta) in self.values.iter_mut().zip(&self.delta) {
            within(deadline)?;
            *value = value
                .checked_add(*delta)
                .ok_or("target arithmetic overflow")?;
        }
        Ok(())
    }

    pub(super) fn accepts(&self, index: &Index, deadline: Instant) -> Result<bool, &'static str> {
        for (&value, target) in self.values.iter().zip(&index.targets) {
            within(deadline)?;
            let bound = i128::from(target.bound);
            if (target.equality && value != bound) || (!target.equality && value < bound) {
                return Ok(false);
            }
        }
        Ok(true)
    }

    fn score(&mut self, index: &Index, t: usize, deadline: Instant) -> Result<f64, &'static str> {
        self.effects(index, t, deadline)?;
        let mut score = 0.0;
        for ((&value, &delta), target) in self.values.iter().zip(&self.delta).zip(&index.targets) {
            within(deadline)?;
            let value = value
                .checked_add(delta)
                .ok_or("target arithmetic overflow")?;
            let bound = i128::from(target.bound);
            if target.equality || value < bound {
                score += value.abs_diff(bound) as f64;
            }
        }
        Ok(score)
    }

    pub(super) fn select(
        &mut self,
        index: &Index,
        enabled: &[usize],
        random: &mut Random,
        deadline: Instant,
    ) -> Result<usize, &'static str> {
        let mut chosen = enabled[random.index(enabled.len())];
        if random.index(5) == 0 {
            return Ok(chosen);
        }
        let mut best = self.score(index, chosen, deadline)?;
        let mut ties = 1;
        for _ in 1..8 {
            within(deadline)?;
            let candidate = enabled[random.index(enabled.len())];
            let score = self.score(index, candidate, deadline)?;
            if score < best {
                chosen = candidate;
                best = score;
                ties = 1;
            } else if score == best {
                ties += 1;
                if random.index(ties) == 0 {
                    chosen = candidate;
                }
            }
        }
        Ok(chosen)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        model::{Constraint, Problem, Transition},
        walk::State,
    };
    use std::time::Duration;

    #[test]
    fn incremental_values_and_candidate_scores_match_original_weighted_firings() {
        let p = Problem {
            places: vec!["a".into(), "b".into(), "read".into()],
            initial: vec![4, 2, 1],
            transitions: vec![
                Transition {
                    name: "forward".into(),
                    pre: vec![(0, 2), (2, 1)],
                    post: vec![(1, 3), (2, 1)],
                },
                Transition {
                    name: "back".into(),
                    pre: vec![(1, 2)],
                    post: vec![(0, 1)],
                },
                Transition {
                    name: "source".into(),
                    pre: vec![],
                    post: vec![(0, 2)],
                },
                Transition {
                    name: "sink".into(),
                    pre: vec![(0, 1)],
                    post: vec![],
                },
                Transition {
                    name: "stutter".into(),
                    pre: vec![(2, 1)],
                    post: vec![(2, 1)],
                },
            ],
            target: vec![
                Constraint {
                    coefficients: vec![-3, 2, 1],
                    bound: 7,
                    equality: false,
                },
                Constraint {
                    coefficients: vec![2, -1, 0],
                    bound: 4,
                    equality: true,
                },
                Constraint {
                    coefficients: vec![0, 0, i64::MIN],
                    bound: i64::MIN,
                    equality: true,
                },
            ],
        };
        let deadline = Instant::now() + Duration::from_secs(10);
        let index = Index::new(&p, deadline).unwrap();
        for seed in 0..16 {
            let mut random = Random(seed);
            let mut state = State::new(&p, &index, deadline).unwrap();
            let mut guidance = Guidance::new(&index, &p.initial, deadline).unwrap();
            for step in 0..100 {
                if step % 17 == 16 {
                    state.reset(&p, &index, deadline).unwrap();
                    guidance.reset(&index, &p.initial, deadline).unwrap();
                }
                for &t in &state.enabled {
                    let next = p.fire(&state.marking, t).unwrap().unwrap();
                    let expected: f64 = p
                        .target
                        .iter()
                        .map(|c| {
                            let value: i128 = c
                                .coefficients
                                .iter()
                                .zip(&next)
                                .map(|(&a, &m)| i128::from(a) * i128::from(m))
                                .sum();
                            let bound = i128::from(c.bound);
                            if c.equality || value < bound {
                                value.abs_diff(bound) as f64
                            } else {
                                0.0
                            }
                        })
                        .sum();
                    assert_eq!(guidance.score(&index, t, deadline).unwrap(), expected);
                }
                let t = guidance
                    .select(&index, &state.enabled, &mut random, deadline)
                    .unwrap();
                state.fire(&index, t, deadline).unwrap();
                guidance.fired(&index, t, deadline).unwrap();
                for (value, c) in guidance.values.iter().zip(&p.target) {
                    let expected: i128 = c
                        .coefficients
                        .iter()
                        .zip(&state.marking)
                        .map(|(&a, &m)| i128::from(a) * i128::from(m))
                        .sum();
                    assert_eq!(*value, expected);
                }
                assert_eq!(
                    guidance.accepts(&index, deadline).unwrap(),
                    p.accepts(&state.marking).unwrap()
                );
            }
        }
    }
}
