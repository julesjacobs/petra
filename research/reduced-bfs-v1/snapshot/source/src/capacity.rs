//! Target-directed proposals for nonincreasing 0/1 place potentials.
//!
//! NUPN ancestry and single-input implications only propose supports. Original
//! weighted arcs certify each support; target refutations use the ordinary
//! state-equation certificate checker.
use crate::{
    linear,
    model::{Constraint, Problem},
    place_bounds,
    search::Outcome,
};
use num_bigint::BigInt;
use num_traits::{Signed, Zero};
use roxmltree::{Document, Node, ParsingOptions};
use std::{
    collections::{HashMap, HashSet},
    time::Instant,
};

const MAX_SEEDS: usize = 64;
const MAX_XML_BYTES: usize = 32 * 1024 * 1024;
const MAX_XML_NODES: u32 = 1_500_000;

struct Work {
    deadline: Instant,
    remaining: usize,
}

impl Work {
    fn take(&mut self, count: usize) -> Option<()> {
        if Instant::now() >= self.deadline {
            return None;
        }
        self.remaining = self.remaining.checked_sub(count)?;
        Some(())
    }
}

#[derive(Default)]
pub struct Capacities {
    potentials: Vec<(Vec<usize>, BigInt)>,
}

impl Capacities {
    /// The standard proof object lets other engines independently reuse bounds.
    pub fn certificate(&self) -> place_bounds::Certificate {
        place_bounds::Certificate {
            potentials: self
                .potentials
                .iter()
                .map(|(support, _)| place_bounds::Potential {
                    weights: support.iter().map(|&p| (p, "1".into())).collect(),
                })
                .collect(),
            ..Default::default()
        }
    }

    pub fn len(&self) -> usize {
        self.potentials.len()
    }

    pub fn is_empty(&self) -> bool {
        self.potentials.is_empty()
    }

    /// Recheck the final certificate against this exact original query.
    pub fn refute(&self, problem: &Problem, deadline: Instant) -> Option<Outcome> {
        let mut row = problem.places.len();
        for target in &problem.target {
            for sign in if target.equality {
                &[-1_i32, 1][..]
            } else {
                &[1_i32][..]
            } {
                if Instant::now() >= deadline {
                    return None;
                }
                let empty = (vec![], BigInt::zero());
                for (support, mass) in std::iter::once(&empty).chain(&self.potentials) {
                    if Instant::now() >= deadline {
                        return None;
                    }
                    let Some(proof) = contradiction(target, *sign, row, support, mass) else {
                        continue;
                    };
                    let value = serde_json::to_value(proof).ok()?;
                    if Instant::now() >= deadline {
                        return None;
                    }
                    if linear::verify_certificate(problem, &value).is_err() {
                        continue;
                    }
                    if Instant::now() >= deadline {
                        return None;
                    }
                    let mut outcome = Outcome::unknown(
                        "checked-capacity",
                        "structural potential gives an exact state-equation refutation",
                        self.len(),
                    );
                    outcome.verdict = "unreachable";
                    outcome.proof = Some(value);
                    return Some(outcome);
                }
                row += 1;
            }
        }
        None
    }
}

fn contradiction(
    target: &Constraint,
    sign: i32,
    row: usize,
    support: &[usize],
    mass: &BigInt,
) -> Option<linear::Certificate> {
    let mut alpha = BigInt::zero();
    for (place, &coefficient) in target.coefficients.iter().enumerate() {
        let coefficient = BigInt::from(coefficient) * sign;
        if coefficient.is_positive() {
            if support.binary_search(&place).is_err() {
                return None;
            }
            alpha = alpha.max(coefficient);
        }
    }
    if BigInt::from(target.bound) * sign <= &alpha * mass {
        return None;
    }
    let mut multipliers = Vec::new();
    for (place, &coefficient) in target.coefficients.iter().enumerate() {
        let mut weight = -BigInt::from(coefficient) * sign;
        if support.binary_search(&place).is_ok() {
            weight += &alpha;
        }
        if weight.is_positive() {
            multipliers.push((place, weight.to_string()));
        }
    }
    multipliers.push((row, "1".into()));
    Some(linear::Certificate {
        kind: "sparse-farkas-v1".into(),
        multipliers,
    })
}

