//! Safe-net pair reachability partitioned by the first landmark transition.
//! Only a checked inductive relation excluding the target proves unreachability.
use crate::{model::Problem, search::Outcome};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    time::{Duration, Instant},
};

const MAX_WORDS: usize = 8_000_000;
type Relations = Vec<Vec<Vec<u64>>>;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Required {
    pub place: usize,
    pub constraint: usize,
    pub negated: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Conflict {
    pub left: Required,
    pub right: Required,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub groups: Vec<Vec<usize>>,
    pub landmarks: Vec<usize>,
    pub relations: Relations,
    pub conflicts: Vec<Conflict>,
}
fn tick(deadline: Instant) -> Result<()> {
    ensure!(Instant::now() < deadline, "phase pair deadline");
    Ok(())
}
fn has(row: &[u64], place: usize) -> bool {
    row[place / 64] & (1u64 << (place % 64)) != 0
}
fn set(row: &mut [u64], place: usize) {
    row[place / 64] |= 1u64 << (place % 64);
}
fn members(row: &[u64]) -> impl Iterator<Item = usize> + '_ {
    row.iter().enumerate().flat_map(|(word, &bits)| {
        let mut bits = bits;
        std::iter::from_fn(move || {
            if bits == 0 {
                return None;
            }
            let bit = bits.trailing_zeros() as usize;
            bits &= bits - 1;
            Some(word * 64 + bit)
        })
    })
}
fn dimensions(p: &Problem) -> Result<usize> {
    let n = p.places.len();
    let words = n.div_ceil(64);
    ensure!(
        n.checked_mul(words)
            .and_then(|v| v.checked_mul(2))
            .is_some_and(|v| v <= MAX_WORDS),
        "pair relation size limit"
    );
    Ok(words)
}
fn validate_groups(p: &Problem, groups: &[Vec<usize>], deadline: Instant) -> Result<Vec<usize>> {
    let n = p.places.len();
    let mut owner = vec![usize::MAX; n];
    for (g, group) in groups.iter().enumerate() {
        tick(deadline)?;
        ensure!(
            !group.is_empty() && group.windows(2).all(|w| w[0] < w[1]),
            "invalid safe group"
        );
        let mut initial = 0u128;
        for &i in group {
            ensure!(i < n && owner[i] == usize::MAX, "invalid group partition");
            owner[i] = g;
            initial += u128::from(p.initial[i]);
        }
        ensure!(initial <= 1, "group initially exceeds one token");
    }
    ensure!(
        owner.iter().all(|&g| g != usize::MAX),
        "group partition omits a place"
    );
    for t in &p.transitions {
        tick(deadline)?;
        let mut delta = BTreeMap::<usize, i128>::new();
        for (sign, arcs) in [(-1, &t.pre), (1, &t.post)] {
            for &(i, w) in arcs {
                let d = delta.entry(owner[i]).or_default();
                *d = d
                    .checked_add(sign * i128::from(w))
                    .context("group arithmetic overflow")?;
            }
        }
        ensure!(
            delta.values().all(|&d| d <= 0),
            "safe group token mass increases"
        );
    }
    Ok(owner)
}
fn required(p: &Problem, r: &Required) -> Result<()> {
    let row = p.target.get(r.constraint).context("invalid target row")?;
    ensure!(
        r.place < p.places.len() && (!r.negated || row.equality),
        "invalid required place or row direction"
    );
    let sign = if r.negated { -1i128 } else { 1 };
    ensure!(
        sign * i128::from(row.coefficients[r.place]) > 0,
        "required place has no positive coefficient"
    );
    let mut upper = 0i128;
    for (i, &a) in row.coefficients.iter().enumerate() {
        if i != r.place {
            upper = upper
                .checked_add((sign * i128::from(a)).max(0))
                .context("target bound overflow")?;
        }
    }
    ensure!(
        upper < sign * i128::from(row.bound),
        "target does not require this place"
    );
    Ok(())
}
struct Encoded {
    pre: Vec<usize>,
    post: Vec<usize>,
    deleted: Vec<usize>,
    landmark: bool,
    impossible: bool,
}
fn encode(p: &Problem, landmarks: &[usize]) -> Result<Vec<Encoded>> {
    ensure!(
        landmarks.windows(2).all(|w| w[0] < w[1])
            && landmarks.iter().all(|&t| t < p.transitions.len()),
        "invalid landmarks"
    );
    Ok(p.transitions
        .iter()
        .enumerate()
        .map(|(i, t)| Encoded {
            pre: t.pre.iter().map(|&(p, _)| p).collect(),
            post: t.post.iter().map(|&(p, _)| p).collect(),
            deleted: t
                .pre
                .iter()
                .filter_map(|&(p, _)| (!t.post.iter().any(|&(q, _)| p == q)).then_some(p))
                .collect(),
            landmark: landmarks.binary_search(&i).is_ok(),
            impossible: t.pre.iter().chain(&t.post).any(|&(_, w)| w > 1),
        })
        .collect())
}
struct Closure {
    rows: Relations,
    live: Vec<Vec<u64>>,
    added: usize,
    limit: usize,
    deadline: Instant,
}
impl Closure {
    fn new(rows: Relations, limit: usize, deadline: Instant) -> Self {
        let n = rows[0].len();
        let words = n.div_ceil(64);
        let mut live = vec![vec![0; words]; 2];
        for phase in 0..2 {
            for (i, row) in rows[phase].iter().enumerate() {
                if has(row, i) {
                    set(&mut live[phase], i);
                }
            }
        }
        Self {
            rows,
            live,
            added: 0,
            limit,
            deadline,
        }
    }
    fn union(&mut self, phase: usize, i: usize, proposed: &[u64]) -> Result<bool> {
        let mut changed = false;
        for (word, &bits) in proposed.iter().enumerate() {
            tick(self.deadline)?;
            let mut fresh = bits & !self.rows[phase][i][word];
            if fresh == 0 {
                continue;
            }
            changed = true;
            self.rows[phase][i][word] |= bits;
            self.added = self.added.saturating_add(fresh.count_ones() as usize);
            while fresh != 0 {
                let j = word * 64 + fresh.trailing_zeros() as usize;
                fresh &= fresh - 1;
                if !has(&self.rows[phase][j], i) {
                    set(&mut self.rows[phase][j], i);
                    self.added = self.added.saturating_add(1);
                }
            }
            ensure!(self.added <= self.limit, "pair addition limit");
        }
        if has(&self.rows[phase][i], i) {
            set(&mut self.live[phase], i);
        }
        Ok(changed)
    }
    fn pass(&mut self, transitions: &[Encoded]) -> Result<bool> {
        let mut changed = false;
        for phase in 0..2 {
            for t in transitions {
                tick(self.deadline)?;
                if t.impossible
                    || t.pre.iter().any(|&i| !has(&self.live[phase], i))
                    || t.pre
                        .iter()
                        .any(|&i| t.pre.iter().any(|&j| !has(&self.rows[phase][i], j)))
                {
                    continue;
                }
                let mut surviving = self.live[phase].clone();
                for &i in &t.pre {
                    for (a, &b) in surviving.iter_mut().zip(&self.rows[phase][i]) {
                        *a &= b;
                    }
                }
                for &i in &t.deleted {
                    surviving[i / 64] &= !(1u64 << (i % 64));
                }
                let dest = if t.landmark { 1 } else { phase };
                if dest != phase {
                    for i in members(&surviving) {
                        let copied: Vec<_> = self.rows[phase][i]
                            .iter()
                            .zip(&surviving)
                            .map(|(&a, &b)| a & b)
                            .collect();
                        changed |= self.union(dest, i, &copied)?;
                    }
                }
                for &i in &t.post {
                    set(&mut surviving, i);
                }
                for &i in &t.post {
                    changed |= self.union(dest, i, &surviving)?;
                }
            }
        }
        Ok(changed)
    }
}

