//! Checked uniform-buffer agglomeration with bounded original-trace recipes.
use crate::model::{Constraint, Problem, Transition};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::{
    collections::{BTreeMap, BTreeSet},
    time::Instant,
};

const MAX_ARCS: usize = 20_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Orientation {
    Eager,
    Delayed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Step {
    pub place: usize,
    pub orientation: Orientation,
}

#[derive(Debug)]
enum Recipe {
    Original(usize),
    Concat(usize, usize),
}

#[derive(Debug)]
pub struct Prepared {
    pub problem: Problem,
    pub places: Vec<usize>,
    pub transitions: Vec<usize>,
    pub steps: Vec<Step>,
    recipes: Vec<Recipe>,
}

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self, work: usize) -> Result<()> {
        ensure!(
            Instant::now() < self.deadline,
            "buffer agglomeration deadline"
        );
        self.remaining = self
            .remaining
            .checked_sub(work)
            .context("buffer agglomeration work limit")?;
        Ok(())
    }
    fn tree(&mut self, size: usize) -> Result<()> {
        self.tick(1 + usize::BITS as usize - size.leading_zeros() as usize)
    }
}

fn validate(p: &Problem, budget: &mut Budget) -> Result<Vec<bool>> {
    let n = p.places.len();
    budget.tick(n.saturating_mul(2).saturating_add(1))?;
    ensure!(p.initial.len() == n, "initial marking dimension mismatch");
    let mut support = vec![false; n];
    for row in &p.target {
        budget.tick(1)?;
        ensure!(row.coefficients.len() == n, "target dimension mismatch");
        for (place, &a) in row.coefficients.iter().enumerate() {
            budget.tick(1)?;
            support[place] |= a != 0;
        }
    }
    let mut seen = vec![0usize; n];
    let mut generation = 0usize;
    let mut arcs = 0usize;
    for t in &p.transitions {
        budget.tick(1)?;
        for side in [&t.pre, &t.post] {
            generation = generation.checked_add(1).context("too many arc lists")?;
            arcs = arcs.checked_add(side.len()).context("arc count overflow")?;
            ensure!(arcs <= MAX_ARCS, "buffer agglomeration arc limit");
            for &(place, weight) in side {
                budget.tick(1)?;
                ensure!(place < n && weight > 0, "invalid arc");
                ensure!(seen[place] != generation, "repeated arc");
                seen[place] = generation;
            }
        }
    }
    Ok(support)
}

struct State {
    active_places: Vec<bool>,
    support: Vec<bool>,
    transitions: Vec<Option<Transition>>,
    producers: Vec<BTreeMap<usize, u64>>,
    consumers: Vec<BTreeMap<usize, u64>>,
    pending: BTreeSet<usize>,
    recipes: Vec<Recipe>,
    steps: Vec<Step>,
    total_arcs: usize,
    transition_limit: usize,
}

impl State {
    fn new(p: &Problem, budget: &mut Budget) -> Result<Self> {
        let support = validate(p, budget)?;
        let n = p.places.len();
        let transition_limit = p.transitions.len().saturating_mul(4).clamp(1024, 1_000_000);
        ensure!(
            p.transitions.len() <= transition_limit,
            "buffer agglomeration transition limit"
        );
        budget.tick(n.saturating_mul(4).saturating_add(p.transitions.len()))?;
        let mut state = Self {
            active_places: vec![true; n],
            support,
            transitions: Vec::new(),
            producers: vec![BTreeMap::new(); n],
            consumers: vec![BTreeMap::new(); n],
            pending: BTreeSet::new(),
            recipes: Vec::new(),
            steps: Vec::new(),
            total_arcs: 0,
            transition_limit,
        };
        for (id, t) in p.transitions.iter().enumerate() {
            budget.tick(
                t.name
                    .len()
                    .saturating_add(t.pre.len())
                    .saturating_add(t.post.len())
                    .saturating_add(1),
            )?;
            state.total_arcs = state
                .total_arcs
                .checked_add(t.pre.len())
                .and_then(|v| v.checked_add(t.post.len()))
                .context("arc count overflow")?;
            state.index(id, t, true, budget)?;
            state.transitions.push(Some(t.clone()));
            state.recipes.push(Recipe::Original(id));
        }
        for (place, &initial) in p.initial.iter().enumerate() {
            budget.tick(1)?;
            if initial == 0 && !state.support[place] {
                budget.tree(state.pending.len())?;
                state.pending.insert(place);
            }
        }
        Ok(state)
    }