/// Prioritize all positive target coordinates, including negated equalities.
pub fn target_places(targets: &[Vec<Constraint>]) -> Vec<usize> {
    let mut seen = HashSet::new();
    let mut seeds = Vec::new();
    for target in targets.iter().flatten() {
        for (place, &coefficient) in target.coefficients.iter().enumerate() {
            if (coefficient > 0 || (target.equality && coefficient < 0)) && seen.insert(place) {
                seeds.push(place);
                if seeds.len() == MAX_SEEDS {
                    return seeds;
                }
            }
        }
    }
    seeds
}

struct Units {
    places: Vec<Vec<usize>>,
    parent: Vec<Option<usize>>,
    owner: Vec<Option<usize>>,
}

fn child<'a, 'input>(node: Node<'a, 'input>, name: &str) -> Option<Node<'a, 'input>> {
    let mut matches = node
        .children()
        .filter(|n| n.is_element() && n.tag_name().name() == name);
    let result = matches.next()?;
    if matches.next().is_some() {
        return None;
    }
    Some(result)
}

fn words(node: Node<'_, '_>) -> Option<String> {
    if node.children().any(|n| n.is_element()) {
        return None;
    }
    Some(
        node.children()
            .filter(|n| n.is_text())
            .filter_map(|n| n.text())
            .collect(),
    )
}

impl Units {
    fn parse(xml: &str, problem: &Problem, work: &mut Work) -> Option<Self> {
        work.take(1)?;
        if xml.len() > MAX_XML_BYTES {
            return None;
        }
        work.take(xml.len().div_ceil(64))?;
        if !xml.contains("nupn") {
            return None;
        }
        let document = Document::parse_with_options(
            xml,
            ParsingOptions {
                nodes_limit: u32::try_from(work.remaining)
                    .unwrap_or(u32::MAX)
                    .min(MAX_XML_NODES),
                ..Default::default()
            },
        )
        .ok()?;
        let mut metadata = None;
        for node in document.descendants() {
            work.take(1)?;
            if node.is_element()
                && node.tag_name().name() == "toolspecific"
                && node.attribute("tool") == Some("nupn")
                && metadata.replace(node).is_some()
            {
                return None;
            }
        }
        let structure = child(metadata?, "structure")?;
        let nodes: Vec<_> = structure.children().filter(|n| n.is_element()).collect();
        let mut ids = HashMap::new();
        for (index, node) in nodes.iter().enumerate() {
            work.take(1)?;
            if node.tag_name().name() != "unit"
                || ids.insert(node.attribute("id")?, index).is_some()
            {
                return None;
            }
        }
        let root = *ids.get(structure.attribute("root")?)?;
        work.take(problem.places.len() + nodes.len() * 3)?;
        let place_ids: HashMap<_, _> = problem
            .places
            .iter()
            .enumerate()
            .map(|(p, name)| (name.as_str(), p))
            .collect();
        let mut result = Self {
            places: vec![vec![]; nodes.len()],
            parent: vec![None; nodes.len()],
            owner: vec![None; problem.places.len()],
        };
        let mut children = vec![vec![]; nodes.len()];
        for (unit, node) in nodes.iter().enumerate() {
            for name in words(child(*node, "places")?)?.split_whitespace() {
                work.take(1)?;
                let place = *place_ids.get(name)?;
                if result.owner[place].replace(unit).is_some() {
                    return None;
                }
                result.places[unit].push(place);
            }
            for name in words(child(*node, "subunits")?)?.split_whitespace() {
                work.take(1)?;
                let subunit = *ids.get(name)?;
                if result.parent[subunit].replace(unit).is_some() {
                    return None;
                }
                children[unit].push(subunit);
            }
        }
        if result.parent[root].is_some() {
            return None;
        }
        let mut seen = vec![false; nodes.len()];
        let mut pending = vec![root];
        let mut count = 0;
        while let Some(unit) = pending.pop() {
            work.take(1)?;
            if std::mem::replace(&mut seen[unit], true) {
                return None;
            }
            count += 1;
            pending.extend(&children[unit]);
        }
        if count != nodes.len() {
            return None;
        }
        Some(result)
    }

    fn support(&self, place: usize, work: &mut Work) -> Option<Vec<usize>> {
        let mut unit = Some(*self.owner.get(place)?.as_ref()?);
        let mut support = Vec::new();
        while let Some(index) = unit {
            work.take(self.places[index].len() + 1)?;
            support.extend(&self.places[index]);
            unit = self.parent[index];
        }
        support.sort_unstable();
        Some(support)
    }
}

