//! Bounded demand generation and full-rescan Houdini over threshold clauses.
use super::*;
use crate::search::Outcome;
use std::{collections::BTreeSet, time::Duration};

const MAX_CANDIDATES: usize = 2048;
const MAX_FORMS: usize = 64;
const MAX_THRESHOLDS: usize = 64;
const MAX_ROUNDS: usize = 8;

#[derive(Default)]
struct Statistics {
    rounds: usize,
    retained: usize,
    scans: usize,
    obligations: usize,
    removed: usize,
    revived: usize,
    proposals: usize,
    capped: usize,
}
struct Discovery<'a> {
    problem: &'a Problem,
    forms: Forms,
    pool: BTreeSet<Vec<Lit>>,
    vocabulary: BTreeMap<usize, BTreeSet<BigInt>>,
    deadline: Instant,
    remaining: usize,
    max_work: usize,
    arity: usize,
    statistics: Statistics,
}
impl Discovery<'_> {
    fn take(&mut self, amount: usize) -> Result<()> {
        tick(self.deadline)?;
        self.remaining = self
            .remaining
            .checked_sub(amount)
            .context("logical work limit")?;
        Ok(())
    }
    fn describe(&self, message: &str, retained: usize) -> String {
        format!(
            "{message}; candidates={} retained={retained} forms={} rounds={} scans={} obligations={} removed={} revived={} proposals={} capped={} logical_work={}",
            self.pool.len(),
            self.vocabulary.len(),
            self.statistics.rounds,
            self.statistics.scans,
            self.statistics.obligations,
            self.statistics.removed,
            self.statistics.revived,
            self.statistics.proposals,
            self.statistics.capped,
            self.max_work - self.remaining
        )
    }
    fn initial_truth(&mut self, lit: &Lit) -> Result<bool> {
        self.take(self.forms.values[lit.form].len().saturating_add(1))?;
        let mut value = BigInt::zero();
        for (place, coefficient) in &self.forms.values[lit.form] {
            tick(self.deadline)?;
            value += coefficient * BigInt::from(self.problem.initial[*place]);
        }
        Ok((value >= lit.threshold) != lit.negated)
    }
    fn propose(&mut self, mut clause: Vec<Lit>) -> Result<()> {
        self.take(1)?;
        self.statistics.proposals += 1;
        clause.sort();
        clause.dedup();
        if self.pool.contains(&clause) {
            return Ok(());
        }
        if clause.len() == 2
            && clause[0].form == clause[1].form
            && clause[0].threshold == clause[1].threshold
            && clause[0].negated != clause[1].negated
        {
            return Ok(());
        }
        let mut initially_true = false;
        for lit in &clause {
            initially_true |= self.initial_truth(lit)?;
        }
        if !initially_true {
            return Ok(());
        }
        let mut new_forms = BTreeSet::new();
        let mut new_thresholds: BTreeMap<usize, BTreeSet<BigInt>> = BTreeMap::new();
        for lit in &clause {
            if !self.vocabulary.contains_key(&lit.form) {
                new_forms.insert(lit.form);
            }
            if !self
                .vocabulary
                .get(&lit.form)
                .is_some_and(|ks| ks.contains(&lit.threshold))
            {
                new_thresholds
                    .entry(lit.form)
                    .or_default()
                    .insert(lit.threshold.clone());
            }
        }
        if self.pool.len() >= MAX_CANDIDATES
            || self.vocabulary.len() + new_forms.len() > MAX_FORMS
            || new_thresholds.iter().any(|(form, ks)| {
                self.vocabulary.get(form).map_or(0, BTreeSet::len) + ks.len() > MAX_THRESHOLDS
            })
        {
            self.statistics.capped += 1;
            return Ok(());
        }
        for lit in &clause {
            self.vocabulary
                .entry(lit.form)
                .or_default()
                .insert(lit.threshold.clone());
        }
        self.pool.insert(clause);
        Ok(())
    }
    fn grow(&mut self, cube: &[Lit]) -> Result<()> {
        self.take(cube.len())?;
        let mut negated: Vec<_> = cube
            .iter()
            .map(|lit| Lit {
                form: lit.form,
                threshold: lit.threshold.clone(),
                negated: !lit.negated,
            })
            .collect();
        negated.sort();
        negated.dedup();
        for literal in &negated {
            self.propose(vec![literal.clone()])?;
        }
        if self.arity == 2 {
            for (i, left) in negated.iter().enumerate() {
                for right in &negated[i + 1..] {
                    self.propose(vec![left.clone(), right.clone()])?;
                }
            }
        }
        Ok(())
    }
    fn target(&mut self) -> Result<Vec<Lit>> {
        let mut cube = Vec::new();
        let problem = self.problem;
        for row in &problem.target {
            self.take(row.coefficients.len().saturating_add(1))?;
            let form: ParsedForm = row
                .coefficients
                .iter()
                .enumerate()
                .filter(|&(_, &a)| a != 0)
                .map(|(p, &a)| (p, BigInt::from(a)))
                .collect();
            let form = self.forms.intern(form);
            cube.push(Lit {
                form,
                threshold: BigInt::from(row.bound),
                negated: false,
            });
            if row.equality {
                cube.push(Lit {
                    form,
                    threshold: BigInt::from(row.bound) + BigInt::one(),
                    negated: true,
                });
            }
        }
        Ok(cube)
    }
    fn unsat(&mut self, invariant: &[Vec<Lit>], cube: &[Lit]) -> Result<bool> {
        // Logical charges count clauses/literals and form terms, not instructions.
        let mut cost = cube.len().saturating_add(1);
        for clause in invariant {
            tick(self.deadline)?;
            cost = cost.saturating_add(1);
            for lit in clause {
                cost = cost.saturating_add(self.forms.values[lit.form].len().saturating_add(1));
            }
        }
        for lit in cube {
            tick(self.deadline)?;
            cost = cost.saturating_add(self.forms.values[lit.form].len());
        }
        self.take(cost)?;
        self.statistics.obligations += 1;
        contradiction(&self.forms, invariant, cube, self.deadline)
    }
    fn changes(&mut self) -> Result<BTreeMap<usize, BTreeMap<usize, BigInt>>> {
        let mut incidence: BTreeMap<usize, Vec<(usize, BigInt)>> = BTreeMap::new();
        for &form in self.vocabulary.keys() {
            for (place, coefficient) in &self.forms.values[form] {
                tick(self.deadline)?;
                incidence
                    .entry(*place)
                    .or_default()
                    .push((form, coefficient.clone()));
            }
        }
        self.take(incidence.values().map(Vec::len).sum())?;
        let mut changed: BTreeMap<usize, BTreeMap<usize, BigInt>> = BTreeMap::new();
        let problem = self.problem;
        for (id, transition) in problem.transitions.iter().enumerate() {
            self.take(1)?;
            let mut delta = BTreeMap::<usize, BigInt>::new();
            for (positive, arcs) in [(false, &transition.pre), (true, &transition.post)] {
                for &(place, weight) in arcs {
                    self.take(1)?;
                    if let Some(terms) = incidence.get(&place) {
                        for (form, coefficient) in terms {
                            self.take(1)?;
                            let amount = coefficient * BigInt::from(weight);
                            let entry = delta.entry(*form).or_default();
                            if positive {
                                *entry += amount;
                            } else {
                                *entry -= amount;
                            }
                        }
                    }
                }
            }
            for (form, delta) in delta {
                if !delta.is_zero() {
                    changed.entry(form).or_default().insert(id, delta);
                }
            }
        }
        Ok(changed)
    }
    fn failure_cube(
        &mut self,
        transition: usize,
        clause: &[Lit],
        changes: &BTreeMap<usize, BTreeMap<usize, BigInt>>,
    ) -> Result<Vec<Lit>> {
        let mut cube = Vec::new();
        let problem = self.problem;
        for &(place, weight) in &problem.transitions[transition].pre {
            self.take(1)?;
            let form = self.forms.intern(vec![(place, BigInt::one())]);
            cube.push(Lit {
                form,
                threshold: BigInt::from(weight),
                negated: false,
            });
        }
        for lit in clause {
            self.take(1)?;
            let delta = changes
                .get(&lit.form)
                .and_then(|ts| ts.get(&transition))
                .cloned()
                .unwrap_or_default();
            cube.push(Lit {
                form: lit.form,
                threshold: &lit.threshold - delta,
                negated: !lit.negated,
            });
        }
        Ok(cube)
    }
    fn certificate(&mut self, retained: &[Vec<Lit>]) -> Result<Certificate> {
        let mut forms = Vec::new();
        let mut ids = BTreeMap::new();
        for lit in retained.iter().flatten() {
            self.take(1)?;
            if let std::collections::btree_map::Entry::Vacant(entry) = ids.entry(lit.form) {
                entry.insert(forms.len());
                let mut form = Vec::new();
                for (place, coefficient) in &self.forms.values[lit.form] {
                    tick(self.deadline)?;
                    form.push((*place, coefficient.to_string()));
                }
                forms.push(form);
            }
        }
        let clauses = retained
            .iter()
            .map(|clause| {
                clause
                    .iter()
                    .map(|lit| Literal {
                        form: ids[&lit.form],
                        threshold: lit.threshold.to_string(),
                        negated: lit.negated,
                    })
                    .collect()
            })
            .collect();
        Ok(Certificate {
            kind: "signed-threshold-invariant-v1".into(),
            forms,
            clauses,
        })
    }
    fn run(&mut self) -> Result<Option<Certificate>> {
        self.take(1)?;
        self.problem.validate()?;
        let target = self.target()?;
        self.grow(&target)?;
        let mut previous_removed = BTreeSet::new();
        for round in 0..MAX_ROUNDS {
            self.take(1)?;
            self.statistics.rounds += 1;
            let changes = self.changes()?;
            let mut retained: Vec<_> = self.pool.iter().cloned().collect();
            let mut failed = Vec::new();
            let mut removed = BTreeSet::new();
            loop {
                self.take(1)?;
                self.statistics.scans += 1;
                let mut keep = Vec::new();
                for clause in &retained {
                    self.take(1)?;
                    let mut affected = BTreeSet::new();
                    for lit in clause {
                        if let Some(transitions) = changes.get(&lit.form) {
                            self.take(transitions.len())?;
                            affected.extend(transitions.keys().copied());
                        }
                    }
                    let mut preserved = true;
                    for transition in affected {
                        let cube = self.failure_cube(transition, clause, &changes)?;
                        if !self.unsat(&retained, &cube)? {
                            failed.push(cube);
                            removed.insert(clause.clone());
                            self.statistics.removed += 1;
                            preserved = false;
                            break;
                        }
                    }
                    if preserved {
                        keep.push(clause.clone());
                    }
                }
                if keep.len() == retained.len() {
                    break;
                }
                retained = keep;
            }
            self.statistics.revived += retained
                .iter()
                .filter(|c| previous_removed.contains(*c))
                .count();
            self.statistics.retained = retained.len();
            if self.unsat(&retained, &target)? {
                let certificate = self.certificate(&retained)?;
                verify(self.problem, &certificate, self.deadline)?;
                return Ok(Some(certificate));
            }
            if round + 1 == MAX_ROUNDS {
                return Ok(None);
            }
            let before = self.pool.len();
            for cube in failed {
                self.grow(&cube)?;
            }
            if self.pool.len() == before {
                return Ok(None);
            }
            previous_removed = removed;
        }
        Ok(None)
    }
}

