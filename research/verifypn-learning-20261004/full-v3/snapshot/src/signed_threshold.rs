//! Supplied inductive 2-CNF invariants over exact signed linear thresholds.
//! Boolean satisfiability is an overapproximation, so only contradictions certify.
use crate::model::Problem;
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_traits::{One, Zero};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, time::Instant};

#[path = "threshold_discovery.rs"]
mod discovery;
pub use discovery::solve;

pub type Form = Vec<(usize, String)>;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Literal {
    pub form: usize,
    pub threshold: String,
    pub negated: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub forms: Vec<Form>,
    pub clauses: Vec<Vec<Literal>>,
}

type ParsedForm = Vec<(usize, BigInt)>;
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Lit {
    form: usize,
    threshold: BigInt,
    negated: bool,
}

fn tick(deadline: Instant) -> Result<()> {
    ensure!(Instant::now() < deadline, "signed threshold deadline");
    Ok(())
}

fn integer(s: &str, deadline: Instant) -> Result<BigInt> {
    tick(deadline)?;
    let digits = s.strip_prefix(['+', '-']).unwrap_or(s);
    ensure!(!digits.is_empty(), "empty signed decimal integer");
    for digit in digits.bytes() {
        tick(deadline)?;
        ensure!(digit.is_ascii_digit(), "invalid signed decimal integer");
    }
    let value = s.parse().context("invalid signed decimal integer")?;
    tick(deadline)?;
    Ok(value)
}

#[derive(Default)]
struct Forms {
    values: Vec<ParsedForm>,
    ids: BTreeMap<ParsedForm, usize>,
}
impl Forms {
    fn intern(&mut self, value: ParsedForm) -> usize {
        if let Some(&id) = self.ids.get(&value) {
            return id;
        }
        let id = self.values.len();
        self.ids.insert(value.clone(), id);
        self.values.push(value);
        id
    }
}

// Node 2*i means atom i; node 2*i+1 means its negation.
fn boolean_unsat(graph: &[Vec<usize>], deadline: Instant) -> Result<bool> {
    let mut reverse = vec![Vec::new(); graph.len()];
    for (u, edges) in graph.iter().enumerate() {
        tick(deadline)?;
        for &v in edges {
            tick(deadline)?;
            reverse[v].push(u);
        }
    }
    let mut seen = vec![false; graph.len()];
    let mut order = Vec::with_capacity(graph.len());
    let mut stack = Vec::new();
    for root in 0..graph.len() {
        tick(deadline)?;
        if seen[root] {
            continue;
        }
        seen[root] = true;
        stack.push((root, 0));
        while let Some((u, next)) = stack.last_mut() {
            tick(deadline)?;
            if *next == graph[*u].len() {
                order.push(*u);
                stack.pop();
            } else {
                let v = graph[*u][*next];
                *next += 1;
                if !seen[v] {
                    seen[v] = true;
                    stack.push((v, 0));
                }
            }
        }
    }
    let mut component = vec![usize::MAX; graph.len()];
    let mut work = Vec::new();
    for root in order.into_iter().rev() {
        tick(deadline)?;
        if component[root] != usize::MAX {
            continue;
        }
        component[root] = root;
        work.push(root);
        while let Some(u) = work.pop() {
            tick(deadline)?;
            for &v in &reverse[u] {
                tick(deadline)?;
                if component[v] == usize::MAX {
                    component[v] = root;
                    work.push(v);
                }
            }
        }
    }
    for atom in 0..graph.len() / 2 {
        tick(deadline)?;
        if component[2 * atom] == component[2 * atom + 1] {
            return Ok(true);
        }
    }
    tick(deadline)?;
    Ok(false)
}