    fn index(
        &mut self,
        id: usize,
        t: &Transition,
        insert: bool,
        budget: &mut Budget,
    ) -> Result<()> {
        for (arcs, incidence) in [
            (&t.pre, &mut self.consumers),
            (&t.post, &mut self.producers),
        ] {
            for &(place, weight) in arcs {
                budget.tree(incidence[place].len())?;
                if insert {
                    incidence[place].insert(id, weight);
                } else {
                    ensure!(
                        incidence[place].remove(&id) == Some(weight),
                        "incidence mismatch"
                    );
                }
                budget.tree(self.pending.len())?;
                self.pending.insert(place);
            }
        }
        Ok(())
    }

    fn eligible(&self, p: &Problem, place: usize, budget: &mut Budget) -> Result<(bool, bool)> {
        budget.tick(1)?;
        ensure!(place < self.active_places.len(), "invalid buffer place");
        if !self.active_places[place] || self.support[place] || p.initial[place] != 0 {
            return Ok((false, false));
        }
        let producers = &self.producers[place];
        let consumers = &self.consumers[place];
        if producers.is_empty() || consumers.is_empty() {
            return Ok((false, false));
        }
        let weight = *producers.first_key_value().context("missing producer")?.1;
        let mut eager = true;
        let mut delayed = true;
        for (&id, &a) in producers {
            budget.tree(consumers.len())?;
            if a != weight || consumers.contains_key(&id) {
                return Ok((false, false));
            }
            let t = self.transitions[id].as_ref().context("inactive producer")?;
            delayed &= t.post.len() == 1;
            for &(other, _) in &t.pre {
                budget.tick(1)?;
                delayed &= !self.support[other];
            }
        }
        for (&id, &a) in consumers {
            budget.tick(1)?;
            if a != weight {
                return Ok((false, false));
            }
            let t = self.transitions[id].as_ref().context("inactive consumer")?;
            eager &= t.pre.len() == 1;
            for &(other, _) in &t.post {
                budget.tick(1)?;
                eager &= !self.support[other];
            }
        }
        Ok((eager, delayed))
    }

    fn apply(&mut self, p: &Problem, step: Step, budget: &mut Budget) -> Result<()> {
        let (eager, delayed) = self.eligible(p, step.place, budget)?;
        ensure!(
            match step.orientation {
                Orientation::Eager => eager,
                Orientation::Delayed => delayed,
            },
            "ineligible buffer agglomeration step"
        );
        let producer_count = self.producers[step.place].len();
        let consumer_count = self.consumers[step.place].len();
        let count = producer_count
            .checked_mul(consumer_count)
            .context("macro count overflow")?;
        ensure!(
            self.transitions
                .len()
                .checked_add(count)
                .is_some_and(|n| n <= self.transition_limit),
            "buffer agglomeration transition limit"
        );
        budget.tick(
            producer_count
                .saturating_add(consumer_count)
                .saturating_add(count),
        )?;
        let producers: Vec<_> = self.producers[step.place].keys().copied().collect();
        let consumers: Vec<_> = self.consumers[step.place].keys().copied().collect();
        let mut macros = Vec::new();
        let mut total_arcs = self.total_arcs;
        for &producer in &producers {
            for &consumer in &consumers {
                budget.tick(1)?;
                let f = self.transitions[producer]
                    .as_ref()
                    .context("inactive producer")?;
                let c = self.transitions[consumer]
                    .as_ref()
                    .context("inactive consumer")?;
                let (pre, post) = match step.orientation {
                    Orientation::Eager => {
                        budget.tick(f.pre.len())?;
                        (f.pre.clone(), merge(&f.post, &c.post, step.place, budget)?)
                    }
                    Orientation::Delayed => {
                        budget.tick(c.post.len())?;
                        (merge(&f.pre, &c.pre, step.place, budget)?, c.post.clone())
                    }
                };
                total_arcs = total_arcs
                    .checked_add(pre.len())
                    .and_then(|n| n.checked_add(post.len()))
                    .context("arc count overflow")?;
                ensure!(total_arcs <= MAX_ARCS, "buffer agglomeration arc limit");
                let id = self.transitions.len() + macros.len();
                budget.tick(64)?;
                macros.push((
                    Transition {
                        name: format!("buffer-macro-{id}"),
                        pre,
                        post,
                    },
                    Recipe::Concat(producer, consumer),
                ));
            }
        }
        for id in producers.into_iter().chain(consumers) {
            budget.tick(1)?;
            let t = self.transitions[id]
                .take()
                .context("transition removed twice")?;
            self.index(id, &t, false, budget)?;
        }
        self.active_places[step.place] = false;
        for (t, recipe) in macros {
            budget.tick(1)?;
            let id = self.transitions.len();
            self.index(id, &t, true, budget)?;
            self.transitions.push(Some(t));
            self.recipes.push(recipe);
        }
        self.total_arcs = total_arcs;
        self.steps.push(step);
        budget.tick(0)
    }

