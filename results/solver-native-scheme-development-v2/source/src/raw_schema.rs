//! Checked serial sublanguages for automaton targets.
use crate::raw_diagnostics::Diagnostics;
use crate::raw_target::{LinearSet, RawQuery, SerialAutomaton};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, time::Instant};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Segment {
    pub path: Vec<usize>,
    pub cycles: Vec<Vec<usize>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Schema {
    pub segments: Vec<Segment>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub format: String,
    pub schemas: Vec<Schema>,
    pub invariant: crate::raw_invariant::Certificate,
}

struct Budget {
    deadline: Instant,
    remaining: usize,
    diagnostics: Diagnostics,
}
impl Budget {
    fn spend(&mut self, work: usize) -> Result<()> {
        if Instant::now() >= self.deadline {
            self.diagnostics.finish("deadline");
            anyhow::bail!("serial schema deadline");
        }
        let Some(remaining) = self.remaining.checked_sub(work) else {
            self.diagnostics.finish("work-limit");
            anyhow::bail!("serial schema work limit");
        };
        self.remaining = remaining;
        self.diagnostics.work(work);
        Ok(())
    }
}

fn walk(
    automaton: &SerialAutomaton,
    mut state: usize,
    path: &[usize],
    vector: &mut BTreeMap<usize, u64>,
    budget: &mut Budget,
) -> Result<usize> {
    for &index in path {
        budget.spend(1)?;
        let edge = automaton
            .edges
            .get(index)
            .ok_or_else(|| anyhow::anyhow!("invalid serial edge index"))?;
        ensure!(edge.source == state, "disconnected serial path");
        let count = vector.entry(edge.response).or_default();
        *count = count
            .checked_add(1)
            .ok_or_else(|| anyhow::anyhow!("serial vector overflow"))?;
        state = edge.target;
    }
    Ok(state)
}

/// Replace the serial language by a certified subset, returning the remaining
/// work allowance. Proving inclusion in this subset proves the original query.
pub fn semilinear_query(
    q: &RawQuery,
    schemas: &[Schema],
    deadline: Instant,
    max_work: usize,
) -> Result<(RawQuery, usize)> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
        diagnostics: Diagnostics::new("schema-materialization"),
    };
    budget.diagnostics.phase("schema-validation");
    budget.diagnostics.add("schemas", schemas.len());
    budget.spend(1)?;
    budget.spend(
        q.places
            .len()
            .saturating_add(q.initial.len())
            .saturating_add(q.target.zero_places.len())
            .saturating_add(q.target.response_places.len()),
    )?;
    for transition in &q.transitions {
        budget.spend(
            transition
                .pre
                .len()
                .saturating_add(transition.post.len())
                .saturating_add(1),
        )?;
    }
    if let Some(automaton) = &q.target.excluded_automaton {
        budget.spend(
            automaton
                .edges
                .len()
                .saturating_add(automaton.accepting.len()),
        )?;
    }
    for component in &q.target.excluded_semilinear {
        budget.spend(component.base.len().saturating_add(1))?;
        for period in &component.periods {
            budget.spend(period.len().saturating_add(1))?;
        }
    }
    q.validate()?;
    let a = q
        .target
        .excluded_automaton
        .as_ref()
        .ok_or_else(|| anyhow::anyhow!("serial schemas require an automaton target"))?;
    let mut components = vec![];
    for schema in schemas {
        budget.spend(1)?;
        let mut state = a.initial;
        let mut base = BTreeMap::new();
        let mut periods = vec![];
        for segment in &schema.segments {
            budget
                .diagnostics
                .add("schema_path_edges", segment.path.len());
            budget
                .diagnostics
                .add("schema_cycles", segment.cycles.len());
            budget.spend(1)?;
            state = walk(a, state, &segment.path, &mut base, &mut budget)?;
            for cycle in &segment.cycles {
                budget.diagnostics.add("schema_cycle_edges", cycle.len());
                budget.spend(1)?;
                ensure!(!cycle.is_empty(), "empty serial cycle");
                let mut period = BTreeMap::new();
                ensure!(
                    walk(a, state, cycle, &mut period, &mut budget)? == state,
                    "serial cycle does not return to its anchor"
                );
                periods.push(period.into_iter().collect());
            }
        }
        budget.spend(a.accepting.len())?;
        ensure!(
            a.accepting.contains(&state),
            "serial schema ends outside accepting states"
        );
        components.push(LinearSet {
            base: base.into_iter().collect(),
            periods,
        });
    }
    budget.diagnostics.phase("semilinear-materialization");
    budget.diagnostics.add("components", components.len());
    budget.spend(q.places.len().saturating_add(q.transitions.len()))?;
    for tr in &q.transitions {
        budget.spend(tr.pre.len().saturating_add(tr.post.len()))?;
    }
    let subset = RawQuery {
        format: "ser-raw-v1".into(),
        places: q.places.clone(),
        initial: q.initial.clone(),
        transitions: q.transitions.clone(),
        target: crate::raw_target::RawTarget {
            kind: "completed-outside-semilinear".into(),
            zero_places: q.target.zero_places.clone(),
            response_places: q.target.response_places.clone(),
            excluded_automaton: None,
            excluded_semilinear: components,
        },
    };
    budget.spend(1)?;
    budget.diagnostics.finish("complete");
    Ok((subset, budget.remaining))
}