/// The work allowance counts deterministic logical operations, not CPU instructions.
/// Every negative answer is rechecked by the supplied-invariant kernel.
pub fn solve(
    problem: &Problem,
    timeout: Duration,
    max_work: usize,
    max_clause_arity: usize,
) -> Outcome {
    let method = if max_clause_arity == 1 {
        "threshold-unary"
    } else {
        "threshold"
    };
    let start = Instant::now();
    let Some(deadline) = start.checked_add(timeout) else {
        return Outcome::unknown(method, "invalid timeout", 0);
    };
    if !(1..=2).contains(&max_clause_arity) {
        return Outcome::unknown(method, "clause arity must be 1 or 2", 0);
    }
    let mut discovery = Discovery {
        problem,
        forms: Forms::default(),
        pool: BTreeSet::new(),
        vocabulary: BTreeMap::new(),
        deadline,
        remaining: max_work,
        max_work,
        arity: max_clause_arity,
        statistics: Statistics::default(),
    };
    let result = discovery.run();
    let (message, certificate) = match result {
        Ok(Some(certificate)) => (
            "checked signed-threshold invariant".to_string(),
            Some(certificate),
        ),
        Ok(None) => ("bounded candidate discovery exhausted".to_string(), None),
        Err(error) => (error.to_string(), None),
    };
    let retained = certificate
        .as_ref()
        .map_or(discovery.statistics.retained, |c| c.clauses.len());
    let mut outcome = Outcome::unknown(
        method,
        &discovery.describe(&message, retained),
        discovery.max_work - discovery.remaining,
    );
    if let Some(certificate) = certificate {
        match serde_json::to_value(certificate) {
            Ok(proof) if Instant::now() < deadline => {
                outcome.verdict = "unreachable";
                outcome.proof = Some(proof);
            }
            _ => {
                outcome.reason =
                    discovery.describe("certificate serialization or deadline failure", retained);
            }
        }
    }
    outcome
}