    fn finish(self, p: &Problem, budget: &mut Budget) -> Result<Prepared> {
        budget.tick(p.places.len())?;
        let mut map = vec![None; p.places.len()];
        let mut places = Vec::new();
        let mut problem = Problem {
            places: vec![],
            initial: vec![],
            transitions: vec![],
            target: vec![],
        };
        for (place, &active) in self.active_places.iter().enumerate() {
            budget.tick(1)?;
            if active {
                budget.tick(p.places[place].len().saturating_add(1))?;
                map[place] = Some(places.len());
                places.push(place);
                problem.places.push(p.places[place].clone());
                problem.initial.push(p.initial[place]);
            }
        }
        let mut transitions = Vec::new();
        for (id, t) in self.transitions.into_iter().enumerate() {
            budget.tick(1)?;
            if let Some(mut t) = t {
                for arcs in [&mut t.pre, &mut t.post] {
                    for (place, _) in arcs {
                        budget.tick(1)?;
                        *place = map[*place].context("remaining arc on removed place")?;
                    }
                }
                transitions.push(id);
                problem.transitions.push(t);
            }
        }
        for row in &p.target {
            budget.tick(1)?;
            let mut coefficients = Vec::new();
            for &place in &places {
                budget.tick(1)?;
                coefficients.push(row.coefficients[place]);
            }
            problem.target.push(Constraint {
                coefficients,
                bound: row.bound,
                equality: row.equality,
            });
        }
        budget.tick(0)?;
        Ok(Prepared {
            problem,
            places,
            transitions,
            steps: self.steps,
            recipes: self.recipes,
        })
    }
}

fn merge(
    first: &[(usize, u64)],
    second: &[(usize, u64)],
    removed: usize,
    budget: &mut Budget,
) -> Result<Vec<(usize, u64)>> {
    let mut arcs = BTreeMap::<usize, u64>::new();
    for &(place, weight) in first.iter().chain(second) {
        budget.tree(arcs.len())?;
        if place == removed {
            continue;
        }
        let sum = arcs.entry(place).or_default();
        *sum = sum
            .checked_add(weight)
            .context("macro arc weight overflow")?;
    }
    budget.tick(arcs.len())?;
    Ok(arcs.into_iter().collect())
}

pub fn prepare(p: &Problem, deadline: Instant, max_work: usize) -> Result<Option<Prepared>> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    let mut state = State::new(p, &mut budget)?;
    while !state.pending.is_empty() {
        budget.tree(state.pending.len())?;
        let place = state
            .pending
            .pop_first()
            .context("missing worklist place")?;
        let (eager, delayed) = state.eligible(p, place, &mut budget)?;
        if eager || delayed {
            let producers = state.producers[place].len();
            let consumers = state.consumers[place].len();
            let Some(macros) = producers.checked_mul(consumers) else {
                continue;
            };
            if macros > producers.saturating_add(consumers)
                || state
                    .transitions
                    .len()
                    .checked_add(macros)
                    .is_none_or(|n| n > state.transition_limit)
            {
                continue;
            }
            let orientation = if eager {
                Orientation::Eager
            } else {
                Orientation::Delayed
            };
            state.apply(p, Step { place, orientation }, &mut budget)?;
        }
    }
    budget.tick(0)?;
    if state.steps.is_empty() {
        Ok(None)
    } else {
        Ok(Some(state.finish(p, &mut budget)?))
    }
}

