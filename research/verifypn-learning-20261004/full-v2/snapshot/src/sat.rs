//! Bounded native SAT proposals with independently checked models and RUP proofs.
use anyhow::{Result, ensure};
use std::{
    cell::RefCell,
    io::{self, Write},
    rc::Rc,
    time::Instant,
};
use varisat::{ExtendFormula, Lit, ProofFormat, Solver, Var};

#[derive(Debug)]
pub enum SatResult {
    Sat(Vec<bool>),
    Unsat(Vec<Vec<i32>>),
    Unknown(String),
}

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn charge(&mut self, work: usize) -> Result<()> {
        ensure!(Instant::now() < self.deadline, "SAT deadline");
        self.remaining = self
            .remaining
            .checked_sub(work)
            .ok_or_else(|| anyhow::anyhow!("SAT work limit"))?;
        Ok(())
    }
}

fn validate_literal(literal: i32, variables: usize) -> Result<()> {
    ensure!(
        literal != 0 && literal.unsigned_abs() as usize <= variables,
        "invalid CNF literal {literal}"
    );
    Ok(())
}
fn normalize(variables: usize, clause: &[i32], budget: &mut Budget) -> Result<Vec<i32>> {
    budget.charge(
        clause
            .len()
            .saturating_mul(clause.len().checked_ilog2().unwrap_or(0) as usize + 2)
            .saturating_add(1),
    )?;
    for &literal in clause {
        validate_literal(literal, variables)?;
    }
    let mut result = clause.to_vec();
    result.sort_unstable();
    result.dedup();
    budget.charge(0)?;
    Ok(result)
}
fn index(literal: i32) -> usize {
    literal.unsigned_abs() as usize - 1
}
fn watch_index(literal: i32) -> usize {
    index(literal) * 2 + usize::from(literal < 0)
}
fn value(assignment: &[i8], literal: i32) -> i8 {
    assignment[index(literal)] * if literal > 0 { 1 } else { -1 }
}

struct Rup {
    clauses: Vec<Vec<i32>>,
    watches: Vec<Vec<usize>>,
    units: Vec<i32>,
    assignment: Vec<i8>,
    trail: Vec<i32>,
    empty: bool,
}
impl Rup {
    fn new(variables: usize, budget: &mut Budget) -> Result<Self> {
        budget.charge(variables.saturating_mul(3).saturating_add(1))?;
        Ok(Self {
            clauses: Vec::new(),
            watches: vec![Vec::new(); variables * 2],
            units: Vec::new(),
            assignment: vec![0; variables],
            trail: Vec::new(),
            empty: false,
        })
    }
    fn add(&mut self, clause: Vec<i32>) {
        if clause
            .iter()
            .any(|&literal| clause.binary_search(&-literal).is_ok())
        {
            return;
        }
        match clause.len() {
            0 => self.empty = true,
            1 => self.units.push(clause[0]),
            _ => {
                let id = self.clauses.len();
                self.watches[watch_index(clause[0])].push(id);
                self.watches[watch_index(clause[1])].push(id);
                self.clauses.push(clause);
            }
        }
    }
    fn assign(&mut self, literal: i32) -> bool {
        match value(&self.assignment, literal) {
            -1 => false,
            1 => true,
            _ => {
                self.assignment[index(literal)] = if literal > 0 { 1 } else { -1 };
                self.trail.push(literal);
                true
            }
        }
    }
    fn conflict(&mut self, clause: &[i32], budget: &mut Budget) -> Result<bool> {
        budget.charge(self.trail.len().saturating_add(1))?;
        for literal in self.trail.drain(..) {
            self.assignment[index(literal)] = 0;
        }
        if self.empty {
            return Ok(true);
        }
        for &literal in clause {
            budget.charge(1)?;
            if !self.assign(-literal) {
                return Ok(true);
            }
        }
        for i in 0..self.units.len() {
            budget.charge(1)?;
            if !self.assign(self.units[i]) {
                return Ok(true);
            }
        }
        let mut head = 0;
        while head < self.trail.len() {
            budget.charge(1)?;
            let false_literal = -self.trail[head];
            head += 1;
            let watched = watch_index(false_literal);
            let mut pending = std::mem::take(&mut self.watches[watched]);
            while let Some(id) = pending.pop() {
                budget.charge(1)?;
                let clause = &mut self.clauses[id];
                if clause[0] == false_literal {
                    clause.swap(0, 1);
                }
                ensure!(clause[1] == false_literal, "invalid RUP watch");
                if value(&self.assignment, clause[0]) == 1 {
                    self.watches[watched].push(id);
                    continue;
                }
                let mut replacement = None;
                for (i, &literal) in clause.iter().enumerate().skip(2) {
                    budget.charge(1)?;
                    if value(&self.assignment, literal) != -1 {
                        replacement = Some(i);
                        break;
                    }
                }
                if let Some(i) = replacement {
                    clause.swap(1, i);
                    self.watches[watch_index(clause[1])].push(id);
                } else {
                    let unit = clause[0];
                    self.watches[watched].push(id);
                    if !self.assign(unit) {
                        self.watches[watched].extend(pending);
                        return Ok(true);
                    }
                }
            }
        }
        Ok(false)
    }
}

