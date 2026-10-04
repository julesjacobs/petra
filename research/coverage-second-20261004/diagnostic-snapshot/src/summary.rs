use crate::model::{Problem, Transition};
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_traits::Zero;
use std::collections::BTreeMap;

/// A word is enabled exactly above `hurdle` and adds `effect` when executed.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct WordSummary {
    pub hurdle: Vec<BigInt>,
    pub effect: Vec<BigInt>,
}
impl WordSummary {
    pub fn identity(places: usize) -> Self {
        Self {
            hurdle: vec![BigInt::zero(); places],
            effect: vec![BigInt::zero(); places],
        }
    }
    pub fn transition(places: usize, t: &Transition) -> Self {
        let mut s = Self::identity(places);
        for &(p, w) in &t.pre {
            s.hurdle[p] += w;
            s.effect[p] -= w;
        }
        for &(p, w) in &t.post {
            s.effect[p] += w;
        }
        s
    }
    /// Execute self, then next. Dimensions must agree.
    pub fn then(&self, next: &Self) -> Self {
        assert_eq!(self.hurdle.len(), next.hurdle.len());
        Self {
            hurdle: self
                .hurdle
                .iter()
                .zip(&self.effect)
                .zip(&next.hurdle)
                .map(|((h, e), k)| h.clone().max(k - e))
                .collect(),
            effect: self
                .effect
                .iter()
                .zip(&next.effect)
                .map(|(a, b)| a + b)
                .collect(),
        }
    }
    pub fn repeat(&self, count: &num_bigint::BigUint) -> Self {
        if count.is_zero() {
            return Self::identity(self.hurdle.len());
        }
        let n = BigInt::from(count.clone());
        Self {
            hurdle: self
                .hurdle
                .iter()
                .zip(&self.effect)
                .map(|(h, e)| h + (-(&n - 1u8) * e).max(BigInt::zero()))
                .collect(),
            effect: self.effect.iter().map(|e| e * &n).collect(),
        }
    }
    pub fn apply(&self, marking: &[BigInt]) -> Option<Vec<BigInt>> {
        if marking.len() != self.hurdle.len()
            || marking.iter().zip(&self.hurdle).any(|(m, h)| m < h)
        {
            return None;
        }
        Some(
            marking
                .iter()
                .zip(&self.effect)
                .map(|(m, e)| m + e)
                .collect(),
        )
    }
}

#[derive(Default)]
pub(crate) struct SparseWordSummary {
    // Each entry stores (hurdle, effect); absent places have both equal to zero.
    pub(crate) places: BTreeMap<usize, (BigInt, BigInt)>,
}

pub(crate) fn sparse_summary(problem: &Problem, word: &[usize]) -> Result<SparseWordSummary> {
    ensure!(!word.is_empty(), "empty transition word");
    let mut result = SparseWordSummary::default();
    for &index in word {
        let transition = problem
            .transitions
            .get(index)
            .context("invalid transition index")?;
        for &(place, weight) in &transition.pre {
            let (hurdle, effect) = result.places.entry(place).or_default();
            *hurdle = hurdle.clone().max(BigInt::from(weight) - &*effect);
            *effect -= weight;
        }
        for &(place, weight) in &transition.post {
            result.places.entry(place).or_default().1 += weight;
        }
    }
    result
        .places
        .retain(|_, (h, e)| !h.is_zero() || !e.is_zero());
    Ok(result)
}