/// Reconstruct every step; the caller must check the inner proof on the returned net.
pub fn verify_reduction<'a>(
    p: &Problem,
    proof: &'a Value,
    deadline: Instant,
    max_work: usize,
) -> Result<(Prepared, &'a Value)> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    budget.tick(1)?;
    let object = proof.as_object().context("buffer proof is not an object")?;
    ensure!(
        object.len() == 3
            && ["kind", "steps", "inner"]
                .iter()
                .all(|key| object.contains_key(*key)),
        "invalid buffer proof fields"
    );
    ensure!(
        proof["kind"] == "buffer-agglomeration-v1",
        "wrong buffer proof kind"
    );
    let inner = proof
        .get("inner")
        .filter(|v| v.is_object())
        .context("inner proof is not an object")?;
    let values = proof["steps"]
        .as_array()
        .context("buffer steps are not an array")?;
    ensure!(
        !values.is_empty() && values.len() <= p.places.len(),
        "invalid number of buffer steps"
    );
    budget.tick(values.len())?;
    let mut state = State::new(p, &mut budget)?;
    for value in values {
        budget.tick(1)?;
        let object = value.as_object().context("buffer step is not an object")?;
        ensure!(
            object.len() == 2 && object.contains_key("place") && object.contains_key("orientation"),
            "invalid buffer step fields"
        );
        let place = usize::try_from(value["place"].as_u64().context("invalid buffer place")?)?;
        let orientation = match value["orientation"].as_str() {
            Some("eager") => Orientation::Eager,
            Some("delayed") => Orientation::Delayed,
            _ => anyhow::bail!("invalid buffer orientation"),
        };
        state.apply(p, Step { place, orientation }, &mut budget)?;
    }
    Ok((state.finish(p, &mut budget)?, inner))
}

impl Prepared {
    pub fn wrap_proof(&self, inner: Value, deadline: Instant, max_work: usize) -> Result<Value> {
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        budget.tick(self.steps.len().saturating_add(1))?;
        ensure!(
            inner.is_object() && !self.steps.is_empty(),
            "invalid buffer proof wrapper"
        );
        let mut steps = Vec::new();
        for step in &self.steps {
            budget.tick(1)?;
            let mut object = Map::new();
            object.insert("place".into(), Value::from(step.place));
            object.insert(
                "orientation".into(),
                Value::from(match step.orientation {
                    Orientation::Eager => "eager",
                    Orientation::Delayed => "delayed",
                }),
            );
            steps.push(Value::Object(object));
        }
        let mut object = Map::new();
        object.insert("kind".into(), Value::from("buffer-agglomeration-v1"));
        object.insert("steps".into(), Value::Array(steps));
        object.insert("inner".into(), inner);
        budget.tick(0)?;
        Ok(Value::Object(object))
    }

