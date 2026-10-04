//! Discovery of checked component invariants for original raw queries.
use crate::raw_invariant::{Certificate, Credit, Edge, Node};
use crate::raw_target::RawQuery;
use anyhow::{Result, anyhow, ensure};
use num_bigint::BigInt;
use num_traits::{Signed, ToPrimitive, Zero};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::time::Instant;

type Vector = BTreeMap<usize, BigInt>;
type Coefficients = Vec<(usize, u64)>;

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self) -> Result<()> {
        self.spend(1)
    }

    fn spend(&mut self, work: usize) -> Result<()> {
        ensure!(
            Instant::now() < self.deadline,
            "raw invariant discovery deadline"
        );
        self.remaining = self
            .remaining
            .checked_sub(work)
            .ok_or_else(|| anyhow!("raw invariant discovery work limit"))?;
        Ok(())
    }
}

fn add(vector: &mut Vector, place: usize, amount: BigInt) {
    let value = vector.entry(place).or_default();
    *value += amount;
    if value.is_zero() {
        vector.remove(&place);
    }
}

fn vector(terms: &[(usize, u64)]) -> Vector {
    terms.iter().map(|&(p, w)| (p, w.into())).collect()
}

fn credits(q: &RawQuery, budget: &mut Budget) -> Result<Vec<Credit>> {
    let zeros: HashSet<_> = q.target.zero_places.iter().copied().collect();
    let responses: HashSet<_> = q.target.response_places.iter().copied().collect();
    let mut found = BTreeMap::new();
    for tr in &q.transitions {
        budget.tick()?;
        if let [(place, weight)] = tr.pre.as_slice()
            && zeros.contains(place)
            && tr
                .post
                .iter()
                .all(|(p, w)| responses.contains(p) && w % weight == 0)
        {
            let mut terms: Vec<_> = tr.post.iter().map(|&(p, w)| (p, w / weight)).collect();
            terms.sort_unstable();
            found.entry(*place).or_insert(terms);
        }
    }
    Ok(found
        .into_iter()
        .map(|(place, terms)| Credit { place, terms })
        .collect())
}

struct Component {
    base: Vector,
    periods: Vec<Vector>,
    exact: HashMap<Vector, usize>,
}

fn coefficients(
    target: &Vector,
    component: &Component,
    budget: &mut Budget,
) -> Result<Option<Coefficients>> {
    budget.tick()?;
    if target.values().any(Signed::is_negative) {
        return Ok(None);
    }
    if target.is_empty() {
        return Ok(Some(vec![]));
    }
    if let Some(&index) = component.exact.get(target) {
        return Ok(Some(vec![(index, 1)]));
    }
    let mut eligible = vec![];
    for (index, period) in component.periods.iter().enumerate() {
        budget.tick()?;
        if !period.is_empty()
            && period
                .iter()
                .all(|(p, w)| target.get(p).is_some_and(|v| v >= w))
        {
            eligible.push(index);
        }
    }
    ensure!(
        eligible.len() <= 128,
        "raw invariant coefficient search dimension limit"
    );
    fn search(
        target: &Vector,
        indices: &[usize],
        component: &Component,
        budget: &mut Budget,
    ) -> Result<Option<Coefficients>> {
        budget.tick()?;
        if target.is_empty() {
            return Ok(Some(vec![]));
        }
        let Some((&index, rest)) = indices.split_first() else {
            return Ok(None);
        };
        let period = &component.periods[index];
        let bound = period
            .iter()
            .map(|(p, w)| target.get(p).cloned().unwrap_or_default() / w)
            .min()
            .unwrap();
        let Some(bound) = bound.to_u64() else {
            return Err(anyhow!("raw invariant coefficient exceeds u64"));
        };
        let mut residual = target.clone();
        for (&p, w) in period {
            add(&mut residual, p, -(w * bound));
        }
        for amount in (0..=bound).rev() {
            budget.tick()?;
            if let Some(mut found) = search(&residual, rest, component, budget)? {
                if amount != 0 {
                    found.insert(0, (index, amount));
                }
                return Ok(Some(found));
            }
            for (&p, w) in period {
                add(&mut residual, p, w.clone());
            }
        }
        Ok(None)
    }
    search(target, &eligible, component, budget)
}