fn initial_mass(problem: &Problem, support: &[usize], work: &mut Work) -> Option<BigInt> {
    if support.is_empty() || !support.windows(2).all(|pair| pair[0] < pair[1]) {
        return None;
    }
    work.take(problem.places.len())?;
    let mut selected = vec![false; problem.places.len()];
    let mut initial = 0_u128;
    for &place in support {
        *selected.get_mut(place)? = true;
        initial = initial.checked_add(u128::from(*problem.initial.get(place)?))?;
    }
    for transition in &problem.transitions {
        work.take(transition.pre.len() + transition.post.len() + 1)?;
        let sum = |arcs: &[(usize, u64)]| -> Option<u128> {
            arcs.iter().try_fold(0_u128, |sum, &(p, weight)| {
                if *selected.get(p)? {
                    sum.checked_add(u128::from(weight))
                } else {
                    Some(sum)
                }
            })
        };
        if sum(&transition.post)? > sum(&transition.pre)? {
            return None;
        }
    }
    Some(BigInt::from(initial))
}

/// Work-limited discovery; exhausted or malformed hints only lose candidates.
pub fn discover(
    problem: &Problem,
    xml: &str,
    seeds: &[usize],
    deadline: Instant,
    max_work: usize,
) -> Capacities {
    let mut result = Capacities::default();
    let mut work = Work {
        deadline,
        remaining: max_work,
    };
    if seeds.is_empty() || work.take(1).is_none() {
        return result;
    }
    let mut attempted = HashSet::new();
    if let Some(units) = Units::parse(xml, problem, &mut work) {
        for &place in seeds.iter().take(MAX_SEEDS) {
            let Some(support) = units.support(place, &mut work) else {
                continue;
            };
            if attempted.insert(support.clone())
                && let Some(mass) = initial_mass(problem, &support, &mut work)
            {
                result.potentials.push((support, mass));
            }
        }
    }
    if work.take(problem.places.len()).is_none() {
        return result;
    }
    let mut implications = vec![Vec::new(); problem.places.len()];
    for transition in &problem.transitions {
        if work
            .take(transition.pre.len() + transition.post.len() + 1)
            .is_none()
        {
            return result;
        }
        if let [(source, 1)] = transition.pre.as_slice() {
            for &(place, _) in &transition.post {
                let Some(parents) = implications.get_mut(place) else {
                    return result;
                };
                parents.push(*source);
            }
        }
    }
    for &seed in seeds.iter().take(MAX_SEEDS) {
        if result
            .potentials
            .iter()
            .any(|(support, mass)| mass <= &BigInt::from(1) && support.binary_search(&seed).is_ok())
        {
            continue;
        }
        if seed >= problem.places.len() || work.take(problem.places.len()).is_none() {
            break;
        }
        let mut selected = vec![false; problem.places.len()];
        selected[seed] = true;
        let mut pending = vec![seed];
        while let Some(place) = pending.pop() {
            if work.take(implications[place].len() + 1).is_none() {
                return result;
            }
            for &parent in &implications[place] {
                let Some(included) = selected.get_mut(parent) else {
                    return result;
                };
                if !std::mem::replace(included, true) {
                    pending.push(parent);
                }
            }
        }
        let support: Vec<_> = selected
            .into_iter()
            .enumerate()
            .filter_map(|(p, included)| included.then_some(p))
            .collect();
        if attempted.insert(support.clone())
            && let Some(mass) = initial_mass(problem, &support, &mut work)
        {
            result.potentials.push((support, mass));
        }
    }
    result
}

/// Give each target row a seed before taking another coordinate from that row.
pub fn target_places_by_row(targets: &[Vec<Constraint>]) -> Vec<usize> {
    let mut rows: Vec<_> = targets
        .iter()
        .flatten()
        .map(|row| {
            row.coefficients
                .iter()
                .enumerate()
                .filter_map(|(place, &coefficient)| {
                    (coefficient > 0 || (row.equality && coefficient < 0)).then_some(place)
                })
                .collect::<Vec<_>>()
        })
        .filter(|row| !row.is_empty())
        .collect();
    rows.sort_by_key(Vec::len);
    let mut iterators: Vec<_> = rows.into_iter().map(Vec::into_iter).collect();
    let mut seen = HashSet::new();
    let mut result = Vec::new();
    loop {
        let mut advanced = false;
        for row in &mut iterators {
            if let Some(place) = row.next() {
                advanced = true;
                if seen.insert(place) {
                    result.push(place);
                    if result.len() == MAX_SEEDS {
                        return result;
                    }
                }
            }
        }
        if !advanced {
            return result;
        }
    }
}