pub fn verify(p: &Problem, certificate: &Certificate, deadline: Instant) -> Result<()> {
    p.validate()?;
    tick(deadline)?;
    let n = p.places.len();
    let words = dimensions(p)?;
    ensure!(
        certificate.kind == "phase-pair-closure-v1",
        "wrong phase pair proof kind"
    );
    validate_groups(p, &certificate.groups, deadline)?;
    ensure!(
        certificate.relations.len() == 2 && certificate.conflicts.len() == 2,
        "expected two phases"
    );
    for rows in &certificate.relations {
        ensure!(
            rows.len() == n && rows.iter().all(|r| r.len() == words),
            "invalid relation dimensions"
        );
        for (i, row) in rows.iter().enumerate() {
            tick(deadline)?;
            if !n.is_multiple_of(64) {
                ensure!(row[words - 1] >> (n % 64) == 0, "nonzero relation padding");
            }
            for j in members(row) {
                ensure!(
                    has(&rows[j], i) && has(row, i) && has(&rows[j], j),
                    "invalid symmetric relation"
                );
            }
        }
    }
    for (i, &m) in p.initial.iter().enumerate() {
        if m > 0 {
            for (j, &v) in p.initial.iter().enumerate() {
                if v > 0 {
                    ensure!(has(&certificate.relations[0][i], j), "initial pair omitted");
                }
            }
        }
    }
    let transitions = encode(p, &certificate.landmarks)?;
    let mut closure = Closure::new(certificate.relations.clone(), usize::MAX, deadline);
    ensure!(
        !closure.pass(&transitions)?,
        "relation is not inductively closed"
    );
    for (phase, conflict) in certificate.conflicts.iter().enumerate() {
        required(p, &conflict.left)?;
        required(p, &conflict.right)?;
        ensure!(
            !has(
                &certificate.relations[phase][conflict.left.place],
                conflict.right.place
            ),
            "target conflict is present"
        );
    }
    tick(deadline)
}
fn groups(p: &Problem, deadline: Instant) -> Result<Vec<Vec<usize>>> {
    fn root(parent: &mut [usize], mut p: usize) -> usize {
        while parent[p] != p {
            parent[p] = parent[parent[p]];
            p = parent[p];
        }
        p
    }
    let mut parent: Vec<_> = (0..p.places.len()).collect();
    for t in &p.transitions {
        tick(deadline)?;
        let mut delta = BTreeMap::<usize, i128>::new();
        for (sign, arcs) in [(-1, &t.pre), (1, &t.post)] {
            for &(i, w) in arcs {
                *delta.entry(i).or_default() += sign * i128::from(w);
            }
        }
        let mut changed = delta.into_iter().filter_map(|(i, d)| (d != 0).then_some(i));
        if let Some(first) = changed.next() {
            let r = root(&mut parent, first);
            for i in changed {
                let other = root(&mut parent, i);
                parent[other] = r;
            }
        }
    }
    let mut groups = BTreeMap::<usize, Vec<usize>>::new();
    for i in 0..parent.len() {
        let r = root(&mut parent, i);
        groups.entry(r).or_default().push(i);
    }
    let mut result: Vec<_> = groups.into_values().collect();
    result.sort_unstable_by_key(|g| g[0]);
    Ok(result)
}
#[derive(Clone, Copy)]
enum Partition {
    Uniform,
    FirstLandmark,
}