    pub fn lift_witness(
        &self,
        original: &Problem,
        trace: &[usize],
        deadline: Instant,
        max_work: usize,
    ) -> Result<(Vec<usize>, Vec<u64>)> {
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        validate(original, &mut budget)?;
        budget.tick(original.initial.len())?;
        let mut marking = original.initial.clone();
        let mut lifted = Vec::new();
        let mut stack = Vec::new();
        for &reduced in trace {
            budget.tick(1)?;
            stack.push(
                *self
                    .transitions
                    .get(reduced)
                    .context("invalid reduced witness transition")?,
            );
            while let Some(id) = stack.pop() {
                budget.tick(1)?;
                match *self.recipes.get(id).context("invalid recipe ID")? {
                    Recipe::Concat(first, second) => {
                        ensure!(first < id && second < id, "cyclic buffer recipe");
                        budget.tick(2)?;
                        stack.push(second);
                        stack.push(first);
                    }
                    Recipe::Original(id) => {
                        let t = original
                            .transitions
                            .get(id)
                            .context("invalid original witness transition")?;
                        for &(place, weight) in &t.pre {
                            budget.tick(1)?;
                            ensure!(marking[place] >= weight, "lifted witness disabled");
                        }
                        for &(place, weight) in &t.pre {
                            budget.tick(1)?;
                            marking[place] -= weight;
                        }
                        for &(place, weight) in &t.post {
                            budget.tick(1)?;
                            marking[place] = marking[place]
                                .checked_add(weight)
                                .context("lifted counter overflow")?;
                        }
                        budget.tick(1)?;
                        lifted.push(id);
                    }
                }
            }
        }
        for row in &original.target {
            budget.tick(1)?;
            let mut value = 0i128;
            for (&a, &tokens) in row.coefficients.iter().zip(&marking) {
                budget.tick(1)?;
                value = value
                    .checked_add(i128::from(a) * i128::from(tokens))
                    .context("lifted target overflow")?;
            }
            ensure!(
                if row.equality {
                    value == i128::from(row.bound)
                } else {
                    value >= i128::from(row.bound)
                },
                "lifted witness misses target"
            );
        }
        budget.tick(0)?;
        Ok((lifted, marking))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::{
        collections::{HashSet, VecDeque},
        time::Duration,
    };

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(20)
    }
    fn budget() -> Budget {
        Budget {
            deadline: deadline(),
            remaining: 10_000_000,
        }
    }
    fn t(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
        Transition {
            name: "t".into(),
            pre: pre.to_vec(),
            post: post.to_vec(),
        }
    }
    fn p(initial: &[u64], transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
        Problem {
            places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
            initial: initial.to_vec(),
            transitions,
            target,
        }
    }
    fn eq(coefficients: &[i64], bound: i64) -> Constraint {
        Constraint {
            coefficients: coefficients.to_vec(),
            bound,
            equality: true,
        }
    }
    fn reduced(p: &Problem) -> Prepared {
        prepare(p, deadline(), 10_000_000).unwrap().unwrap()
    }
    fn proof(steps: Value) -> Value {
        json!({"kind":"buffer-agglomeration-v1","steps":steps,"inner":{}})
    }
    fn eager() -> Problem {
        p(
            &[0, 2, 0],
            vec![
                t(&[(1, 2)], &[(0, 2), (1, 1)]),
                t(&[(0, 2)], &[(1, 1)]),
                t(&[], &[(2, 1)]),
            ],
            vec![eq(&[0, 0, 1], 1)],
        )
    }

    #[test]
    fn eager_weighted_cycle_preserves_shared_arcs_and_original_ids() {
        let p = eager();
        let q = reduced(&p);
        assert_eq!(
            q.steps,
            [Step {
                place: 0,
                orientation: Orientation::Eager
            }]
        );
        assert_eq!(q.places, [1, 2]);
        assert_eq!(q.transitions, [2, 3]);
        assert_eq!(q.problem.transitions[1].pre, [(0, 2)]);
        assert_eq!(q.problem.transitions[1].post, [(0, 2)]);
        assert_eq!(q.problem.transitions[1].name, "buffer-macro-3");
        let (trace, marking) = q.lift_witness(&p, &[1, 0], deadline(), 10_000).unwrap();
        assert_eq!(trace, [0, 1, 2]);
        assert_eq!(p.check_witness(&trace).unwrap(), marking);
        assert_eq!(marking, [0, 2, 1]);
        let wrapped = q.wrap_proof(json!({}), deadline(), 1000).unwrap();
        let (checked, _) = verify_reduction(&p, &wrapped, deadline(), 10_000).unwrap();
        assert_eq!(
            serde_json::to_value(&q.problem).unwrap(),
            serde_json::to_value(&checked.problem).unwrap()
        );
    }

    #[test]
    fn delayed_merges_shared_inputs_and_preserves_target_selfloop() {
        let p = p(
            &[0, 5, 1],
            vec![
                t(&[(1, 2)], &[(0, 2)]),
                t(&[(2, 1), (0, 2), (1, 3)], &[(2, 1)]),
            ],
            vec![eq(&[0, 0, 1], 1)],
        );
        let q = reduced(&p);
        assert_eq!(
            q.steps,
            [Step {
                place: 0,
                orientation: Orientation::Delayed
            }]
        );
        assert_eq!(q.problem.transitions[0].pre, [(0, 5), (1, 1)]);
        assert_eq!(q.problem.transitions[0].post, [(1, 1)]);
        assert_eq!(
            q.lift_witness(&p, &[0], deadline(), 10_000).unwrap(),
            (vec![0, 1], vec![0, 0, 1])
        );
        assert!(q.lift_witness(&p, &[0, 0], deadline(), 10_000).is_err());
    }