pub fn check(q: &RawQuery, proof: &Certificate, deadline: Instant, max_work: usize) -> Result<()> {
    let mut diagnostics = Diagnostics::new("schema-checking");
    diagnostics.phase("schema-wrapper-checking");
    let result = check_inner(q, proof, deadline, max_work, &mut diagnostics);
    diagnostics.finish_result(&result);
    result
}

fn check_inner(
    q: &RawQuery,
    proof: &Certificate,
    deadline: Instant,
    max_work: usize,
    diagnostics: &mut Diagnostics,
) -> Result<()> {
    ensure!(
        proof.format == "raw-automaton-invariant-v1",
        "wrong serial schema certificate format"
    );
    let (subset, remaining) = semilinear_query(q, &proof.schemas, deadline, max_work)?;
    diagnostics.phase("component-checking");
    crate::raw_invariant::check(&subset, &proof.invariant, deadline, remaining)
}

pub fn discover(q: &RawQuery, deadline: Instant, max_work: usize) -> Result<Certificate> {
    let mut diagnostics = Diagnostics::new("raw-schema-discovery");
    let result = discover_inner(
        q,
        deadline,
        max_work,
        &mut diagnostics,
        crate::raw_negative::discover,
    );
    diagnostics.finish_result(&result);
    result
}

pub fn discover_adaptive(q: &RawQuery, deadline: Instant, max_work: usize) -> Result<Certificate> {
    let mut diagnostics = Diagnostics::new("raw-adaptive-schema-discovery");
    let result = discover_inner(
        q,
        deadline,
        max_work,
        &mut diagnostics,
        crate::raw_negative::discover_adaptive,
    );
    diagnostics.finish_result(&result);
    result
}

pub fn discover_adaptive_groups(
    q: &RawQuery,
    deadline: Instant,
    max_work: usize,
) -> Result<Certificate> {
    let mut diagnostics = Diagnostics::new("raw-adaptive-groups-schema-discovery");
    let result = discover_inner(
        q,
        deadline,
        max_work,
        &mut diagnostics,
        crate::raw_negative::discover_adaptive_groups,
    );
    diagnostics.finish_result(&result);
    result
}

fn discover_inner(
    q: &RawQuery,
    deadline: Instant,
    max_work: usize,
    diagnostics: &mut Diagnostics,
    discover_components: fn(&RawQuery, Instant, usize) -> Result<crate::raw_invariant::Certificate>,
) -> Result<Certificate> {
    q.validate()?;
    let automaton = q
        .target
        .excluded_automaton
        .as_ref()
        .ok_or_else(|| anyhow::anyhow!("serial schemas require an automaton target"))?;
    diagnostics.phase("serial-schema-discovery");
    let schemas = crate::raw_schemas::discover(automaton, deadline, max_work / 8, 256)?;
    diagnostics.phase("schema-materialization");
    let (subset, remaining) = semilinear_query(q, &schemas, deadline, max_work / 8)?;
    diagnostics.phase("component-invariant-discovery");
    let invariant = discover_components(&subset, deadline, remaining.saturating_add(max_work / 2))?;
    let proof = Certificate {
        format: "raw-automaton-invariant-v1".into(),
        schemas,
        invariant,
    };
    diagnostics.phase("outer-schema-checking");
    check(q, &proof, deadline, max_work / 4)?;
    Ok(proof)
}