fn contradiction(
    forms: &Forms,
    invariant: &[Vec<Lit>],
    units: &[Lit],
    deadline: Instant,
) -> Result<bool> {
    let mut atoms = BTreeMap::new();
    for lit in invariant.iter().flatten().chain(units) {
        tick(deadline)?;
        let next = atoms.len();
        atoms
            .entry((lit.form, lit.threshold.clone()))
            .or_insert(next);
    }
    let nodes = atoms
        .len()
        .checked_mul(2)
        .context("threshold graph size overflow")?;
    let mut graph = vec![Vec::new(); nodes];
    let node = |lit: &Lit| 2 * atoms[&(lit.form, lit.threshold.clone())] + usize::from(lit.negated);
    for clause in invariant {
        tick(deadline)?;
        let a = node(&clause[0]);
        let b = node(clause.last().unwrap());
        graph[a ^ 1].push(b);
        graph[b ^ 1].push(a);
    }
    for lit in units {
        tick(deadline)?;
        let a = node(lit);
        graph[a ^ 1].push(a);
    }
    let mut previous = None;
    for ((form, threshold), &atom) in &atoms {
        tick(deadline)?;
        let current = 2 * atom;
        if let Some((prior_form, lower)) = previous
            && prior_form == *form
        {
            graph[current].push(lower);
            graph[lower ^ 1].push(current ^ 1);
        }
        previous = Some((*form, current));
        let mut nonnegative = true;
        let mut nonpositive = true;
        for (_, coefficient) in &forms.values[*form] {
            tick(deadline)?;
            nonnegative &= coefficient >= &BigInt::zero();
            nonpositive &= coefficient <= &BigInt::zero();
        }
        if nonnegative && threshold <= &BigInt::zero() {
            graph[current ^ 1].push(current);
        }
        if nonpositive && threshold > &BigInt::zero() {
            graph[current].push(current ^ 1);
        }
    }
    boolean_unsat(&graph, deadline)
}