    #[test]
    fn pair_order_no_dedup_and_eager_precedence_are_deterministic() {
        let p = p(
            &[0, 1],
            vec![
                t(&[(1, 1)], &[(0, 1)]),
                t(&[(1, 1)], &[(0, 1)]),
                t(&[(0, 1)], &[(1, 1)]),
                t(&[(0, 1)], &[(1, 1)]),
            ],
            vec![],
        );
        let q = reduced(&p);
        assert_eq!(
            q.steps,
            [Step {
                place: 0,
                orientation: Orientation::Eager
            }]
        );
        assert_eq!(q.transitions, [4, 5, 6, 7]);
        for (index, expected) in [[0, 2], [0, 3], [1, 2], [1, 3]].into_iter().enumerate() {
            assert_eq!(
                q.lift_witness(&p, &[index], deadline(), 10_000).unwrap().0,
                expected
            );
        }
    }

    #[test]
    fn chained_steps_use_recipe_dag_and_project_original_place_order() {
        let p = p(
            &[0, 0, 1, 0],
            vec![
                t(&[(2, 1)], &[(0, 1)]),
                t(&[(0, 1)], &[(1, 1)]),
                t(&[(1, 1)], &[(3, 1)]),
            ],
            vec![eq(&[0, 0, 0, 1], 1)],
        );
        let q = reduced(&p);
        assert_eq!(
            q.steps,
            [
                Step {
                    place: 0,
                    orientation: Orientation::Eager
                },
                Step {
                    place: 1,
                    orientation: Orientation::Delayed
                }
            ]
        );
        assert_eq!(q.places, [2, 3]);
        assert_eq!(q.transitions, [4]);
        assert_eq!(q.recipes.len(), 5);
        assert_eq!(
            q.lift_witness(&p, &[0], deadline(), 10_000).unwrap().0,
            [0, 1, 2]
        );
        let alternate =
            proof(json!([{"place":1,"orientation":"delayed"},{"place":0,"orientation":"delayed"}]));
        let (other, _) = verify_reduction(&p, &alternate, deadline(), 10_000).unwrap();
        assert_eq!(
            other.lift_witness(&p, &[0], deadline(), 10_000).unwrap().0,
            [0, 1, 2]
        );
    }

    #[test]
    fn target_support_initial_marking_overlap_and_nonuniform_weights_reject() {
        let cases = [
            p(&[1, 0], vec![t(&[], &[(0, 1)]), t(&[(0, 1)], &[])], vec![]),
            p(
                &[0, 0],
                vec![t(&[], &[(0, 1)]), t(&[(0, 1)], &[])],
                vec![eq(&[1, 0], 0)],
            ),
            p(&[0, 0], vec![t(&[], &[(0, 1)]), t(&[(0, 2)], &[])], vec![]),
            p(&[0, 0], vec![t(&[(0, 1)], &[(0, 1)])], vec![]),
            p(
                &[0, 1],
                vec![t(&[(1, 1)], &[(0, 1)]), t(&[(0, 1)], &[(1, 1)])],
                vec![eq(&[0, 1], 1)],
            ),
            p(&[0, 1], vec![t(&[(1, 1)], &[(0, 1)])], vec![]),
        ];
        for p in cases {
            assert!(prepare(&p, deadline(), 10_000).unwrap().is_none());
            for orientation in ["eager", "delayed"] {
                assert!(
                    verify_reduction(
                        &p,
                        &proof(json!([{"place":0,"orientation":orientation}])),
                        deadline(),
                        10_000
                    )
                    .is_err()
                );
            }
        }
        let p = p(
            &[0, 1, 1],
            vec![t(&[(1, 1)], &[(0, 1), (2, 1)]), t(&[(0, 1), (2, 1)], &[])],
            vec![eq(&[0, 0, 1], 1)],
        );
        assert!(prepare(&p, deadline(), 10_000).unwrap().is_none());
    }