fn discover(
    p: &Problem,
    deadline: Instant,
    max_pairs: usize,
    partition: Partition,
) -> Result<(Certificate, usize)> {
    p.validate()?;
    let words = dimensions(p)?;
    let n = p.places.len();
    let groups = groups(p, deadline)?;
    let owner = validate_groups(p, &groups, deadline)?;
    let mut changes = vec![Vec::new(); groups.len()];
    for (index, t) in p.transitions.iter().enumerate() {
        tick(deadline)?;
        let mut delta = BTreeMap::<usize, i128>::new();
        for (sign, arcs) in [(-1, &t.pre), (1, &t.post)] {
            for &(i, w) in arcs {
                *delta.entry(i).or_default() += sign * i128::from(w);
            }
        }
        let mut touched: Vec<_> = delta
            .into_iter()
            .filter_map(|(i, d)| (d != 0).then_some(owner[i]))
            .collect();
        touched.sort_unstable();
        touched.dedup();
        for g in touched {
            changes[g].push(index);
        }
    }
    let landmarks = changes
        .iter()
        .enumerate()
        .filter(|(_, ts)| !ts.is_empty())
        .min_by_key(|(g, ts)| (ts.len(), groups[*g][0]))
        .map(|(_, ts)| ts.clone())
        .unwrap_or_default();
    let landmarks = match partition {
        Partition::Uniform => Vec::new(),
        Partition::FirstLandmark => landmarks,
    };
    let mut relations = vec![vec![vec![0; words]; n]; 2];
    let mut initial = vec![0; words];
    for (i, &value) in p.initial.iter().enumerate() {
        if value > 0 {
            set(&mut initial, i);
        }
    }
    for i in members(&initial) {
        relations[0][i].clone_from(&initial);
    }
    let transitions = encode(p, &landmarks)?;
    let mut closure = Closure::new(relations, max_pairs, deadline);
    while closure.pass(&transitions)? {}
    let mut requirements = Vec::new();
    for (constraint, row) in p.target.iter().enumerate() {
        for negated in [false, true] {
            if negated && !row.equality {
                continue;
            }
            let sign = if negated { -1i128 } else { 1 };
            let upper: i128 = row
                .coefficients
                .iter()
                .map(|&a| (sign * i128::from(a)).max(0))
                .sum();
            for (place, &a) in row.coefficients.iter().enumerate() {
                if sign * i128::from(a) > 0
                    && upper - sign * i128::from(a) < sign * i128::from(row.bound)
                {
                    requirements.push(Required {
                        place,
                        constraint,
                        negated,
                    });
                }
            }
        }
    }
    let mut conflicts = Vec::new();
    for phase in 0..2 {
        let conflict = requirements.iter().find_map(|left| {
            requirements
                .iter()
                .find(|right| !has(&closure.rows[phase][left.place], right.place))
                .map(|right| Conflict {
                    left: left.clone(),
                    right: right.clone(),
                })
        });
        conflicts.push(conflict.context("closed pair abstraction does not exclude target")?);
    }
    let certificate = Certificate {
        kind: "phase-pair-closure-v1".into(),
        groups,
        landmarks,
        relations: closure.rows,
        conflicts,
    };
    verify(p, &certificate, deadline)?;
    Ok((certificate, closure.added))
}
pub fn solve(p: &Problem, timeout: Duration, max_pairs: usize) -> Outcome {
    solve_partition(p, timeout, max_pairs, Partition::FirstLandmark)
}

pub fn solve_uniform(p: &Problem, timeout: Duration, max_pairs: usize) -> Outcome {
    solve_partition(p, timeout, max_pairs, Partition::Uniform)
}

fn solve_partition(
    p: &Problem,
    timeout: Duration,
    max_pairs: usize,
    partition: Partition,
) -> Outcome {
    let method = match partition {
        Partition::Uniform => "pair",
        Partition::FirstLandmark => "phase-pair",
    };
    let Some(deadline) = Instant::now().checked_add(timeout) else {
        return Outcome::unknown(method, "invalid deadline", 0);
    };
    match discover(p, deadline, max_pairs, partition) {
        Ok((certificate, added)) => Outcome {
            verdict: "unreachable",
            method: method.into(),
            reason: match partition {
                Partition::Uniform => "checked uniform pair closure excludes target",
                Partition::FirstLandmark => "checked two-phase pair closure excludes target",
            }
            .into(),
            states: added,
            trace: vec![],
            marking: None,
            certificate: None,
            proof: Some(serde_json::to_value(certificate).unwrap()),
        },
        Err(e) => Outcome::unknown(method, &e.to_string(), 0),
    }
}
