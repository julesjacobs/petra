//! Direct membership in the uncomplemented serial response language.
use crate::model::{Constraint, Problem, Transition};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::time::Instant;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RawQuery {
    pub format: String,
    pub places: Vec<String>,
    pub initial: Vec<u64>,
    pub transitions: Vec<Transition>,
    pub target: RawTarget,
}
#[derive(Clone, Debug, Serialize)]
pub struct RawTarget {
    pub kind: String,
    pub zero_places: Vec<usize>,
    pub response_places: Vec<usize>,
    pub excluded_semilinear: Vec<LinearSet>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub excluded_automaton: Option<SerialAutomaton>,
}
impl<'de> Deserialize<'de> for RawTarget {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        #[derive(Deserialize)]
        struct Fields {
            kind: String,
            zero_places: Vec<usize>,
            response_places: Vec<usize>,
            excluded_semilinear: Option<Vec<LinearSet>>,
            excluded_automaton: Option<SerialAutomaton>,
        }
        let fields = Fields::deserialize(deserializer)?;
        let excluded_semilinear = match fields.excluded_semilinear {
            Some(components) => components,
            None if fields.kind == "completed-outside-automaton" => vec![],
            None => return Err(serde::de::Error::missing_field("excluded_semilinear")),
        };
        Ok(Self {
            kind: fields.kind,
            zero_places: fields.zero_places,
            response_places: fields.response_places,
            excluded_semilinear,
            excluded_automaton: fields.excluded_automaton,
        })
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SerialAutomaton {
    pub states: usize,
    pub initial: usize,
    pub accepting: Vec<usize>,
    /// Each edge emits one token at a response place of the original net.
    pub edges: Vec<SerialEdge>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SerialEdge {
    pub source: usize,
    pub target: usize,
    pub response: usize,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LinearSet {
    pub base: Vec<(usize, u64)>,
    pub periods: Vec<Vec<(usize, u64)>>,
}
impl RawQuery {
    pub fn from_json_file(path: &std::path::Path) -> Result<Self> {
        let mut diagnostics = crate::raw_diagnostics::Diagnostics::new("raw-input");
        let result = (|| {
            diagnostics.phase("input-read");
            let source = std::fs::read_to_string(path)?;
            diagnostics.add("input_bytes", source.len());
            diagnostics.phase("json-parse");
            let query: Self = serde_json::from_str(&source)?;
            drop(source);
            diagnostics.phase("input-validation");
            query.validate()?;
            if diagnostics.enabled() {
                diagnostics.add("places", query.places.len());
                diagnostics.add("transitions", query.transitions.len());
                diagnostics.add(
                    "arcs",
                    query
                        .transitions
                        .iter()
                        .map(|t| t.pre.len() + t.post.len())
                        .sum(),
                );
                if let Some(automaton) = &query.target.excluded_automaton {
                    diagnostics.add("serial_states", automaton.states);
                    diagnostics.add("serial_edges", automaton.edges.len());
                }
            }
            Ok(query)
        })();
        diagnostics.finish_result(&result);
        result
    }

    pub fn validate(&self) -> Result<()> {
        match self.format.as_str() {
            "ser-raw-v1" => ensure!(
                self.target.kind == "completed-outside-semilinear"
                    && self.target.excluded_automaton.is_none(),
                "invalid semilinear raw target"
            ),
            "ser-raw-v2" => ensure!(
                self.target.kind == "completed-outside-automaton"
                    && self.target.excluded_automaton.is_some()
                    && self.target.excluded_semilinear.is_empty(),
                "invalid automaton raw target"
            ),
            _ => anyhow::bail!("unsupported raw query format"),
        }
        ensure!(
            self.initial.len() == self.places.len(),
            "initial marking dimension mismatch"
        );
        let mut classified = HashSet::new();
        for &p in self
            .target
            .zero_places
            .iter()
            .chain(&self.target.response_places)
        {
            ensure!(
                p < self.places.len() && classified.insert(p),
                "invalid, repeated, or overlapping target place"
            );
        }
        let responses: HashSet<_> = self.target.response_places.iter().copied().collect();
        if let Some(a) = &self.target.excluded_automaton {
            ensure!(
                a.states > 0 && a.initial < a.states,
                "invalid serial initial state"
            );
            let mut accepting = HashSet::new();
            for &state in &a.accepting {
                ensure!(
                    state < a.states && accepting.insert(state),
                    "invalid serial accepting state"
                );
            }
            for edge in &a.edges {
                ensure!(
                    edge.source < a.states
                        && edge.target < a.states
                        && responses.contains(&edge.response),
                    "invalid serial edge"
                );
            }
        }
        for c in &self.target.excluded_semilinear {
            for v in std::iter::once(&c.base).chain(&c.periods) {
                let mut used = HashSet::new();
                for &(p, w) in v {
                    ensure!(
                        responses.contains(&p) && w > 0 && used.insert(p),
                        "invalid or repeated semilinear term"
                    );
                }
            }
        }
        for t in &self.transitions {
            for arcs in [&t.pre, &t.post] {
                let mut used = HashSet::new();
                for &(p, w) in arcs {
                    ensure!(
                        p < self.places.len() && w > 0 && used.insert(p),
                        "invalid or repeated arc in {}",
                        t.name
                    );
                }
            }
        }
        Ok(())
    }

    /// The target here checks completion only; use `accepts` for the raw target.
    pub fn net(&self) -> Problem {
        let target = if self.target.zero_places.is_empty() {
            vec![]
        } else {
            let mut coefficients = vec![0; self.places.len()];
            for &p in &self.target.zero_places {
                if p < coefficients.len() {
                    coefficients[p] = 1;
                }
            }
            vec![Constraint {
                coefficients,
                bound: 0,
                equality: true,
            }]
        };
        Problem {
            places: self.places.clone(),
            initial: self.initial.clone(),
            transitions: self.transitions.clone(),
            target,
        }
    }

    /// Resource exhaustion is an error, never evidence of nonmembership.
    pub fn accepts(&self, marking: &[u64], deadline: Instant, max_work: usize) -> Result<bool> {
        self.validate()?;
        ensure!(
            marking.len() == self.places.len(),
            "marking dimension mismatch"
        );
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        budget.tick()?;
        if self.target.zero_places.iter().any(|&p| marking[p] != 0) {
            return Ok(false);
        }
        if let Some(a) = &self.target.excluded_automaton {
            return Ok(!automaton_member(
                a,
                marking,
                &self.target.response_places,
                &mut budget,
            )?);
        }
        for component in &self.target.excluded_semilinear {
            budget.tick()?;
            if member(
                component,
                marking,
                &self.target.response_places,
                &mut budget,
            )? {
                return Ok(false);
            }
        }
        Ok(true)
    }
}
struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self) -> Result<()> {
        self.spend(1)
    }
    fn spend(&mut self, amount: usize) -> Result<()> {
        ensure!(
            Instant::now() < self.deadline,
            "raw target membership deadline"
        );
        self.remaining = self
            .remaining
            .checked_sub(amount)
            .ok_or_else(|| anyhow::anyhow!("raw target membership work limit"))?;
        Ok(())
    }
}
fn automaton_member(
    automaton: &SerialAutomaton,
    marking: &[u64],
    responses: &[usize],
    budget: &mut Budget,
) -> Result<bool> {
    budget.spend(automaton.states.saturating_add(responses.len()))?;
    let indices: std::collections::HashMap<_, _> = responses
        .iter()
        .enumerate()
        .map(|(index, &place)| (place, index))
        .collect();
    let mut successors = vec![vec![]; automaton.states];
    for edge in &automaton.edges {
        budget.tick()?;
        successors[edge.source].push((edge.target, indices[&edge.response]));
    }
    let accepting: HashSet<_> = automaton.accepting.iter().copied().collect();
    let residual: Vec<_> = responses.iter().map(|&p| marking[p]).collect();
    let mut pending = vec![(automaton.initial, residual.clone())];
    let mut seen = HashSet::from([(automaton.initial, residual)]);
    while let Some((state, residual)) = pending.pop() {
        budget.spend(residual.len().saturating_add(1))?;
        if accepting.contains(&state) && residual.iter().all(|&n| n == 0) {
            return Ok(true);
        }
        for &(next, dimension) in &successors[state] {
            budget.tick()?;
            if residual[dimension] == 0 {
                continue;
            }
            budget.spend(residual.len().saturating_add(1))?;
            let mut remaining = residual.clone();
            remaining[dimension] -= 1;
            if seen.insert((next, remaining.clone())) {
                pending.push((next, remaining));
            }
        }
    }
    Ok(false)
}
fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 {
        (a, b) = (b, a % b);
    }
    a
}
fn member(
    component: &LinearSet,
    marking: &[u64],
    responses: &[usize],
    budget: &mut Budget,
) -> Result<bool> {
    let mut residual = marking.to_vec();
    for &(p, w) in &component.base {
        if residual[p] < w {
            return Ok(false);
        }
        residual[p] -= w;
    }
    let mut periods = component.periods.clone();
    for v in &mut periods {
        v.sort_unstable();
    }
    periods.sort_unstable();
    periods.dedup();
    periods.retain(|v| !v.is_empty());
    let free: HashSet<usize> = periods
        .iter()
        .filter(|v| v.len() == 1 && v[0].1 == 1)
        .map(|v| v[0].0)
        .collect();
    periods.retain(|v| v.iter().any(|(p, _)| !free.contains(p)));
    // Every retained period has a positive bounded coefficient. Unit periods
    // fill only the remaining slack, so their coordinates still bound all others.
    periods.sort_by_key(|v| v.iter().map(|&(p, w)| residual[p] / w).min().unwrap_or(0));
    let needed: Vec<_> = responses
        .iter()
        .copied()
        .filter(|p| !free.contains(p))
        .collect();
    let mut suffix_gcd = vec![vec![0; needed.len()]; periods.len() + 1];
    for i in (0..periods.len()).rev() {
        suffix_gcd[i] = suffix_gcd[i + 1].clone();
        for (j, &p) in needed.iter().enumerate() {
            let w = periods[i]
                .iter()
                .find(|&&(q, _)| q == p)
                .map_or(0, |&(_, w)| w);
            suffix_gcd[i][j] = gcd(suffix_gcd[i][j], w);
        }
    }
    enum Frame {
        Visit(usize, Vec<u64>),
        More(usize, Vec<u64>),
    }
    let mut stack = vec![Frame::Visit(0, residual)];
    let mut seen = HashSet::new();
    while let Some(frame) = stack.pop() {
        budget.tick()?;
        let (i, r) = match frame {
            Frame::Visit(i, r) => {
                if needed.iter().all(|&p| r[p] == 0) {
                    return Ok(true);
                }
                if i == periods.len() || !seen.insert((i, r.clone())) {
                    continue;
                }
                if needed.iter().enumerate().any(|(j, &p)| {
                    let g = suffix_gcd[i][j];
                    if g == 0 { r[p] != 0 } else { r[p] % g != 0 }
                }) {
                    continue;
                }
                (i, r)
            }
            Frame::More(i, r) => (i, r),
        };
        // Enumerate the coefficient without materializing an unbounded fanout.
        if periods[i].iter().all(|&(p, w)| r[p] >= w) {
            let mut next = r.clone();
            for &(p, w) in &periods[i] {
                next[p] -= w;
            }
            stack.push(Frame::More(i, next));
        }
        if i + 1 == periods.len() {
            let mut count = None;
            let mut possible = true;
            for &p in &needed {
                let w = periods[i]
                    .iter()
                    .find(|&&(q, _)| q == p)
                    .map_or(0, |&(_, w)| w);
                if w == 0 {
                    possible &= r[p] == 0;
                } else {
                    possible &= r[p] % w == 0;
                    let k = r[p] / w;
                    if let Some(old) = count {
                        possible &= old == k;
                    } else {
                        count = Some(k);
                    }
                }
            }
            if possible {
                let k = count.unwrap_or(0);
                if periods[i].iter().all(|&(p, w)| k <= r[p] / w) {
                    return Ok(true);
                }
            }
            // This closed-form check covered every remaining coefficient.
            if matches!(stack.last(), Some(Frame::More(j,_)) if *j == i) {
                stack.pop();
            }
        } else {
            stack.push(Frame::Visit(i + 1, r));
        }
    }
    Ok(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    fn query(periods: Vec<Vec<(usize, u64)>>) -> RawQuery {
        RawQuery {
            format: "ser-raw-v1".into(),
            places: vec!["a".into(), "b".into(), "pending".into()],
            initial: vec![0; 3],
            transitions: vec![],
            target: RawTarget {
                excluded_automaton: None,
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![2],
                response_places: vec![0, 1],
                excluded_semilinear: vec![LinearSet {
                    base: vec![],
                    periods,
                }],
            },
        }
    }
    fn accepted(q: &RawQuery, m: &[u64]) -> bool {
        q.accepts(m, Instant::now() + Duration::from_secs(1), 10000)
            .unwrap()
    }
    #[test]
    fn nongreedy() {
        let q = query(vec![vec![(0, 3)], vec![(0, 2)]]);
        assert!(!accepted(&q, &[4, 0, 0]));
        assert!(accepted(&q, &[1, 0, 0]));
    }
    #[test]
    fn correlated() {
        let q = query(vec![vec![(0, 2), (1, 1)], vec![(0, 1), (1, 2)]]);
        assert!(!accepted(&q, &[3, 3, 0]));
        assert!(accepted(&q, &[2, 2, 0]));
    }
    #[test]
    fn units_duplicates_and_empty_periods() {
        let q = query(vec![
            vec![],
            vec![(0, 1)],
            vec![(0, 1)],
            vec![(0, 2), (1, 3)],
        ]);
        assert!(!accepted(&q, &[u64::MAX, 3, 0]));
        assert!(accepted(&q, &[1, 3, 0]));
        assert!(!accepted(&q, &[u64::MAX, 0, 0]));
        assert!(!accepted(&q, &[1, 1, 1]));
    }
    #[test]
    fn huge_single_generator() {
        let q = query(vec![vec![(0, 2), (1, 2)]]);
        assert!(!accepted(&q, &[u64::MAX - 1, u64::MAX - 1, 0]));
        assert!(accepted(&q, &[u64::MAX - 1, u64::MAX - 3, 0]));
    }
    #[test]
    fn bases_and_union() {
        let mut q = query(vec![]);
        q.target.excluded_semilinear[0].base = vec![(0, 4)];
        q.target.excluded_semilinear.push(LinearSet {
            base: vec![(1, 2)],
            periods: vec![],
        });
        assert!(!accepted(&q, &[4, 0, 0]));
        assert!(!accepted(&q, &[0, 2, 0]));
        assert!(accepted(&q, &[0, 0, 0]));
    }
    #[test]
    fn limits_are_errors() {
        let q = query(vec![vec![(0, 2)]]);
        assert!(q.accepts(&[1, 0, 0], Instant::now(), 100).is_err());
        assert!(
            q.accepts(&[1, 0, 0], Instant::now() + Duration::from_secs(1), 0)
                .is_err()
        );
    }
    #[test]
    fn differential_finite_boxes() {
        for seed in 0usize..80 {
            let periods: Vec<_> = (0..3)
                .map(|i| {
                    [
                        (0, ((seed * (i + 1) + i) % 4) as u64),
                        (1, ((seed + 3 * i + seed / 4) % 4) as u64),
                    ]
                    .into_iter()
                    .filter(|&(_, w)| w != 0)
                    .collect::<Vec<_>>()
                })
                .collect();
            let q = query(periods.clone());
            let mut reachable = HashSet::from([(0u64, 0u64)]);
            let mut todo = vec![(0u64, 0u64)];
            while let Some((a, b)) = todo.pop() {
                for v in &periods {
                    let da = v.iter().find(|&&(p, _)| p == 0).map_or(0, |&(_, w)| w);
                    let db = v.iter().find(|&&(p, _)| p == 1).map_or(0, |&(_, w)| w);
                    let next = (a + da, b + db);
                    if next.0 <= 8 && next.1 <= 8 && reachable.insert(next) {
                        todo.push(next);
                    }
                }
            }
            for a in 0..=8 {
                for b in 0..=8 {
                    assert_eq!(
                        !accepted(&q, &[a, b, 0]),
                        reachable.contains(&(a, b)),
                        "seed={seed} marking={a},{b}"
                    );
                }
            }
        }
    }
    #[test]
    fn invalid_inputs() {
        let mut q = query(vec![vec![(2, 1)]]);
        assert!(q.validate().is_err());
        q = query(vec![vec![(0, 1), (0, 2)]]);
        assert!(q.validate().is_err());
        q = query(vec![vec![(0, 0)]]);
        assert!(q.validate().is_err());
        q = query(vec![]);
        q.target.zero_places.push(0);
        assert!(q.validate().is_err());
        q = query(vec![]);
        q.initial.pop();
        assert!(q.validate().is_err());
        q = query(vec![]);
        q.transitions.push(Transition {
            name: "t".into(),
            pre: vec![(0, 1), (0, 1)],
            post: vec![],
        });
        assert!(q.validate().is_err());
    }
    #[test]
    fn completion_sum_matches_individual_zero_tests() {
        for mask in 0..8 {
            let mut q = query(vec![]);
            q.target.zero_places = (0..3).filter(|i| mask & (1 << i) != 0).collect();
            q.target.response_places = (0..3).filter(|i| mask & (1 << i) == 0).collect();
            q.validate().unwrap();
            let net = q.net();
            assert_eq!(net.target.len(), usize::from(mask != 0));
            for a in [0, 1, u64::MAX] {
                for b in [0, 1, u64::MAX] {
                    for c in [0, 1, u64::MAX] {
                        let m = [a, b, c];
                        assert_eq!(
                            net.accepts(&m).unwrap(),
                            q.target.zero_places.iter().all(|&i| m[i] == 0)
                        );
                    }
                }
            }
        }
    }
}