    #[test]
    fn rejects_malformed_or_forged_proof_sequences() {
        let p = eager();
        for invalid in [
            Value::Null,
            proof(json!([])),
            proof(json!(null)),
            proof(json!([{"place":0,"orientation":"Eager"}])),
            proof(json!([{"place":0.0,"orientation":"eager"}])),
            proof(json!([{"place":true,"orientation":"eager"}])),
            proof(json!([{"place":-1,"orientation":"eager"}])),
            proof(json!([{"place":99,"orientation":"eager"}])),
            proof(json!([{"place":0,"orientation":"eager","arcs":[]}])),
            proof(json!([{"place":0,"orientation":"eager"},{"place":0,"orientation":"eager"}])),
            proof(json!([{"place":0,"orientation":"delayed"}])),
            json!({"kind":"buffer-agglomeration-v1","steps":[{"place":0,"orientation":"eager"}],"inner":[],}),
            json!({"kind":"buffer-agglomeration-v1","steps":[{"place":0,"orientation":"eager"}],"inner":{},"recipes":[]}),
        ] {
            assert!(
                verify_reduction(&p, &invalid, deadline(), 10_000).is_err(),
                "accepted {invalid}"
            );
        }
    }

    #[test]
    fn arc_overflow_transition_growth_and_work_limits_fail_without_mutation() {
        let net = p(
            &[0, 1],
            vec![
                t(&[(1, 1)], &[(0, 1), (1, u64::MAX)]),
                t(&[(0, 1)], &[(1, 1)]),
            ],
            vec![],
        );
        assert!(prepare(&net, deadline(), 10_000).is_err());
        let mut transitions = vec![t(&[], &[(0, 1)]); 40];
        transitions.extend(vec![t(&[(0, 1)], &[]); 40]);
        let net = p(&[0], transitions, vec![]);
        let before = serde_json::to_value(&net).unwrap();
        assert!(prepare(&net, deadline(), 1_000_000).unwrap().is_none());
        let proof = json!({"kind":"buffer-agglomeration-v1",
            "steps":[{"place":0,"orientation":"eager"}],"inner":{}});
        assert!(verify_reduction(&net, &proof, deadline(), 1_000_000).is_err());
        assert_eq!(before, serde_json::to_value(&net).unwrap());
        let net = eager();
        let mut state = State::new(&net, &mut budget()).unwrap();
        state.total_arcs = MAX_ARCS;
        assert!(
            state
                .apply(
                    &net,
                    Step {
                        place: 0,
                        orientation: Orientation::Eager
                    },
                    &mut budget()
                )
                .is_err()
        );
        assert!(state.steps.is_empty());
        assert!(state.active_places[0]);
        assert!(state.transitions.iter().all(Option::is_some));
    }

    #[test]
    fn discovery_keeps_safe_reductions_when_another_buffer_would_expand() {
        let mut transitions = vec![t(&[], &[(0, 1)]), t(&[(0, 1)], &[])];
        transitions.extend(vec![t(&[], &[(1, 1)]); 40]);
        transitions.extend(vec![t(&[(1, 1)], &[]); 40]);
        let net = p(&[0, 0], transitions, vec![]);
        let q = reduced(&net);
        assert_eq!(
            q.steps,
            vec![Step {
                place: 0,
                orientation: Orientation::Eager
            }]
        );
        assert_eq!(q.problem.transitions.len(), 81);
        assert_eq!(q.places, vec![1]);
        let proof = q.wrap_proof(json!({}), deadline(), 1_000_000).unwrap();
        let reconstructed = verify_reduction(&net, &proof, deadline(), 1_000_000)
            .unwrap()
            .0;
        assert_eq!(
            serde_json::to_value(&q.problem).unwrap(),
            serde_json::to_value(&reconstructed.problem).unwrap()
        );
    }