#[cfg(test)]
mod tests {
    use super::*;

    fn instance(problem: &Problem) -> Discovery<'_> {
        Discovery {
            problem,
            forms: Forms::default(),
            pool: BTreeSet::new(),
            vocabulary: BTreeMap::new(),
            deadline: Instant::now() + Duration::from_secs(10),
            remaining: 1_000_000,
            max_work: 1_000_000,
            arity: 2,
            statistics: Statistics::default(),
        }
    }
    fn net(places: usize) -> Problem {
        Problem {
            places: (0..places).map(|p| p.to_string()).collect(),
            initial: vec![0; places],
            transitions: Vec::new(),
            target: Vec::new(),
        }
    }
    fn upper(form: usize, threshold: usize) -> Lit {
        Lit {
            form,
            threshold: BigInt::from(threshold),
            negated: true,
        }
    }
    #[test]
    fn candidate_caps_are_stable_and_do_not_count_guard_forms() {
        let p = net(100);
        let mut discovery = instance(&p);
        for place in 0..100 {
            discovery.forms.intern(vec![(place, BigInt::one())]);
        }
        for form in 0..65 {
            discovery.propose(vec![upper(form, 1)]).unwrap();
        }
        assert_eq!(discovery.pool.len(), MAX_FORMS);
        assert_eq!(discovery.statistics.capped, 1);
        assert_eq!(discovery.forms.values.len(), 100);
        let mut discovery = instance(&p);
        discovery.forms.intern(vec![(0, BigInt::one())]);
        for threshold in 1..=70 {
            discovery.propose(vec![upper(0, threshold)]).unwrap();
        }
        assert_eq!(discovery.pool.len(), MAX_THRESHOLDS);
        assert_eq!(discovery.statistics.capped, 6);
        let mut discovery = instance(&p);
        discovery.forms.intern(vec![(0, BigInt::one())]);
        discovery.forms.intern(vec![(1, BigInt::one())]);
        for left in 1..=33 {
            for right in 1..=64 {
                discovery
                    .propose(vec![upper(0, left), upper(1, right)])
                    .unwrap();
            }
        }
        assert_eq!(discovery.pool.len(), MAX_CANDIDATES);
        assert_eq!(discovery.statistics.capped, 64);
    }
    #[test]
    fn growth_restarts_houdini_and_revives_removed_clauses() {
        use crate::model::{Constraint, Transition};
        let mut p = net(2);
        p.initial = vec![2, 0];
        p.transitions = vec![
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
        ];
        p.target = vec![
            Constraint {
                coefficients: vec![1, 0],
                bound: 2,
                equality: false,
            },
            Constraint {
                coefficients: vec![0, 1],
                bound: 1,
                equality: false,
            },
        ];
        let mut discovery = instance(&p);
        let proof = discovery.run().unwrap().unwrap();
        assert!(discovery.statistics.rounds > 1);
        assert!(discovery.statistics.revived > 0);
        verify(&p, &proof, discovery.deadline).unwrap();
    }

    #[test]
    fn resource_exits_never_produce_a_proof() {
        let p = net(1);
        for outcome in [
            solve(&p, Duration::ZERO, 1_000, 2),
            solve(&p, Duration::from_secs(1), 0, 2),
            solve(&p, Duration::from_secs(1), 1_000, 3),
        ] {
            assert_eq!(outcome.verdict, "unknown");
            assert!(outcome.proof.is_none());
        }
    }
}