/// Check every addition by reverse unit propagation, ending in the empty clause.
/// Deletions are omitted: retaining clauses preserves the validity of RUP steps.
pub fn check_rup(
    variables: usize,
    clauses: &[Vec<i32>],
    additions: &[Vec<i32>],
    deadline: Instant,
    max_work: usize,
) -> Result<()> {
    ensure!(variables <= i32::MAX as usize, "too many CNF variables");
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    let mut checker = Rup::new(variables, &mut budget)?;
    for clause in clauses {
        checker.add(normalize(variables, clause, &mut budget)?);
    }
    ensure!(
        additions.last().is_some_and(Vec::is_empty),
        "RUP proof must end in empty clause"
    );
    for (step, clause) in additions.iter().enumerate() {
        ensure!(
            !clause.is_empty() || step + 1 == additions.len(),
            "steps after empty clause"
        );
        let normalized = normalize(variables, clause, &mut budget)?;
        ensure!(
            checker.conflict(&normalized, &mut budget)?,
            "addition {step} is not RUP"
        );
        checker.add(normalized);
    }
    budget.charge(0)
}

struct ProofWriter {
    bytes: Rc<RefCell<Vec<u8>>>,
    budget: Rc<RefCell<Budget>>,
}
impl Write for ProofWriter {
    fn write(&mut self, data: &[u8]) -> io::Result<usize> {
        self.budget
            .borrow_mut()
            .charge(data.len())
            .map_err(|e| io::Error::other(e.to_string()))?;
        self.bytes.borrow_mut().extend_from_slice(data);
        Ok(data.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        self.budget
            .borrow_mut()
            .charge(0)
            .map_err(|e| io::Error::other(e.to_string()))
    }
}

fn parse_drat(variables: usize, bytes: &[u8], budget: &mut Budget) -> Result<Vec<Vec<i32>>> {
    let text = std::str::from_utf8(bytes)?;
    let mut additions = Vec::new();
    for line in text.lines() {
        budget.charge(line.len().saturating_add(1))?;
        let mut words = line.split_whitespace().peekable();
        if words.peek().is_none() {
            continue;
        }
        let deletion = words.peek() == Some(&"d");
        if deletion {
            words.next();
        }
        let mut clause = Vec::new();
        let mut terminated = false;
        for word in words {
            ensure!(!terminated, "extra tokens after DRAT terminator");
            let literal: i32 = word.parse()?;
            if literal == 0 {
                terminated = true;
            } else {
                validate_literal(literal, variables)?;
                clause.push(literal);
            }
        }
        ensure!(terminated, "unterminated DRAT step");
        if !deletion {
            additions.push(clause);
        }
    }
    Ok(additions)
}

pub fn solve(
    variables: usize,
    clauses: &[Vec<i32>],
    deadline: Instant,
    max_work: usize,
) -> Result<SatResult> {
    ensure!(
        variables <= Var::max_count().min(i32::MAX as usize),
        "too many CNF variables"
    );
    let budget = Rc::new(RefCell::new(Budget {
        deadline,
        remaining: max_work,
    }));
    let proposal = || -> Result<SatResult> {
        budget
            .borrow_mut()
            .charge(variables.saturating_add(clauses.len()))?;
        for clause in clauses {
            budget.borrow_mut().charge(clause.len().saturating_add(1))?;
            for &literal in clause {
                validate_literal(literal, variables)?;
            }
        }
        let bytes = Rc::new(RefCell::new(Vec::new()));
        let mut solver = Solver::new();
        let interrupt_budget = Rc::clone(&budget);
        solver.set_interrupt(move || interrupt_budget.borrow_mut().charge(1).is_err());
        solver.write_proof(
            ProofWriter {
                bytes: Rc::clone(&bytes),
                budget: Rc::clone(&budget),
            },
            ProofFormat::Drat,
        );
        for _ in 0..variables {
            budget.borrow_mut().charge(1)?;
            solver.new_var();
        }
        for clause in clauses {
            budget.borrow_mut().charge(clause.len().saturating_add(1))?;
            let literals: Vec<_> = clause
                .iter()
                .map(|&literal| Lit::from_dimacs(literal as isize))
                .collect();
            solver.add_clause(&literals);
        }
        let satisfied = solver.solve()?;
        solver.close_proof()?;
        budget.borrow_mut().charge(0)?;
        if satisfied {
            let mut model = vec![false; variables];
            for literal in solver
                .model()
                .ok_or_else(|| anyhow::anyhow!("missing SAT model"))?
            {
                budget.borrow_mut().charge(1)?;
                ensure!(
                    literal.index() < variables,
                    "SAT model variable out of range"
                );
                model[literal.index()] = literal.is_positive();
            }
            for clause in clauses {
                budget.borrow_mut().charge(clause.len().saturating_add(1))?;
                ensure!(
                    clause
                        .iter()
                        .any(|&literal| model[index(literal)] == (literal > 0)),
                    "invalid SAT model"
                );
            }
            budget.borrow_mut().charge(0)?;
            Ok(SatResult::Sat(model))
        } else {
            drop(solver);
            let mut additions = parse_drat(variables, &bytes.borrow(), &mut budget.borrow_mut())?;
            if additions.last().is_none_or(|clause| !clause.is_empty()) {
                budget.borrow_mut().charge(1)?;
                additions.push(vec![]);
            }
            let remaining = budget.borrow().remaining;
            check_rup(variables, clauses, &additions, deadline, remaining)?;
            Ok(SatResult::Unsat(additions))
        }
    };
    match proposal() {
        Ok(result) => Ok(result),
        Err(error) => Ok(SatResult::Unknown(error.to_string())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(5)
    }
    fn truth_table(variables: usize, clauses: &[Vec<i32>]) -> bool {
        (0..1usize << variables).any(|mask| {
            clauses.iter().all(|clause| {
                clause
                    .iter()
                    .any(|&literal| ((mask >> index(literal)) & 1 != 0) == (literal > 0))
            })
        })
    }

    #[test]
    fn native_results_match_truth_tables_and_recheck_proofs() {
        let mut seed = 981723u64;
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for case in 0..160 {
            let variables = case % 7 + 1;
            let clauses: Vec<Vec<i32>> = (0..case % 37)
                .map(|_| {
                    (0..next() % 5)
                        .map(|_| {
                            let variable = (next() as usize % variables + 1) as i32;
                            if next() % 2 == 0 { variable } else { -variable }
                        })
                        .collect()
                })
                .collect();
            let expected = truth_table(variables, &clauses);
            match solve(variables, &clauses, deadline(), 10_000_000).unwrap() {
                SatResult::Sat(model) => {
                    assert!(expected, "case {case}");
                    assert_eq!(model.len(), variables);
                    assert!(clauses.iter().all(|clause| {
                        clause
                            .iter()
                            .any(|&literal| model[index(literal)] == (literal > 0))
                    }));
                }
                SatResult::Unsat(additions) => {
                    assert!(!expected, "case {case}");
                    check_rup(variables, &clauses, &additions, deadline(), 10_000_000).unwrap();
                }
                SatResult::Unknown(reason) => {
                    panic!("small case {case} unexpectedly unknown: {reason}")
                }
            }
        }
    }

    #[test]
    fn proof_additions_are_checked_sequentially() {
        let clauses = vec![vec![1, 2], vec![1, -2], vec![-1, 2], vec![-1, -2]];
        check_rup(2, &clauses, &[vec![1], vec![]], deadline(), 10000).unwrap();
        assert!(check_rup(2, &clauses, &[vec![]], deadline(), 10000).is_err());
        let SatResult::Unsat(proof) = solve(2, &clauses, deadline(), 10000).unwrap() else {
            panic!("expected checked UNSAT");
        };
        assert!(proof.last().unwrap().is_empty());
    }

    #[test]
    fn duplicates_tautologies_units_and_empty_input_clauses() {
        check_rup(
            2,
            &[vec![1, 1], vec![-1, -1]],
            &[vec![2, -2], vec![]],
            deadline(),
            10000,
        )
        .unwrap();
        check_rup(0, &[vec![]], &[vec![]], deadline(), 10000).unwrap();
        assert!(check_rup(1, &[vec![1, -1]], &[vec![]], deadline(), 10000).is_err());
        assert!(
            matches!(solve(0, &[], deadline(), 10000).unwrap(), SatResult::Sat(model) if model.is_empty())
        );
    }

    #[test]
    fn malformed_and_non_rup_steps_are_rejected() {
        for proof in [
            vec![],
            vec![vec![1]],
            vec![vec![], vec![1]],
            vec![vec![0], vec![]],
            vec![vec![3], vec![]],
            vec![vec![i32::MIN], vec![]],
        ] {
            assert!(check_rup(2, &[vec![1], vec![-1]], &proof, deadline(), 10000).is_err());
        }
        assert!(check_rup(1, &[], &[vec![1], vec![]], deadline(), 10000).is_err());
        assert!(check_rup(1, &[vec![0]], &[vec![]], deadline(), 10000).is_err());
    }

    #[test]
    fn drat_parser_ignores_valid_deletions_but_rejects_bad_syntax() {
        let mut budget = Budget {
            deadline: deadline(),
            remaining: 10000,
        };
        assert_eq!(
            parse_drat(2, b"1 0\nd 1 -2 0\n0\n", &mut budget).unwrap(),
            vec![vec![1], vec![]]
        );
        for bad in [
            b"1".as_slice(),
            b"1 0 2 0",
            b"a 1 0",
            b"d 0 1",
            b"3 0",
            b"-2147483648 0",
        ] {
            assert!(parse_drat(2, bad, &mut budget).is_err());
        }
    }

    #[test]
    fn expired_and_exhausted_limits_never_return_a_definitive_result() {
        let clauses = vec![vec![1], vec![-1]];
        assert!(matches!(
            solve(1, &clauses, Instant::now(), 10000).unwrap(),
            SatResult::Unknown(_)
        ));
        assert!(matches!(
            solve(1, &clauses, deadline(), 0).unwrap(),
            SatResult::Unknown(_)
        ));
        assert!(check_rup(1, &clauses, &[vec![]], deadline(), 0).is_err());
        assert!(check_rup(1, &clauses, &[vec![]], Instant::now(), 10000).is_err());
        let bytes = Rc::new(RefCell::new(Vec::new()));
        let mut writer = ProofWriter {
            bytes: Rc::clone(&bytes),
            budget: Rc::new(RefCell::new(Budget {
                deadline: deadline(),
                remaining: 2,
            })),
        };
        assert!(writer.write_all(b"1 0\n").is_err());
        assert!(bytes.borrow().is_empty());
    }

    #[test]
    fn native_interrupt_stops_search_without_waiting_for_a_proof_write() {
        let mut solver = Solver::new();
        for pair in 0..100 {
            solver.add_clause(&[
                Lit::from_dimacs(pair * 2 + 1),
                Lit::from_dimacs(pair * 2 + 2),
            ]);
        }
        let calls = Rc::new(RefCell::new(0));
        let callback_calls = Rc::clone(&calls);
        solver.set_interrupt(move || {
            *callback_calls.borrow_mut() += 1;
            *callback_calls.borrow() >= 4
        });
        assert!(matches!(
            solver.solve(),
            Err(varisat::solver::SolverError::Interrupted)
        ));
        assert_eq!(*calls.borrow(), 4);
        assert!(solver.model().is_none());
    }
}
