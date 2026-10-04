//! Exact finite-path CNF for a certified acyclic one-hot control projection.
use crate::{control, model::Problem};
use anyhow::{Context, Result, ensure};
use num_bigint::BigUint;
use num_traits::One;
use std::{
    collections::{BTreeMap, BTreeSet},
    time::Instant,
};

pub struct Encoding {
    pub variables: usize,
    pub clauses: Vec<Vec<i32>>,
    /// Original transition and selection literal, in execution-compatible order.
    pub choices: Vec<(usize, i32)>,
}

struct Builder {
    encoding: Encoding,
    gates: BTreeMap<(u8, i32, i32), i32>,
    deadline: Instant,
    remaining: usize,
}

impl Builder {
    fn charge(&mut self, amount: usize) -> Result<()> {
        ensure!(
            Instant::now() < self.deadline,
            "DAG encoding deadline exhausted"
        );
        self.remaining = self
            .remaining
            .checked_sub(amount)
            .context("DAG encoding work limit exhausted")?;
        Ok(())
    }
    fn variable(&mut self) -> Result<i32> {
        self.charge(1)?;
        self.encoding.variables += 1;
        i32::try_from(self.encoding.variables).context("DAG variable index overflow")
    }
    fn clause(&mut self, literals: Vec<i32>) -> Result<()> {
        self.charge(literals.len().saturating_add(1))?;
        self.encoding.clauses.push(literals);
        Ok(())
    }
    fn and(&mut self, a: i32, b: i32) -> Result<i32> {
        self.charge(1)?;
        if a == -1 || b == -1 || a == -b {
            return Ok(-1);
        }
        if a == 1 {
            return Ok(b);
        }
        if b == 1 || a == b {
            return Ok(a);
        }
        let (a, b) = (a.min(b), a.max(b));
        if let Some(&z) = self.gates.get(&(0, a, b)) {
            return Ok(z);
        }
        let z = self.variable()?;
        self.clause(vec![-z, a])?;
        self.clause(vec![-z, b])?;
        self.clause(vec![z, -a, -b])?;
        self.gates.insert((0, a, b), z);
        Ok(z)
    }
    fn xor(&mut self, a: i32, b: i32) -> Result<i32> {
        self.charge(1)?;
        if a == b {
            return Ok(-1);
        }
        if a == -b {
            return Ok(1);
        }
        if a == -1 {
            return Ok(b);
        }
        if b == -1 {
            return Ok(a);
        }
        if a == 1 {
            return Ok(-b);
        }
        if b == 1 {
            return Ok(-a);
        }
        let (a, b) = (a.min(b), a.max(b));
        if let Some(&z) = self.gates.get(&(1, a, b)) {
            return Ok(z);
        }
        let z = self.variable()?;
        self.clause(vec![-a, -b, -z])?;
        self.clause(vec![a, b, -z])?;
        self.clause(vec![a, -b, z])?;
        self.clause(vec![-a, b, z])?;
        self.gates.insert((1, a, b), z);
        Ok(z)
    }
    fn or(&mut self, a: i32, b: i32) -> Result<i32> {
        Ok(-self.and(-a, -b)?)
    }
    fn mux(&mut self, s: i32, t: i32, f: i32) -> Result<i32> {
        self.charge(1)?;
        if s == 1 || t == f {
            return Ok(t);
        }
        if s == -1 {
            return Ok(f);
        }
        let left = self.and(s, t)?;
        let right = self.and(-s, f)?;
        self.or(left, right)
    }
    fn constant(&mut self, n: &BigUint, width: usize) -> Result<Vec<i32>> {
        self.charge(width)?;
        Ok((0..width)
            .map(|i| if n.bit(i as u64) { 1 } else { -1 })
            .collect())
    }
    fn add(&mut self, a: &[i32], b: &[i32]) -> Result<Vec<i32>> {
        ensure!(a.len() == b.len(), "DAG bit width mismatch");
        self.charge(a.len())?;
        let mut carry = -1;
        let mut result = Vec::with_capacity(a.len());
        for (&a, &b) in a.iter().zip(b) {
            let x = self.xor(a, b)?;
            result.push(self.xor(x, carry)?);
            let ab = self.and(a, b)?;
            let xc = self.and(x, carry)?;
            carry = self.or(ab, xc)?;
        }
        Ok(result)
    }
    fn ge(&mut self, a: &[i32], b: &[i32]) -> Result<i32> {
        ensure!(a.len() == b.len(), "DAG bit width mismatch");
        let mut result = 1;
        for (&a, &b) in a.iter().zip(b) {
            let greater = self.and(a, -b)?;
            let different = self.xor(a, b)?;
            let equal_prefix = self.and(-different, result)?;
            result = self.or(greater, equal_prefix)?;
        }
        Ok(result)
    }
    fn at_most_one(&mut self, literals: &[i32]) -> Result<()> {
        for (i, &a) in literals.iter().enumerate() {
            for &b in &literals[i + 1..] {
                self.clause(vec![-a, -b])?;
            }
        }
        Ok(())
    }
    fn multiply(&mut self, bits: &[i32], coefficient: u64, width: usize) -> Result<Vec<i32>> {
        self.charge(width)?;
        let mut result = vec![-1; width];
        for shift in 0..64 {
            if (coefficient >> shift) & 1 == 0 {
                continue;
            }
            self.charge(width)?;
            let mut term = vec![-1; width];
            for (i, &bit) in bits.iter().enumerate() {
                if i + shift < width {
                    term[i + shift] = bit;
                }
            }
            result = self.add(&result, &term)?;
        }
        Ok(result)
    }
}

