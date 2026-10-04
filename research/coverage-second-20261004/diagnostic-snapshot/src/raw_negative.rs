//! Discovery of checked component invariants for original raw queries.
use crate::marking::StoredMarking;
use crate::raw_diagnostics::Diagnostics;
use crate::raw_invariant::{Certificate, Credit, Edge, Node};
use crate::raw_target::RawQuery;
use anyhow::{Result, anyhow, ensure};
use num_bigint::BigInt;
use num_traits::{Signed, ToPrimitive, Zero};
use std::collections::{BTreeMap, HashMap, HashSet, VecDeque};
use std::rc::Rc;
use std::time::Instant;

#[path = "raw_negative_adaptive.rs"]
mod adaptive;
pub use adaptive::{discover_adaptive, discover_adaptive_groups};
#[path = "raw_negative_groups.rs"]
mod groups;

type Vector = BTreeMap<usize, BigInt>;
type Coefficients = Vec<(usize, u64)>;

struct Budget {
    deadline: Instant,
    remaining: usize,
    diagnostics: Diagnostics,
}
impl Budget {
    fn tick(&mut self) -> Result<()> {
        self.spend(1)
    }

    fn spend(&mut self, work: usize) -> Result<()> {
        if Instant::now() >= self.deadline {
            self.diagnostics.finish("deadline");
            return Err(anyhow!("raw invariant discovery deadline"));
        }
        let Some(remaining) = self.remaining.checked_sub(work) else {
            self.diagnostics.finish("work-limit");
            return Err(anyhow!("raw invariant discovery work limit"));
        };
        self.remaining = remaining;
        self.diagnostics.work(work);
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
    budget.diagnostics.add("coefficient_calls", 1);
    let previous = budget.diagnostics.activity("coefficient-search");
    let result = coefficients_inner(target, component, budget);
    if matches!(&result, Ok(None)) {
        budget.diagnostics.add("coefficient_completed_failures", 1);
    }
    if result.is_ok() {
        budget.diagnostics.restore_activity(previous);
    }
    result
}

fn coefficients_inner(
    target: &Vector,
    component: &Component,
    budget: &mut Budget,
) -> Result<Option<Coefficients>> {
    budget.tick()?;
    if target.values().any(Signed::is_negative) {
        budget.diagnostics.add("coefficient_negative_residuals", 1);
        return Ok(None);
    }
    if target.is_empty() {
        return Ok(Some(vec![]));
    }
    if let Some(&index) = component.exact.get(target) {
        budget.diagnostics.add("coefficient_exact_period_hits", 1);
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
    budget
        .diagnostics
        .maximum("coefficient_eligible_dimension", eligible.len());
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
        budget.diagnostics.add("coefficient_search_nodes", 1);
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
    transfers: HashMap<(usize, Vector), Rc<Vec<Transfer>>>,
    periods: HashMap<(usize, usize), Option<Vec<Coefficients>>>,
    diagnostics: bool,
    failures: Vec<serde_json::Value>,
}
fn diagnostic_vector(vector: &Vector) -> serde_json::Value {
    serde_json::json!({"terms":vector.iter().take(64).map(|(&p,w)|(p,w.to_string())).collect::<Vec<_>>(),
        "truncated":vector.len()>64})
}
impl Maps {
    fn transfers(
        &mut self,
        source: usize,
        effect: &Vector,
        budget: &mut Budget,
    ) -> Result<Rc<Vec<Transfer>>> {
        budget.diagnostics.add("transfer_calls", 1);
        let previous = budget.diagnostics.activity("transfer-search");
        let result = self.transfers_inner(source, effect, budget);
        if matches!(&result, Ok(transfers) if transfers.is_empty()) {
            budget.diagnostics.add("transfer_completed_empty", 1);
        }
        if result.is_ok() {
            budget.diagnostics.restore_activity(previous);
        }
        result
    }

    fn transfers_inner(
        &mut self,
        source: usize,
        effect: &Vector,
        budget: &mut Budget,
    ) -> Result<Rc<Vec<Transfer>>> {
        budget.tick()?;
        let key = (source, effect.clone());
        if let Some(found) = self.transfers.get(&key) {
            budget.diagnostics.add("transfer_cache_hits", 1);
            self.failures.clear();
            return Ok(found.clone());
        }
        self.failures.clear();
        let mut shifted = self.components[source].base.clone();
        for (&p, w) in effect {
            add(&mut shifted, p, w.clone());
        }
        let mut found = vec![];
        for destination in
            std::iter::once(source).chain((0..self.components.len()).filter(|&i| i != source))
        {
            budget.tick()?;
            budget.diagnostics.add("transfer_destination_trials", 1);
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
                found.push(Transfer {
                    component: destination,
                    base,
                    periods: periods.clone(),
                });
            }
        }
        let found = Rc::new(found);
        budget.diagnostics.add("transfer_cache_entries", 1);
        budget.diagnostics.add("transfer_options", found.len());
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

enum Projection<'a> {
    Legacy(bool),
    Selected(&'a [usize], usize),
}

enum Attempt {
    Checked(Certificate),
    InitialOutside,
    Losing(adaptive::Obligations),
}

impl Attempt {
    fn certificate(self) -> Result<Certificate> {
        match self {
            Self::Checked(certificate) => Ok(certificate),
            Self::InitialOutside => Err(anyhow!(
                "initial credited marking outside candidate components"
            )),
            Self::Losing(_) => Err(anyhow!("no closed original-component invariant found")),
        }
    }
}

fn discover_projection(
    q: &RawQuery,
    budget: &mut Budget,
    track_control: bool,
) -> Result<Certificate> {
    attempt_projection(q, budget, Projection::Legacy(track_control))?.certificate()
}

fn attempt_projection(
    q: &RawQuery,
    budget: &mut Budget,
    projection: Projection<'_>,
) -> Result<Attempt> {
    budget.tick()?;
    q.validate()?;
    ensure!(
        q.target.excluded_automaton.is_none(),
        "component invariants require a semilinear target"
    );
    budget.diagnostics.phase("credit-preparation");
    let credits = credits(q, budget)?;
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
        if matches!(projection, Projection::Legacy(true))
            && !response_places.contains(&p)
            && !credit_places.contains(&p)
            && !source_places.contains(&p)
        {
            control_places.push(p);
        }
    }
    if let Projection::Selected(selected, _) = projection {
        ensure!(
            selected.windows(2).all(|w| w[0] < w[1]),
            "projection must be sorted and unique"
        );
        ensure!(
            selected.iter().all(|&p| p < q.places.len()),
            "projection place out of range"
        );
        control_places = selected.to_vec();
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
    budget.diagnostics.phase("projection-preparation");
    budget
        .diagnostics
        .add("control_places", control_places.len());
    budget
        .diagnostics
        .add("original_transitions", q.transitions.len());
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
    budget.diagnostics.phase("component-preparation");
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
    budget.spend(control_places.len().max(1))?;
    let mut control_markings = ControlMarkings::new(control_places.len());
    let initial_values: Vec<_> = control_places.iter().map(|&p| q.initial[p]).collect();
    let initial_control = control_markings.intern(&initial_values, budget)?;
    if maps.diagnostics {
        eprintln!(
            "{}",
            serde_json::json!({"raw_negative_diagnostic":"setup",
            "components":maps.components.len(),"control_places":control_places.len(),
            "credits":credits.len(),"responses":q.target.response_places.iter().take(64).map(|&p|(p,&q.places[p])).collect::<Vec<_>>()})
        );
    }
    budget.diagnostics.add("components", maps.components.len());
    budget.diagnostics.add("credits", credits.len());
    budget.diagnostics.phase("initial-component-matching");
    let mut game = vec![];
    let mut identities = HashMap::new();
    let mut initial_nodes = vec![];
    for component in 0..maps.components.len() {
        budget.tick()?;
        let mut residual = initial_credit.clone();
        for (&p, w) in &maps.components[component].base {
            add(&mut residual, p, -w);
        }
        if let Some(coefficients) = coefficients(&residual, &maps.components[component], budget)? {
            budget.spend(control_places.len().max(1))?;
            let index = game.len();
            identities.insert((initial_control.clone(), component), index);
            game.push(GameNode {
                control: initial_control.clone(),
                component,
                edges: vec![],
            });
            initial_nodes.push((index, coefficients));
        }
    }
    if initial_nodes.is_empty() {
        return Ok(Attempt::InitialOutside);
    }
    budget.diagnostics.observe_control(&initial_values);
    budget.diagnostics.phase("game-expansion");
    budget.diagnostics.add("game_nodes", game.len());
    let mut cursor = 0;
    let mut diagnostics_remaining = if maps.diagnostics { 4usize } else { 0 };
    let mut control = vec![0; control_places.len()];
    while cursor < game.len() {
        budget.tick()?;
        budget.spend(control_places.len().max(1))?;
        game[cursor].control.write_to(&mut control);
        budget
            .diagnostics
            .maximum("game_queue_high_water", game.len() - cursor);
        budget.diagnostics.add("expanded_game_nodes", 1);
        let component = game[cursor].component;
        transition_index.candidates(&control, &mut candidates);
        budget
            .diagnostics
            .add("transition_candidates", candidates.len());
        for &transition in &candidates {
            budget.tick()?;
            let tr = &projected[transition];
            if tr.stutter || tr.pre.iter().any(|&(i, w)| control[i] < w) {
                continue;
            }
            budget
                .diagnostics
                .add("enabled_nonstuttering_transitions", 1);
            let transfers = maps.transfers(component, &tr.effect, budget)?;
            if transfers.is_empty() && diagnostics_remaining > 0 {
                diagnostics_remaining -= 1;
                eprintln!(
                    "{}",
                    serde_json::json!({"raw_negative_diagnostic":"failed_transfer",
                    "component":component,"node":cursor,"discovered_nodes":game.len(),
                    "transition":transition,"effect":diagnostic_vector(&tr.effect),
                    "control":control.iter().enumerate().filter(|(_,w)|**w!=0).take(64).map(|(i,&w)|(control_places[i],&q.places[control_places[i]],w)).collect::<Vec<_>>(),
                    "source_base":diagnostic_vector(&maps.components[component].base),
                    "rejections":maps.failures})
                );
            }
            budget.spend(control.len().max(1))?;
            let mut successor = control.to_vec();
            for &(i, w) in &tr.pre {
                successor[i] -= w;
            }
            for &(i, w) in &tr.post {
                successor[i] = successor[i]
                    .checked_add(w)
                    .ok_or_else(|| anyhow!("controller overflow"))?;
            }
            let mut targets = Vec::with_capacity(transfers.len());
            budget.spend(transfers.len())?;
            let stored_successor = control_markings.intern(&successor, budget)?;
            for transfer in transfers.iter() {
                budget.spend(successor.len().max(1))?;
                let key = (stored_successor.clone(), transfer.component);
                let target = if let Some(&target) = identities.get(&key) {
                    target
                } else {
                    budget.spend(successor.len().max(1))?;
                    let target = game.len();
                    identities.insert(key, target);
                    budget.diagnostics.add("game_nodes", 1);
                    budget.diagnostics.observe_control(&successor);
                    game.push(GameNode {
                        control: stored_successor.clone(),
                        component: transfer.component,
                        edges: vec![],
                    });
                    target
                };
                targets.push(target);
            }
            budget.diagnostics.add("game_edges", 1);
            budget.diagnostics.add("game_or_targets", targets.len());
            let failed = targets.is_empty();
            game[cursor].edges.push(GameEdge {
                transition,
                transfers,
                targets,
            });
            if failed {
                break;
            }
        }
        cursor += 1;
    }
    budget.diagnostics.phase("greatest-fixed-point");
    let mut losses = vec![];
    let live = if matches!(projection, Projection::Selected(_, _)) {
        greatest_fixed_point_with_causes(&game, budget, Some(&mut losses))?
    } else {
        greatest_fixed_point(&game, budget)?
    };
    if budget.diagnostics.enabled() {
        budget
            .diagnostics
            .add("winning_nodes", live.iter().filter(|&&x| x).count());
    }
    if maps.diagnostics {
        eprintln!(
            "{}",
            serde_json::json!({"raw_negative_diagnostic":"component_game",
            "nodes":game.len(),"winning_nodes":live.iter().filter(|&&x|x).count(),
            "control_places":control_places.len(),"remaining_work":budget.remaining})
        );
    }
    let Some(winning_initial) = initial_nodes.iter().position(|(index, _)| live[*index]) else {
        let obligations = if matches!(projection, Projection::Selected(_, _)) {
            adaptive::obligations(&game, &losses, &initial_nodes, budget)?
        } else {
            adaptive::Obligations::default()
        };
        return Ok(Attempt::Losing(obligations));
    };
    let (initial, initial_coefficients) = initial_nodes.swap_remove(winning_initial);
    budget.diagnostics.phase("certificate-extraction");
    let certificate = extract_certificate(
        &game,
        &live,
        initial,
        initial_coefficients,
        control_places,
        credits,
        budget,
    )?;
    budget
        .diagnostics
        .add("certificate_nodes", certificate.nodes.len());
    budget.diagnostics.phase("component-checking");
    let check_work = match projection {
        Projection::Legacy(_) => budget.remaining,
        Projection::Selected(_, reserved) => budget.remaining.saturating_add(reserved),
    };
    crate::raw_invariant::check(q, &certificate, budget.deadline, check_work)?;
    Ok(Attempt::Checked(certificate))
}

struct ControlMarkings {
    dimension: usize,
    values: HashSet<Rc<StoredMarking>>,
}

impl ControlMarkings {
    fn new(dimension: usize) -> Self {
        Self {
            dimension,
            values: HashSet::new(),
        }
    }

    fn intern(&mut self, marking: &[u64], budget: &mut Budget) -> Result<Rc<StoredMarking>> {
        ensure!(
            marking.len() == self.dimension,
            "control dimension mismatch"
        );
        // Logical word allowances; hash-table collisions and growth are not
        // instruction-counted. The deadline independently bounds elapsed time.
        let conversion = marking.len().max(1).saturating_mul(2);
        budget.spend(conversion)?;
        budget
            .diagnostics
            .add("control_conversion_work", conversion);
        let value = StoredMarking::new(marking);
        let words = match &value {
            StoredMarking::Dense(values) => values.len(),
            StoredMarking::Sparse(values) => values.len().saturating_mul(2),
        }
        .saturating_add(2);
        let lookup = words.saturating_mul(2);
        budget.spend(lookup)?;
        budget.diagnostics.add("control_lookup_work", lookup);
        if let Some(stored) = self.values.get(&value) {
            budget.diagnostics.add("control_marking_intern_hits", 1);
            return Ok(Rc::clone(stored));
        }
        budget.spend(lookup)?;
        budget.diagnostics.add("control_insertion_work", lookup);
        let stored = Rc::new(value);
        self.values.insert(Rc::clone(&stored));
        budget.diagnostics.add("interned_control_markings", 1);
        Ok(stored)
    }
}

struct GameNode {
    control: Rc<StoredMarking>,
    component: usize,
    edges: Vec<GameEdge>,
}
struct GameEdge {
    transition: usize,
    transfers: Rc<Vec<Transfer>>,
    targets: Vec<usize>,
}

/// A node wins when every enabled transition has at least one winning target.
/// Removing losing nodes to a fixed point retains cycles that close jointly.
fn greatest_fixed_point(game: &[GameNode], budget: &mut Budget) -> Result<Vec<bool>> {
    greatest_fixed_point_with_causes(game, budget, None)
}

#[derive(Clone, Copy)]
struct Loss {
    edge: usize,
    rank: usize,
}

fn greatest_fixed_point_with_causes(
    game: &[GameNode],
    budget: &mut Budget,
    mut losses: Option<&mut Vec<Option<Loss>>>,
) -> Result<Vec<bool>> {
    budget.spend(game.len())?;
    if let Some(losses) = losses.as_deref_mut() {
        budget.spend(game.len())?;
        losses.resize(game.len(), None);
    }
    let mut next_rank = 0;
    let mut live = vec![true; game.len()];
    let mut predecessors = vec![vec![]; game.len()];
    let mut remaining = vec![];
    let mut removed = VecDeque::new();
    for (source, node) in game.iter().enumerate() {
        let mut counts = vec![];
        for (edge, choices) in node.edges.iter().enumerate() {
            budget.spend(choices.targets.len().saturating_add(1))?;
            counts.push(choices.targets.len());
            if choices.targets.is_empty() && live[source] {
                live[source] = false;
                if let Some(losses) = losses.as_deref_mut() {
                    losses[source] = Some(Loss {
                        edge,
                        rank: next_rank,
                    });
                    next_rank += 1;
                }
                removed.push_back(source);
            }
            for &target in &choices.targets {
                predecessors[target].push((source, edge));
            }
        }
        remaining.push(counts);
    }
    while let Some(target) = removed.pop_front() {
        for &(source, edge) in &predecessors[target] {
            budget.tick()?;
            if !live[source] {
                continue;
            }
            remaining[source][edge] -= 1;
            if remaining[source][edge] == 0 {
                live[source] = false;
                if let Some(losses) = losses.as_deref_mut() {
                    losses[source] = Some(Loss {
                        edge,
                        rank: next_rank,
                    });
                    next_rank += 1;
                }
                removed.push_back(source);
            }
        }
    }
    Ok(live)
}

fn extract_certificate(
    game: &[GameNode],
    live: &[bool],
    initial: usize,
    initial_coefficients: Coefficients,
    control_places: Vec<usize>,
    credits: Vec<Credit>,
    budget: &mut Budget,
) -> Result<Certificate> {
    let control_dimension = control_places.len();
    let dense_control = |control: &StoredMarking| {
        let mut values = vec![0; control_dimension];
        control.write_to(&mut values);
        values
    };
    budget.spend(control_places.len().max(1))?;
    let initial_node = Node {
        control: dense_control(&game[initial].control),
        component: game[initial].component,
        edges: vec![],
    };
    let mut result = Certificate {
        format: "raw-component-invariant-v1".into(),
        control_places,
        credits,
        initial_node: 0,
        initial_coefficients,
        nodes: vec![initial_node],
    };
    let mut indices = HashMap::from([(initial, 0)]);
    let mut todo = vec![initial];
    let mut cursor = 0;
    while cursor < todo.len() {
        let node = &game[todo[cursor]];
        for edge in &node.edges {
            budget.spend(edge.targets.len().saturating_add(1))?;
            let option = edge
                .targets
                .iter()
                .position(|&target| live[target])
                .ok_or_else(|| anyhow!("losing choice in extracted invariant"))?;
            let target = edge.targets[option];
            let transfer = &edge.transfers[option];
            let target = if let Some(&index) = indices.get(&target) {
                index
            } else {
                budget.spend(control_dimension.max(1))?;
                let index = result.nodes.len();
                result.nodes.push(Node {
                    control: dense_control(&game[target].control),
                    component: game[target].component,
                    edges: vec![],
                });
                indices.insert(target, index);
                todo.push(target);
                index
            };
            budget.spend(transfer.base.len().saturating_add(transfer.periods.len()))?;
            for column in &transfer.periods {
                budget.spend(column.len())?;
            }
            result.nodes[cursor].edges.push(Edge {
                transition: edge.transition,
                target,
                base_coefficients: transfer.base.clone(),
                period_coefficients: transfer.periods.clone(),
            });
        }
        cursor += 1;
    }
    Ok(result)
}

/// Starts with the coarsest control projection, then retains the structural
/// control places if the first abstraction does not yield a checked invariant.
pub fn discover(q: &RawQuery, deadline: Instant, max_work: usize) -> Result<Certificate> {
    let allowance = max_work / 8;
    let mut coarse = Budget {
        deadline,
        remaining: allowance,
        diagnostics: Diagnostics::new("raw-negative-empty"),
    };
    let result = discover_projection(q, &mut coarse, false);
    coarse.diagnostics.finish_result(&result);
    if let Ok(proof) = result {
        return Ok(proof);
    }
    let mut budget = Budget {
        deadline,
        remaining: max_work - allowance,
        diagnostics: Diagnostics::new("raw-negative-structural"),
    };
    let result = discover_projection(q, &mut budget, true);
    budget.diagnostics.finish_result(&result);
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn reset_query() -> RawQuery {
        serde_json::from_value(serde_json::json!({
            "format":"ser-raw-v1","places":["ready","used","a","r"],"initial":[1,0,0,0],
            "transitions":[
                {"name":"use","pre":[[0,1]],"post":[[1,1],[2,1]]},
                {"name":"reset","pre":[[1,1]],"post":[[0,1],[3,1]]},
                {"name":"idle-reset","pre":[[0,1]],"post":[[0,1],[3,1]]}],
            "target":{"kind":"completed-outside-semilinear","zero_places":[],"response_places":[2,3],
                "excluded_semilinear":[
                    {"base":[],"periods":[[[2,1],[3,1]],[[3,1]]]},
                    {"base":[[2,1]],"periods":[[[2,1],[3,1]],[[3,1]]]}]}
        })).unwrap()
    }

    #[test]
    fn control_markings_share_storage_without_merging_distinct_markings() {
        let mut budget = Budget {
            deadline: Instant::now() + Duration::from_secs(5),
            remaining: 1000,
            diagnostics: Diagnostics::disabled(),
        };
        let mut controls = ControlMarkings::new(3);
        let a = controls.intern(&[0, u64::MAX, 3], &mut budget).unwrap();
        let b = controls.intern(&[0, u64::MAX, 3], &mut budget).unwrap();
        let c = controls.intern(&[1, u64::MAX, 3], &mut budget).unwrap();
        assert!(Rc::ptr_eq(&a, &b));
        assert!(!Rc::ptr_eq(&a, &c));
        let mut successor = vec![0; 3];
        a.write_to(&mut successor);
        successor[0] = 1;
        assert!(Rc::ptr_eq(
            &controls.intern(&successor, &mut budget).unwrap(),
            &c
        ));
        a.write_to(&mut successor);
        assert_eq!(successor, [0, u64::MAX, 3]);
        budget.remaining = 0;
        assert!(controls.intern(&[2, 0, 3], &mut budget).is_err());
        assert_eq!(controls.values.len(), 2);
    }

    #[test]
    fn sparse_control_interning_preserves_positions_values_and_dimension() {
        let mut budget = Budget {
            deadline: Instant::now() + Duration::from_secs(5),
            remaining: 10_000,
            diagnostics: Diagnostics::disabled(),
        };
        let mut controls = ControlMarkings::new(64);
        let mut values = vec![0; 64];
        values[17] = u64::MAX;
        let first = controls.intern(&values, &mut budget).unwrap();
        assert!(matches!(&*first, StoredMarking::Sparse(_)));
        assert!(Rc::ptr_eq(
            &first,
            &controls.intern(&values, &mut budget).unwrap()
        ));
        values.swap(17, 18);
        let second = controls.intern(&values, &mut budget).unwrap();
        assert!(!Rc::ptr_eq(&first, &second));
        let mut restored = vec![42; 64];
        first.write_to(&mut restored);
        assert_eq!(restored[17], u64::MAX);
        assert_eq!(restored.iter().filter(|&&value| value != 0).count(), 1);
        second.write_to(&mut restored);
        assert_eq!(restored, values);
        assert!(controls.intern(&values[..63], &mut budget).is_err());
        assert_eq!(controls.values.len(), 2);
    }

    #[test]
    fn control_work_charges_conversion_and_encoded_keys_without_partial_insertion() {
        let deadline = Instant::now() + Duration::from_secs(5);
        for values in [vec![0; 64], vec![1; 64]] {
            let words = if values[0] == 0 { 2 } else { 66 };
            let conversion = 128;
            let lookup = words * 2;
            let mut controls = ControlMarkings::new(64);
            let mut budget = Budget {
                deadline,
                remaining: conversion + 2 * lookup - 1,
                diagnostics: Diagnostics::disabled(),
            };
            assert!(controls.intern(&values, &mut budget).is_err());
            assert!(controls.values.is_empty());
            budget.remaining = conversion + 2 * lookup;
            let first = controls.intern(&values, &mut budget).unwrap();
            assert_eq!(budget.remaining, 0);
            budget.remaining = conversion + lookup;
            let second = controls.intern(&values, &mut budget).unwrap();
            assert_eq!(budget.remaining, 0);
            assert!(Rc::ptr_eq(&first, &second));
        }
    }

    #[test]
    fn sparse_controls_extract_an_unchanged_dense_checked_certificate() {
        let mut q = reset_query();
        q.places.extend((0..64).map(|i| format!("unused{i}")));
        q.initial.extend([0; 64]);
        let deadline = Instant::now() + Duration::from_secs(5);
        let certificate = discover(&q, deadline, 1_000_000).unwrap();
        assert!(certificate.control_places.len() >= 64);
        assert!(
            certificate
                .nodes
                .iter()
                .all(|node| node.control.len() == certificate.control_places.len())
        );
        crate::raw_invariant::check(&q, &certificate, deadline, 1_000_000).unwrap();
    }

    #[test]
    fn chooses_a_closed_reset_transfer_instead_of_the_first_valid_transfer() {
        let q = reset_query();
        let deadline = Instant::now() + Duration::from_secs(5);
        let certificate = discover(&q, deadline, 100_000).unwrap();
        crate::raw_invariant::check(&q, &certificate, deadline, 100_000).unwrap();
        let used = certificate
            .nodes
            .iter()
            .find(|n| n.control == [0, 1])
            .unwrap();
        let reset = used.edges.iter().find(|e| e.transition == 1).unwrap();
        assert_eq!(certificate.nodes[reset.target].component, 0);
    }

    #[test]
    fn extra_uses_do_not_gain_a_false_invariant_from_component_choices() {
        let mut q = reset_query();
        q.transitions.push(crate::model::Transition {
            name: "repeat-use".into(),
            pre: vec![(1, 1)],
            post: vec![(1, 1), (2, 1)],
        });
        assert!(discover(&q, Instant::now() + Duration::from_secs(5), 100_000).is_err());
    }

    #[test]
    fn unbounded_pending_requests_need_no_control_for_an_unrestricted_response_language() {
        let q: RawQuery = serde_json::from_value(serde_json::json!({
            "format":"ser-raw-v1","places":["entry","pending","response"],"initial":[0,0,0],
            "transitions":[
                {"name":"request","pre":[],"post":[[0,1]]},
                {"name":"snapshot","pre":[[0,1]],"post":[[1,1]]},
                {"name":"return","pre":[[1,1]],"post":[[2,1]]}],
            "target":{"kind":"completed-outside-semilinear","zero_places":[0,1],"response_places":[2],
                "excluded_semilinear":[{"base":[],"periods":[[[2,1]]]}]}
        })).unwrap();
        let certificate = discover(&q, Instant::now() + Duration::from_secs(5), 10_000).unwrap();
        assert!(certificate.control_places.is_empty());
        assert_eq!(certificate.nodes.len(), 1);
    }

    #[test]
    fn greatest_fixed_point_preserves_supported_cycles_and_requires_every_transition() {
        let edge = |targets| GameEdge {
            transition: 0,
            transfers: Rc::new(vec![]),
            targets,
        };
        let node = |edges| GameNode {
            control: Rc::new(StoredMarking::new(&[])),
            component: 0,
            edges,
        };
        let game = vec![
            node(vec![edge(vec![1, 2])]),
            node(vec![edge(vec![1])]),
            node(vec![edge(vec![])]),
            node(vec![edge(vec![0]), edge(vec![2])]),
        ];
        let mut budget = Budget {
            deadline: Instant::now() + Duration::from_secs(5),
            remaining: 1000,
            diagnostics: Diagnostics::disabled(),
        };
        assert_eq!(
            greatest_fixed_point(&game, &mut budget).unwrap(),
            [true, true, false, false]
        );
    }

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