impl Capacities {
    /// Sum two signed target rows and reuse the original sparse Farkas checker.
    pub fn refute_combined(
        &self,
        problem: &Problem,
        deadline: Instant,
        max_work: usize,
    ) -> Option<Outcome> {
        if let Some(outcome) = self.refute(problem, deadline) {
            return Some(outcome);
        }
        let mut work = Work {
            deadline,
            remaining: max_work,
        };
        let mut rows = Vec::new();
        for target in &problem.target {
            if target.equality {
                rows.push((target, -1));
            }
            rows.push((target, 1));
        }
        for left in 0..rows.len() {
            for right in left + 1..rows.len() {
                work.take(problem.places.len() + 1)?;
                let (a, sa) = rows[left];
                let (b, sb) = rows[right];
                let coefficients: Vec<BigInt> = a
                    .coefficients
                    .iter()
                    .zip(&b.coefficients)
                    .map(|(&a, &b)| BigInt::from(a) * sa + BigInt::from(b) * sb)
                    .collect();
                let bound = BigInt::from(a.bound) * sa + BigInt::from(b.bound) * sb;
                let empty = (vec![], BigInt::zero());
                for (support, mass) in std::iter::once(&empty).chain(&self.potentials) {
                    work.take(coefficients.len() + 1)?;
                    let mut alpha = BigInt::zero();
                    let mut covered = true;
                    for (place, coefficient) in coefficients.iter().enumerate() {
                        if coefficient.is_positive() {
                            if support.binary_search(&place).is_err() {
                                covered = false;
                                break;
                            }
                            alpha = alpha.max(coefficient.clone());
                        }
                    }
                    if !covered || bound <= &alpha * mass {
                        continue;
                    }
                    work.take(coefficients.len() + 1)?;
                    let mut multipliers = Vec::new();
                    for (place, coefficient) in coefficients.iter().enumerate() {
                        let mut weight = -coefficient;
                        if support.binary_search(&place).is_ok() {
                            weight += &alpha;
                        }
                        if weight.is_positive() {
                            multipliers.push((place, weight.to_string()));
                        }
                    }
                    multipliers.push((problem.places.len() + left, "1".into()));
                    multipliers.push((problem.places.len() + right, "1".into()));
                    let proof = serde_json::to_value(linear::Certificate {
                        kind: "sparse-farkas-v1".into(),
                        multipliers,
                    })
                    .ok()?;
                    work.take(1)?;
                    if linear::verify_certificate(problem, &proof).is_err() {
                        continue;
                    }
                    work.take(1)?;
                    let mut outcome = Outcome::unknown(
                        "checked-capacity-combined",
                        "sum of target rows contradicts a checked structural potential",
                        self.len(),
                    );
                    outcome.verdict = "unreachable";
                    outcome.proof = Some(proof);
                    return Some(outcome);
                }
            }
        }
        None
    }
}

pub fn solve(problem: &Problem, timeout: std::time::Duration, max_work: usize) -> Outcome {
    let start = Instant::now();
    let Some(deadline) = start.checked_add(timeout) else {
        return Outcome::unknown("capacity", "invalid deadline", 0);
    };
    if problem.validate().is_err() || start >= deadline {
        return Outcome::unknown("capacity", "invalid problem or exhausted deadline", 0);
    }
    let seeds = target_places_by_row(std::slice::from_ref(&problem.target));
    let discovery_deadline =
        (start + (timeout / 2).min(std::time::Duration::from_millis(500))).min(deadline);
    let capacities = discover(problem, "", &seeds, discovery_deadline, max_work);
    capacities
        .refute_combined(problem, deadline, max_work)
        .unwrap_or_else(|| {
            Outcome::unknown(
                "capacity",
                "no checked capacity refutation within limits",
                capacities.len(),
            )
        })
}