/// Check a supplied invariant against the original net and target. Any unsupported
/// obligation or expired deadline returns an error, never an unreachability proof.
pub fn verify(problem: &Problem, certificate: &Certificate, deadline: Instant) -> Result<()> {
    tick(deadline)?;
    problem.validate()?;
    tick(deadline)?;
    ensure!(
        certificate.kind == "signed-threshold-invariant-v1",
        "invalid certificate kind"
    );
    let mut forms = Forms::default();
    let mut canonical = Vec::new();
    for form in &certificate.forms {
        tick(deadline)?;
        let mut parsed = Vec::new();
        let mut previous = None;
        for (place, value) in form {
            tick(deadline)?;
            ensure!(*place < problem.places.len(), "form place out of range");
            ensure!(
                previous.is_none_or(|p| p < *place),
                "form places must be strictly sorted"
            );
            previous = Some(*place);
            let value = integer(value, deadline)?;
            ensure!(!value.is_zero(), "zero form coefficient");
            parsed.push((*place, value));
        }
        canonical.push(forms.intern(parsed));
    }
    let mut invariant = Vec::new();
    for clause in &certificate.clauses {
        tick(deadline)?;
        ensure!((1..=2).contains(&clause.len()), "invalid clause arity");
        let mut parsed = Vec::new();
        for lit in clause {
            tick(deadline)?;
            parsed.push(Lit {
                form: *canonical
                    .get(lit.form)
                    .context("literal form out of range")?,
                threshold: integer(&lit.threshold, deadline)?,
                negated: lit.negated,
            });
        }
        invariant.push(parsed);
    }
    let mut initial = Vec::new();
    for form in &forms.values {
        tick(deadline)?;
        let mut value = BigInt::zero();
        for (p, a) in form {
            tick(deadline)?;
            value += a * BigInt::from(problem.initial[*p]);
        }
        initial.push(value);
    }
    for clause in &invariant {
        tick(deadline)?;
        ensure!(
            clause
                .iter()
                .any(|lit| (initial[lit.form] >= lit.threshold) != lit.negated),
            "invariant false initially"
        );
    }
    let mut incidence: BTreeMap<usize, Vec<(usize, BigInt)>> = BTreeMap::new();
    for (form, terms) in forms.values.iter().enumerate() {
        for (place, coefficient) in terms {
            tick(deadline)?;
            incidence
                .entry(*place)
                .or_default()
                .push((form, coefficient.clone()));
        }
    }
    for transition in &problem.transitions {
        tick(deadline)?;
        let mut deltas = BTreeMap::<usize, BigInt>::new();
        for (positive, arcs) in [(false, &transition.pre), (true, &transition.post)] {
            for &(place, weight) in arcs {
                tick(deadline)?;
                if let Some(terms) = incidence.get(&place) {
                    for (form, coefficient) in terms {
                        tick(deadline)?;
                        let term = coefficient * BigInt::from(weight);
                        let delta = deltas.entry(*form).or_default();
                        if positive {
                            *delta += term;
                        } else {
                            *delta -= term;
                        }
                    }
                }
            }
        }
        let mut guards = None;
        for clause in &invariant {
            tick(deadline)?;
            if clause
                .iter()
                .all(|lit| deltas.get(&lit.form).is_none_or(BigInt::is_zero))
            {
                continue;
            }
            if guards.is_none() {
                let mut units = Vec::new();
                for &(place, weight) in &transition.pre {
                    tick(deadline)?;
                    units.push(Lit {
                        form: forms.intern(vec![(place, BigInt::one())]),
                        threshold: BigInt::from(weight),
                        negated: false,
                    });
                }
                guards = Some(units);
            }
            let mut units = guards.as_ref().unwrap().clone();
            for lit in clause {
                tick(deadline)?;
                units.push(Lit {
                    form: lit.form,
                    threshold: &lit.threshold - deltas.get(&lit.form).cloned().unwrap_or_default(),
                    negated: !lit.negated,
                });
            }
            ensure!(
                contradiction(&forms, &invariant, &units, deadline)?,
                "transition {} does not preserve invariant",
                transition.name
            );
        }
    }
    let mut target = Vec::new();
    for row in &problem.target {
        tick(deadline)?;
        let mut form = Vec::new();
        for (place, &coefficient) in row.coefficients.iter().enumerate() {
            tick(deadline)?;
            if coefficient != 0 {
                form.push((place, BigInt::from(coefficient)));
            }
        }
        let form = forms.intern(form);
        target.push(Lit {
            form,
            threshold: BigInt::from(row.bound),
            negated: false,
        });
        if row.equality {
            target.push(Lit {
                form,
                threshold: BigInt::from(row.bound) + BigInt::one(),
                negated: true,
            });
        }
    }
    ensure!(
        contradiction(&forms, &invariant, &target, deadline)?,
        "invariant does not exclude target"
    );
    tick(deadline)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    use std::time::Duration;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(10)
    }
    fn net(initial: Vec<u64>, transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
        Problem {
            places: (0..initial.len()).map(|p| p.to_string()).collect(),
            initial,
            transitions,
            target,
        }
    }
    fn row(coefficients: Vec<i64>, bound: i64, equality: bool) -> Constraint {
        Constraint {
            coefficients,
            bound,
            equality,
        }
    }
    fn lit(form: usize, threshold: &str, negated: bool) -> Literal {
        Literal {
            form,
            threshold: threshold.into(),
            negated,
        }
    }
    fn cert(forms: Vec<Form>, clauses: Vec<Vec<Literal>>) -> Certificate {
        Certificate {
            kind: "signed-threshold-invariant-v1".into(),
            forms,
            clauses,
        }
    }
    fn coordinate(p: usize) -> Form {
        vec![(p, "1".into())]
    }

    #[test]
    fn weighted_unbounded() {
        let p = net(
            vec![2, 0],
            vec![
                Transition {
                    name: "grow".into(),
                    pre: vec![(0, 2)],
                    post: vec![(1, 5)],
                },
                Transition {
                    name: "unbounded".into(),
                    pre: vec![],
                    post: vec![(1, 3)],
                },
            ],
            vec![row(vec![1, 0], 3, false)],
        );
        let c = cert(vec![coordinate(0)], vec![vec![lit(0, "3", true)]]);
        verify(&p, &c, deadline()).unwrap();
        let mut mutation = p.clone();
        mutation.transitions[1].post.push((0, 1));
        assert!(verify(&mutation, &c, deadline()).is_err());
    }

    #[test]
    fn read_guard_is_necessary() {
        let mut p = net(
            vec![0, 0],
            vec![Transition {
                name: "read".into(),
                pre: vec![(1, 2)],
                post: vec![(0, 1), (1, 2)],
            }],
            vec![row(vec![1, 0], 1, false), row(vec![0, 1], 1, true)],
        );
        let c = cert(
            vec![coordinate(0), coordinate(1)],
            vec![vec![lit(0, "1", true), lit(1, "2", false)]],
        );
        verify(&p, &c, deadline()).unwrap();
        p.transitions[0].pre.clear();
        p.transitions[0].post.retain(|&(place, _)| place == 0);
        assert!(verify(&p, &c, deadline()).is_err());
    }

    #[test]
    fn reachable_and_initial_targets_rejected() {
        let mut p = net(vec![0], vec![], vec![row(vec![1], 0, true)]);
        let c = cert(vec![coordinate(0)], vec![vec![lit(0, "1", true)]]);
        assert!(verify(&p, &c, deadline()).is_err());
        p.target[0].bound = 1;
        p.transitions.push(Transition {
            name: "inc".into(),
            pre: vec![],
            post: vec![(0, 1)],
        });
        assert!(verify(&p, &c, deadline()).is_err());
        let false_initial = cert(vec![coordinate(0)], vec![vec![lit(0, "1", false)]]);
        assert!(verify(&p, &false_initial, deadline()).is_err());
    }

    #[test]
    fn zero_signed_and_integer_extrema() {
        let empty = cert(vec![], vec![]);
        for target in [
            row(vec![0], 1, false),
            row(vec![0], -1, true),
            row(vec![-1], 1, false),
        ] {
            verify(&net(vec![0], vec![], vec![target]), &empty, deadline()).unwrap();
        }
        let p = net(vec![1], vec![], vec![row(vec![i64::MIN], i64::MIN, true)]);
        assert!(verify(&p, &empty, deadline()).is_err());
        let p = net(vec![u64::MAX], vec![], vec![row(vec![1], i64::MAX, true)]);
        let c = cert(
            vec![coordinate(0)],
            vec![vec![lit(0, "18446744073709551615", false)]],
        );
        verify(&p, &c, deadline()).unwrap();
        let p = net(vec![1], vec![], vec![row(vec![-1], 0, true)]);
        let c = cert(vec![vec![(0, "-1".into())]], vec![vec![lit(0, "0", true)]]);
        verify(&p, &c, deadline()).unwrap();
        let huge = cert(
            vec![vec![(0, "18446744073709551616000000000".into())]],
            vec![vec![lit(0, "18446744073709551616000000000", false)]],
        );
        verify(
            &net(vec![u64::MAX], vec![], vec![row(vec![0], 1, false)]),
            &huge,
            deadline(),
        )
        .unwrap();
    }

    #[test]
    fn canonicalization_and_malformed_certificates() {
        let p = net(vec![0], vec![], vec![row(vec![1], 1, false)]);
        let mut c = cert(
            vec![vec![(0, "+01".into())], coordinate(0)],
            vec![vec![lit(0, "1", true)]],
        );
        verify(&p, &c, deadline()).unwrap();
        c.clauses[0][0].form = 1;
        verify(&p, &c, deadline()).unwrap();
        for bad in ["", "+", "1_0", " 1", "١", "--1", "0"] {
            let mut mutation = c.clone();
            mutation.forms[0][0].1 = bad.into();
            assert!(verify(&p, &mutation, deadline()).is_err());
        }
        for form in [
            vec![(1, "1".into())],
            vec![(0, "1".into()), (0, "2".into())],
        ] {
            let mut mutation = c.clone();
            mutation.forms[0] = form;
            assert!(verify(&p, &mutation, deadline()).is_err());
        }
        let mut mutation = c.clone();
        mutation.clauses.push(vec![]);
        assert!(verify(&p, &mutation, deadline()).is_err());
        let mut mutation = c.clone();
        mutation.clauses[0][0].form = 2;
        assert!(verify(&p, &mutation, deadline()).is_err());
        let mut value = serde_json::to_value(&c).unwrap();
        value["extra"] = true.into();
        assert!(serde_json::from_value::<Certificate>(value).is_err());
        let mut value = serde_json::to_value(&c).unwrap();
        value["clauses"][0][0]["extra"] = true.into();
        assert!(serde_json::from_value::<Certificate>(value).is_err());
        assert!(verify(&p, &c, Instant::now()).is_err());
        let mut invalid_problem = p.clone();
        invalid_problem.initial.clear();
        assert!(verify(&invalid_problem, &c, deadline()).is_err());
    }

    #[test]
    fn finite_net_differential() {
        let forms = vec![
            coordinate(0),
            coordinate(1),
            vec![(0, "1".into()), (1, "-1".into())],
            vec![(0, "1".into()), (1, "1".into())],
        ];
        let transitions = [
            Transition {
                name: "right".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "left".into(),
                pre: vec![(1, 1)],
                post: vec![(0, 1)],
            },
            Transition {
                name: "two".into(),
                pre: vec![(0, 2)],
                post: vec![(1, 2)],
            },
            Transition {
                name: "read".into(),
                pre: vec![(0, 1), (1, 1)],
                post: vec![(1, 2)],
            },
        ];
        let mut random = 0x9932_783a_u64;
        let mut next = || {
            random = random.wrapping_mul(6364136223846793005).wrapping_add(1);
            (random >> 32) as usize
        };
        let mut accepted = 0;
        let mut rejected = 0;
        for _ in 0..1000 {
            let selected = transitions
                .iter()
                .filter(|_| next().is_multiple_of(2))
                .cloned()
                .collect();
            let target = row(
                vec![(next() % 5) as i64 - 2, (next() % 5) as i64 - 2],
                (next() % 9) as i64 - 4,
                next().is_multiple_of(2),
            );
            let p = net(vec![2, 0], selected, vec![target]);
            let clauses = (0..next() % 4)
                .map(|_| {
                    (0..1 + next() % 2)
                        .map(|_| {
                            lit(
                                next() % 4,
                                &((next() % 7) as i64 - 2).to_string(),
                                next().is_multiple_of(2),
                            )
                        })
                        .collect()
                })
                .collect();
            let c = cert(forms.clone(), clauses);
            if verify(&p, &c, deadline()).is_err() {
                rejected += 1;
                continue;
            }
            accepted += 1;
            let mut reached = std::collections::BTreeSet::from([p.initial.clone()]);
            let mut work = vec![p.initial.clone()];
            while let Some(marking) = work.pop() {
                assert!(!p.accepts(&marking).unwrap());
                for clause in &c.clauses {
                    assert!(clause.iter().any(|literal| {
                        let value: i64 = c.forms[literal.form]
                            .iter()
                            .map(|(place, coefficient)| {
                                coefficient.parse::<i64>().unwrap() * marking[*place] as i64
                            })
                            .sum();
                        (value >= literal.threshold.parse::<i64>().unwrap()) != literal.negated
                    }));
                }
                for t in 0..p.transitions.len() {
                    if let Some(successor) = p.fire(&marking, t).unwrap()
                        && reached.insert(successor.clone())
                    {
                        work.push(successor);
                    }
                }
            }
        }
        assert!(accepted > 0 && rejected > 0);
    }

    #[test]
    fn boolean_scc_matches_exhaustive_truth_tables() {
        let mut random = 0x9128_abcd_u64;
        for variables in 1..=6 {
            for _ in 0..300 {
                let mut graph = vec![Vec::new(); 2 * variables];
                let mut clauses = Vec::new();
                for _ in 0..12 {
                    random = random.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let a = (random >> 32) as usize % (2 * variables);
                    random = random.wrapping_mul(6364136223846793005).wrapping_add(1);
                    let b = (random >> 32) as usize % (2 * variables);
                    graph[a ^ 1].push(b);
                    graph[b ^ 1].push(a);
                    clauses.push((a, b));
                }
                let satisfiable = (0..1usize << variables).any(|assignment| {
                    let eval = |literal: usize| {
                        ((assignment >> (literal / 2)) & 1 == 1) != (literal % 2 == 1)
                    };
                    clauses.iter().all(|&(a, b)| eval(a) || eval(b))
                });
                assert_eq!(boolean_unsat(&graph, deadline()).unwrap(), !satisfiable);
            }
        }
    }
}