fn width(bound: &BigUint) -> Result<usize> {
    usize::try_from(bound.bits().max(1)).context("DAG bit width overflow")
}

pub fn encode(
    p: &Problem,
    control_places: &[usize],
    deadline: Instant,
    max_work: usize,
) -> Result<Encoding> {
    encode_impl(p, control_places, deadline, max_work, true)
}

pub fn encode_legacy(
    p: &Problem,
    control_places: &[usize],
    deadline: Instant,
    max_work: usize,
) -> Result<Encoding> {
    encode_impl(p, control_places, deadline, max_work, false)
}

fn encode_impl(
    p: &Problem,
    control_places: &[usize],
    deadline: Instant,
    max_work: usize,
    derive_control_markings: bool,
) -> Result<Encoding> {
    let mut b = Builder {
        encoding: Encoding {
            variables: 0,
            clauses: vec![],
            choices: vec![],
        },
        gates: BTreeMap::new(),
        deadline,
        remaining: max_work,
    };
    b.charge(p.places.len())?;
    b.charge(p.transitions.len())?;
    for t in &p.transitions {
        b.charge(t.pre.len().saturating_add(t.post.len()))?;
    }
    for c in &p.target {
        b.charge(c.coefficients.len())?;
    }
    let control = control::build_until(
        p,
        control_places,
        p.transitions.len().min(max_work),
        deadline,
    )?;
    let mut selected_control = vec![false; p.places.len()];
    for &place in &control.places {
        selected_control[place] = true;
    }
    b.charge(control.edges.len())?;
    let mut incoming = vec![Vec::new(); control.modes.len()];
    let mut outgoing = vec![Vec::new(); control.modes.len()];
    for (i, e) in control.edges.iter().enumerate() {
        incoming[e.target].push(i);
        outgoing[e.source].push(i);
    }
    let mut indegree: Vec<_> = incoming.iter().map(Vec::len).collect();
    let mut ready = BTreeSet::new();
    for (mode, &degree) in indegree.iter().enumerate() {
        if degree == 0 {
            ready.insert((control.modes[mode], mode));
        }
    }
    let mut topological = Vec::new();
    while let Some((_, mode)) = ready.pop_first() {
        b.charge(1)?;
        topological.push(mode);
        for &edge in &outgoing[mode] {
            let target = control.edges[edge].target;
            indegree[target] -= 1;
            if indegree[target] == 0 {
                ready.insert((control.modes[target], target));
            }
        }
    }
    ensure!(
        topological.len() == control.modes.len(),
        "reachable control graph is cyclic or stuttering"
    );
    let mut ordered_edges = Vec::new();
    for &mode in &topological {
        outgoing[mode].sort_by_key(|&i| control.edges[i].transition);
        ordered_edges.extend_from_slice(&outgoing[mode]);
    }
    ensure!(b.variable()? == 1, "DAG constant allocation failed");
    b.clause(vec![1])?;
    let mut choice = vec![0; control.edges.len()];
    for &i in &ordered_edges {
        let literal = b.variable()?;
        choice[i] = literal;
        b.encoding
            .choices
            .push((control.edges[i].transition, literal));
    }
    for &mode in &topological {
        incoming[mode].sort_by_key(|&i| choice[i]);
        let ins: Vec<_> = incoming[mode].iter().map(|&i| choice[i]).collect();
        let outs: Vec<_> = outgoing[mode].iter().map(|&i| choice[i]).collect();
        b.at_most_one(&ins)?;
        b.at_most_one(&outs)?;
        if mode != control.initial {
            for &literal in &outs {
                let mut clause = vec![-literal];
                clause.extend_from_slice(&ins);
                b.clause(clause)?;
            }
        }
    }
    let mut upper: Vec<_> = p.initial.iter().map(|&n| BigUint::from(n)).collect();
    let mut effects = Vec::with_capacity(ordered_edges.len());
    for &i in &ordered_edges {
        let t = &p.transitions[control.edges[i].transition];
        let mut delta = BTreeMap::<usize, i128>::new();
        for &(place, w) in &t.pre {
            *delta.entry(place).or_default() -= i128::from(w);
        }
        for &(place, w) in &t.post {
            *delta.entry(place).or_default() += i128::from(w);
        }
        delta.retain(|_, d| *d != 0);
        for (&place, &d) in &delta {
            b.charge(1)?;
            if d > 0 {
                upper[place] += BigUint::from(d as u128);
            }
        }
        effects.push(delta);
    }
    for &place in &control.places {
        upper[place] = BigUint::one();
    }
    let mut markings = Vec::with_capacity(p.places.len());
    for (place, &initial) in p.initial.iter().enumerate() {
        markings.push(b.constant(&BigUint::from(initial), width(&upper[place])?)?);
    }
    for (&edge, delta) in ordered_edges.iter().zip(&effects) {
        let selected = choice[edge];
        let t = &p.transitions[control.edges[edge].transition];
        let mut pre = t.pre.clone();
        pre.sort_unstable_by_key(|&(place, _)| place);
        for &(place, w) in &pre {
            if derive_control_markings && selected_control[place] {
                continue;
            }
            if BigUint::from(w) > upper[place] {
                b.clause(vec![-selected])?;
            } else {
                let constant = b.constant(&BigUint::from(w), markings[place].len())?;
                let enabled = b.ge(&markings[place], &constant)?;
                b.clause(vec![-selected, enabled])?;
            }
        }
        for (&place, &d) in delta {
            if derive_control_markings && selected_control[place] {
                continue;
            }
            let width = markings[place].len();
            let modulus = BigUint::one() << width;
            let value = if d >= 0 {
                BigUint::from(d as u128) % &modulus
            } else {
                (&modulus - (BigUint::from(d.unsigned_abs()) % &modulus)) % &modulus
            };
            let constant = b.constant(&value, width)?;
            let updated = b.add(&markings[place], &constant)?;
            let mut next = Vec::with_capacity(width);
            for (&new, &old) in updated.iter().zip(&markings[place]) {
                next.push(b.mux(selected, new, old)?);
            }
            markings[place] = next;
        }
    }
    if derive_control_markings {
        for &place in &control.places {
            markings[place] = vec![-1];
        }
        for &mode in &topological {
            let mut entered = if mode == control.initial { 1 } else { -1 };
            for &edge in &incoming[mode] {
                entered = b.or(entered, choice[edge])?;
            }
            let mut left = -1;
            for &edge in &outgoing[mode] {
                left = b.or(left, choice[edge])?;
            }
            markings[control.modes[mode]] = vec![b.and(entered, -left)?];
        }
    }
    for c in &p.target {
        let left_constant = if c.bound < 0 {
            c.bound.unsigned_abs()
        } else {
            0
        };
        let right_constant = if c.bound > 0 { c.bound as u64 } else { 0 };
        let mut left_bound = BigUint::from(left_constant);
        let mut right_bound = BigUint::from(right_constant);
        for (&coefficient, bound) in c.coefficients.iter().zip(&upper) {
            b.charge(1)?;
            if coefficient > 0 {
                left_bound += bound * BigUint::from(coefficient as u64);
            } else if coefficient < 0 {
                right_bound += bound * BigUint::from(coefficient.unsigned_abs());
            }
        }
        let width = width(&left_bound.max(right_bound))?;
        let mut left = b.constant(&BigUint::from(left_constant), width)?;
        let mut right = b.constant(&BigUint::from(right_constant), width)?;
        for (place, &coefficient) in c.coefficients.iter().enumerate() {
            if coefficient == 0 {
                continue;
            }
            let term = b.multiply(&markings[place], coefficient.unsigned_abs(), width)?;
            if coefficient > 0 {
                left = b.add(&left, &term)?;
            } else {
                right = b.add(&right, &term)?;
            }
        }
        if c.equality {
            for (&a, &c) in left.iter().zip(&right) {
                b.clause(vec![-a, c])?;
                b.clause(vec![a, -c])?;
            }
        } else {
            let accepted = b.ge(&left, &right)?;
            b.clause(vec![accepted])?;
        }
    }
    b.charge(0)?;
    Ok(b.encoding)
}