    #[test]
    fn every_entrypoint_checks_budgets_and_lift_replays_target() {
        let p = eager();
        let q = reduced(&p);
        let proof = q.wrap_proof(json!({}), deadline(), 10_000).unwrap();
        for (time, work) in [(Instant::now(), 100_000), (deadline(), 0)] {
            assert!(prepare(&p, time, work).is_err());
            assert!(verify_reduction(&p, &proof, time, work).is_err());
            assert!(q.wrap_proof(json!({}), time, work).is_err());
            assert!(q.lift_witness(&p, &[0], time, work).is_err());
        }
        assert!(q.wrap_proof(Value::Null, deadline(), 10_000).is_err());
        assert!(q.lift_witness(&p, &[], deadline(), 10_000).is_err());
        assert!(q.lift_witness(&p, &[999], deadline(), 10_000).is_err());
        let mut p = p.clone();
        p.initial[2] = 1;
        assert!(
            q.lift_witness(&p, &[], deadline(), 10_000)
                .unwrap()
                .0
                .is_empty()
        );
        let mut p = eager();
        p.transitions[2].post[0].1 = u64::MAX;
        assert!(q.lift_witness(&p, &[0, 0], deadline(), 10_000).is_err());
    }

    #[test]
    fn malformed_originals_are_rejected_before_replay_or_reduction() {
        let original = eager();
        let q = reduced(&original);
        let mut cases = Vec::new();
        let mut p = original.clone();
        p.initial.clear();
        cases.push(p);
        let mut p = original.clone();
        p.target[0].coefficients.clear();
        cases.push(p);
        for arcs in [vec![(99, 1)], vec![(0, 0)], vec![(0, 1), (0, 2)]] {
            let mut p = original.clone();
            p.transitions[0].pre = arcs;
            cases.push(p);
        }
        for p in cases {
            assert!(prepare(&p, deadline(), 10_000).is_err());
            assert!(q.lift_witness(&p, &[], deadline(), 10_000).is_err());
        }
    }

    #[test]
    fn recipe_expansion_is_bounded_even_when_flattening_is_exponential() {
        let p = p(&[], vec![t(&[], &[])], vec![]);
        let mut recipes = vec![Recipe::Original(0)];
        for i in 1..100 {
            recipes.push(Recipe::Concat(i - 1, i - 1));
        }
        let q = Prepared {
            problem: p.clone(),
            places: vec![],
            transitions: vec![99],
            steps: vec![],
            recipes,
        };
        assert!(q.lift_witness(&p, &[0], deadline(), 1000).is_err());
        let mut q = q;
        q.recipes[99] = Recipe::Concat(99, 0);
        assert!(q.lift_witness(&p, &[0], deadline(), 1000).is_err());
    }

    fn reachable(p: &Problem) -> Option<Vec<usize>> {
        let mut visited = HashSet::from([p.initial.clone()]);
        let mut queue = VecDeque::from([(p.initial.clone(), Vec::new())]);
        while let Some((marking, trace)) = queue.pop_front() {
            if p.accepts(&marking).unwrap() {
                return Some(trace);
            }
            for id in 0..p.transitions.len() {
                if let Some(next) = p.fire(&marking, id).unwrap() {
                    assert_eq!(next.iter().sum::<u64>(), 1);
                    if visited.insert(next.clone()) {
                        let mut trace = trace.clone();
                        trace.push(id);
                        queue.push_back((next, trace));
                    }
                }
            }
        }
        None
    }

    #[test]
    fn exhaustive_three_place_state_machines_preserve_exact_target_reachability() {
        let transitions: Vec<_> = (0..3)
            .flat_map(|i| (0..3).map(move |j| t(&[(i, 1)], &[(j, 1)])))
            .collect();
        let mut reductions = 0;
        for first in 0..transitions.len() {
            for second in first..transitions.len() {
                for marked in 0..3 {
                    for queried in 0..3 {
                        for bound in 0..=1 {
                            let mut initial = vec![0; 3];
                            initial[marked] = 1;
                            let mut coefficients = vec![0; 3];
                            coefficients[queried] = 1;
                            let p = p(
                                &initial,
                                vec![transitions[first].clone(), transitions[second].clone()],
                                vec![eq(&coefficients, bound)],
                            );
                            if let Some(q) = prepare(&p, deadline(), 100_000).unwrap() {
                                reductions += 1;
                                let original = reachable(&p);
                                let transformed = reachable(&q.problem);
                                assert_eq!(original.is_some(), transformed.is_some());
                                if let Some(trace) = transformed {
                                    let (lifted, marking) =
                                        q.lift_witness(&p, &trace, deadline(), 100_000).unwrap();
                                    assert_eq!(p.check_witness(&lifted).unwrap(), marking);
                                }
                            }
                        }
                    }
                }
            }
        }
        assert!(reductions > 0);
    }
}