#[derive(Clone)]
struct Transfer {
    component: usize,
    base: Coefficients,
    periods: Vec<Coefficients>,
}

struct Maps {
    components: Vec<Component>,
    transfers: HashMap<(usize, Vector), Option<Transfer>>,
    periods: HashMap<(usize, usize), Option<Vec<Coefficients>>>,
    diagnostics: bool,
    failures: Vec<serde_json::Value>,
}
fn diagnostic_vector(vector: &Vector) -> serde_json::Value {
    serde_json::json!({"terms":vector.iter().take(64).map(|(&p,w)|(p,w.to_string())).collect::<Vec<_>>(),
        "truncated":vector.len()>64})
}
impl Maps {
    fn transfer(
        &mut self,
        source: usize,
        effect: &Vector,
        budget: &mut Budget,
    ) -> Result<Option<Transfer>> {
        budget.tick()?;
        let key = (source, effect.clone());
        if let Some(found) = self.transfers.get(&key) {
            self.failures.clear();
            return Ok(found.clone());
        }
        self.failures.clear();
        let mut shifted = self.components[source].base.clone();
        for (&p, w) in effect {
            add(&mut shifted, p, w.clone());
        }
        let mut found = None;
        for destination in
            std::iter::once(source).chain((0..self.components.len()).filter(|&i| i != source))
        {
            budget.tick()?;
            let mut residual = shifted.clone();
            for (&p, w) in &self.components[destination].base {
                add(&mut residual, p, -w);
            }
            let Some(base) = coefficients(&residual, &self.components[destination], budget)? else {
                if self.diagnostics && self.failures.len() < 16 {
                    self.failures.push(serde_json::json!({
                        "destination":destination,"reason":"shifted base is outside destination monoid",
                        "residual":diagnostic_vector(&residual),
                        "destination_base":diagnostic_vector(&self.components[destination].base),
                        "destination_periods":self.components[destination].periods.iter().take(16).map(diagnostic_vector).collect::<Vec<_>>(),
                        "periods_truncated":self.components[destination].periods.len()>16}));
                }
                continue;
            };
            let pair = (source, destination);
            if !self.periods.contains_key(&pair) {
                let mut columns = Some(vec![]);
                for (index, period) in self.components[source].periods.iter().enumerate() {
                    if let Some(column) =
                        coefficients(period, &self.components[destination], budget)?
                    {
                        columns.as_mut().unwrap().push(column);
                    } else {
                        if self.diagnostics && self.failures.len() < 16 {
                            self.failures.push(serde_json::json!({
                                "destination":destination,"reason":"source period is outside destination monoid",
                                "source_period":index,"period":diagnostic_vector(period),
                                "destination_periods":self.components[destination].periods.iter().take(16).map(diagnostic_vector).collect::<Vec<_>>(),
                                "periods_truncated":self.components[destination].periods.len()>16}));
                        }
                        columns = None;
                        break;
                    }
                }
                self.periods.insert(pair, columns);
            }
            if let Some(periods) = &self.periods[&pair] {
                found = Some(Transfer {
                    component: destination,
                    base,
                    periods: periods.clone(),
                });
                break;
            }
        }
        self.transfers.insert(key, found.clone());
        Ok(found)
    }
}

struct Projected {
    pre: Vec<(usize, u64)>,
    post: Vec<(usize, u64)>,
    effect: Vector,
    stutter: bool,
}

/// Incomplete proof search. Every returned certificate has passed the exact
/// original-query checker; resource exhaustion and failed discovery are errors.
pub fn discover(q: &RawQuery, deadline: Instant, max_work: usize) -> Result<Certificate> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    budget.tick()?;
    q.validate()?;
    ensure!(
        q.target.excluded_automaton.is_none(),
        "component invariants require a semilinear target"
    );
    let credits = credits(q, &mut budget)?;
    let credit_places: HashSet<_> = credits.iter().map(|c| c.place).collect();
    let source_places: HashSet<_> = q
        .transitions
        .iter()
        .filter(|tr| tr.pre.is_empty())
        .flat_map(|tr| tr.post.iter().map(|&(p, _)| p))
        .collect();
    let response_places: HashSet<_> = q.target.response_places.iter().copied().collect();
    // Finite closure is checked directly; no conservation claim is needed for
    // this projection. Unbounded selected counters exhaust the search budget.
    let mut control_places = vec![];
    for p in 0..q.places.len() {
        budget.tick()?;
        if !response_places.contains(&p)
            && !credit_places.contains(&p)
            && !source_places.contains(&p)
        {
            control_places.push(p);
        }
    }
    let positions: HashMap<_, _> = control_places
        .iter()
        .enumerate()
        .map(|(i, &p)| (p, i))
        .collect();
    let mut credit_columns: HashMap<_, _> =
        credits.iter().map(|c| (c.place, c.terms.clone())).collect();
    for &p in &q.target.response_places {
        credit_columns.insert(p, vec![(p, 1)]);
    }
    let mut initial_credit = Vector::new();
    for (&p, terms) in &credit_columns {
        budget.tick()?;
        for &(r, w) in terms {
            add(&mut initial_credit, r, BigInt::from(q.initial[p]) * w);
        }
    }
    let mut projected = vec![];
    for tr in &q.transitions {
        budget.tick()?;
        let mut effect = Vector::new();
        let mut delta = Vector::new();
        for (sign, arcs) in [(-1i32, &tr.pre), (1i32, &tr.post)] {
            for &(p, w) in arcs {
                budget.tick()?;
                if let Some(&i) = positions.get(&p) {
                    add(&mut delta, i, BigInt::from(w) * sign);
                }
                if let Some(terms) = credit_columns.get(&p) {
                    for &(r, a) in terms {
                        add(&mut effect, r, BigInt::from(w) * a * sign);
                    }
                }
            }
        }
        let selected = |arcs: &[(usize, u64)]| {
            arcs.iter()
                .filter_map(|&(p, w)| positions.get(&p).map(|&i| (i, w)))
                .collect()
        };
        projected.push(Projected {
            pre: selected(&tr.pre),
            post: selected(&tr.post),
            stutter: delta.is_empty() && effect.is_empty(),
            effect,
        });
    }
    let presets: Vec<_> = projected.iter().map(|t| t.pre.as_slice()).collect();
    let transition_index =
        crate::successors::TransitionIndex::from_presets(control_places.len(), &presets);
    let mut candidates = vec![];
    let mut maps = Maps {
        components: vec![],
        transfers: HashMap::new(),
        periods: HashMap::new(),
        diagnostics: std::env::var_os("VASS_RAW_NEGATIVE_DIAGNOSTICS").is_some(),
        failures: vec![],
    };
    for c in &q.target.excluded_semilinear {
        budget.tick()?;
        let periods: Vec<_> = c.periods.iter().map(|p| vector(p)).collect();
        let exact = periods
            .iter()
            .enumerate()
            .map(|(i, p)| (p.clone(), i))
            .collect();
        maps.components.push(Component {
            base: vector(&c.base),
            periods,
            exact,
        });
    }
    let initial_control: Vec<_> = control_places.iter().map(|&p| q.initial[p]).collect();
    let mut diagnostics_remaining = if maps.diagnostics { 4usize } else { 0 };
    if maps.diagnostics {
        eprintln!(
            "{}",
            serde_json::json!({"raw_negative_diagnostic":"setup",
            "components":maps.components.len(),"control_places":control_places.len(),
            "credits":credits.len(),"responses":q.target.response_places.iter().take(64).map(|&p|(p,&q.places[p])).collect::<Vec<_>>()})
        );
    }
    for initial_component in 0..maps.components.len() {
        budget.tick()?;
        let mut residual = initial_credit.clone();
        for (&p, w) in &maps.components[initial_component].base {
            add(&mut residual, p, -w);
        }
        let Some(initial_coefficients) =
            coefficients(&residual, &maps.components[initial_component], &mut budget)?
        else {
            continue;
        };
        let mut certificate = Certificate {
            format: "raw-component-invariant-v1".into(),
            control_places: control_places.clone(),
            credits: credits.clone(),
            initial_node: 0,
            initial_coefficients,
            nodes: vec![Node {
                control: initial_control.clone(),
                component: initial_component,
                edges: vec![],
            }],
        };
        budget.spend(control_places.len().max(1))?;
        let mut nodes = HashMap::from([((initial_control.clone(), initial_component), 0)]);
        let mut cursor = 0;
        let mut closed = true;
        while cursor < certificate.nodes.len() && closed {
            budget.tick()?;
            let control = certificate.nodes[cursor].control.clone();
            let component = certificate.nodes[cursor].component;
            budget.spend(control.len().max(1))?;
            transition_index.candidates(&control, &mut candidates);
            for &transition in &candidates {
                budget.tick()?;
                let tr = &projected[transition];
                if tr.stutter || tr.pre.iter().any(|&(i, w)| control[i] < w) {
                    continue;
                }
                let Some(transfer) = maps.transfer(component, &tr.effect, &mut budget)? else {
                    if diagnostics_remaining > 0 {
                        diagnostics_remaining -= 1;
                        let named_arcs = |arcs: &[(usize, u64)]| {
                            arcs.iter()
                                .take(64)
                                .map(|&(p, w)| (p, &q.places[p], w))
                                .collect::<Vec<_>>()
                        };
                        let mut trail = vec![];
                        let mut current = cursor;
                        while current != 0 && trail.len() < 64 {
                            let parent =
                                certificate.nodes.iter().enumerate().take(current).find_map(
                                    |(i, n)| {
                                        n.edges
                                            .iter()
                                            .find(|e| e.target == current)
                                            .map(|e| (i, e.transition))
                                    },
                                );
                            let Some((parent, transition)) = parent else {
                                break;
                            };
                            trail.push(serde_json::json!({"transition":transition,"from_component":certificate.nodes[parent].component,
                                "to_component":certificate.nodes[current].component,"effect":diagnostic_vector(&projected[transition].effect)}));
                            current = parent;
                        }
                        trail.reverse();
                        eprintln!(
                            "{}",
                            serde_json::json!({"raw_negative_diagnostic":"failed_transfer",
                            "initial_component":initial_component,"component":component,
                            "node":cursor,"discovered_nodes":certificate.nodes.len(),
                            "transition":transition,"transition_name":q.transitions[transition].name,
                            "pre":named_arcs(&q.transitions[transition].pre),"post":named_arcs(&q.transitions[transition].post),
                            "control":control.iter().enumerate().filter(|(_,w)|**w!=0).take(64).map(|(i,&w)|(control_places[i],&q.places[control_places[i]],w)).collect::<Vec<_>>(),
                            "effect":diagnostic_vector(&tr.effect),
                            "source_base":diagnostic_vector(&maps.components[component].base),
                            "source_periods":maps.components[component].periods.iter().take(16).map(diagnostic_vector).collect::<Vec<_>>(),
                            "source_periods_truncated":maps.components[component].periods.len()>16,
                            "predecessor_transfers":trail,"rejections":maps.failures})
                        );
                    }
                    closed = false;
                    break;
                };
                let mut successor = control.clone();
                for &(i, w) in &tr.pre {
                    successor[i] -= w;
                }
                for &(i, w) in &tr.post {
                    successor[i] = successor[i]
                        .checked_add(w)
                        .ok_or_else(|| anyhow!("controller overflow"))?;
                }
                let key = (successor.clone(), transfer.component);
                if !nodes.contains_key(&key) {
                    budget.spend(control_places.len().max(1))?;
                }
                let next = certificate.nodes.len();
                let target = *nodes.entry(key).or_insert_with(|| {
                    certificate.nodes.push(Node {
                        control: successor,
                        component: transfer.component,
                        edges: vec![],
                    });
                    next
                });
                if maps.diagnostics && certificate.nodes.len().is_power_of_two() && target == next {
                    let control = &certificate.nodes[target].control;
                    eprintln!(
                        "{}",
                        serde_json::json!({"raw_negative_diagnostic":"control_growth",
                        "nodes":certificate.nodes.len(),"node":target,"component":transfer.component,
                        "control":control.iter().enumerate().filter(|(_,w)|**w!=0).take(16).map(|(i,&w)|(control_places[i],&q.places[control_places[i]],w)).collect::<Vec<_>>()})
                    );
                }
                budget.spend(1)?;
                budget.spend(transfer.base.len())?;
                budget.spend(transfer.periods.len())?;
                for column in &transfer.periods {
                    budget.spend(column.len())?;
                }
                certificate.nodes[cursor].edges.push(Edge {
                    transition,
                    target,
                    base_coefficients: transfer.base,
                    period_coefficients: transfer.periods,
                });
            }
            cursor += 1;
        }
        if closed {
            crate::raw_invariant::check(q, &certificate, deadline, budget.remaining)?;
            return Ok(certificate);
        }
    }
    Err(anyhow!("no closed original-component invariant found"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn automatically_proves_locked_counter() {
        let q: RawQuery = serde_json::from_str(include_str!(
            "../benchmarks/raw-harder/counter_d3_s1_locked/query.json"
        ))
        .unwrap();
        let c = discover(&q, Instant::now() + Duration::from_secs(10), 1_000_000).unwrap();
        assert!(c.control_places.len() > 3);
        assert_eq!(c.credits.len(), 3);
        assert!(c.nodes.len() >= 8);
    }

    #[test]
    fn discovery_respects_resource_limits() {
        let q: RawQuery = serde_json::from_str(include_str!(
            "../benchmarks/raw-harder/counter_d3_s1_locked/query.json"
        ))
        .unwrap();
        assert!(discover(&q, Instant::now(), usize::MAX).is_err());
        assert!(discover(&q, Instant::now() + Duration::from_secs(10), 0).is_err());
    }

    #[test]
    fn discovery_uses_arcs_instead_of_names() {
        let mut q: RawQuery = serde_json::from_str(include_str!(
            "../benchmarks/raw-harder/counter_d3_s1_locked/query.json"
        ))
        .unwrap();
        q.places.fill("anonymous".into());
        for tr in &mut q.transitions {
            tr.name = "anonymous".into();
        }
        discover(&q, Instant::now() + Duration::from_secs(10), 1_000_000).unwrap();
    }

    #[test]
    fn does_not_certify_racy_counter() {
        let q: RawQuery = serde_json::from_str(include_str!(
            "../benchmarks/raw-harder/counter_d3_s1_racy/query.json"
        ))
        .unwrap();
        assert!(discover(&q, Instant::now() + Duration::from_secs(10), 1_000_000).is_err());
    }

    #[test]
    fn automatically_proves_locked_replicas() {
        let q: RawQuery = serde_json::from_str(include_str!(
            "../benchmarks/raw-harder/replicas_n2_locked/query.json"
        ))
        .unwrap();
        discover(&q, Instant::now() + Duration::from_secs(10), 1_000_000).unwrap();
    }
}
