//! Exact reduction of Petri-net linear targets to pure-effect point VASS reachability.
use crate::{complete_cover::Arc, model::Problem};
use num_bigint::BigInt;
use num_traits::{One, Signed, Zero};
#[derive(Clone, Debug)]
pub struct PointVass {
    pub states: usize,
    pub arcs: Vec<Arc>,
    pub initial_state: usize,
    pub final_state: usize,
    pub initial: Vec<BigInt>,
    pub final_marking: Vec<BigInt>,
}
fn impossible() -> PointVass {
    PointVass {
        states: 2,
        arcs: vec![],
        initial_state: 0,
        final_state: 1,
        initial: vec![],
        final_marking: vec![],
    }
}
fn add(
    arcs: &mut Vec<Arc>,
    states: &mut usize,
    source: usize,
    target: usize,
    pre: Vec<BigInt>,
    post: Vec<BigInt>,
) {
    if pre
        .iter()
        .zip(&post)
        .all(|(a, b)| a.is_zero() || b.is_zero())
    {
        arcs.push(Arc {
            source,
            target,
            effect: post.into_iter().zip(pre).map(|(a, b)| a - b).collect(),
        });
        return;
    }
    let private = *states;
    *states += 1;
    arcs.push(Arc {
        source,
        target: private,
        effect: pre.into_iter().map(|x| -x).collect(),
    });
    arcs.push(Arc {
        source: private,
        target,
        effect: post,
    });
}
pub fn reduce(p: &Problem) -> PointVass {
    let n = p.places.len();
    let mut point = vec![None; n];
    for c in &p.target {
        let support: Vec<_> = c
            .coefficients
            .iter()
            .enumerate()
            .filter(|(_, a)| **a != 0)
            .collect();
        if support.is_empty()
            && (if c.equality {
                c.bound != 0
            } else {
                c.bound > 0
            })
        {
            return impossible();
        }
        if c.equality && support.len() == 1 {
            let (j, &a) = support[0];
            let a = BigInt::from(a);
            let b = BigInt::from(c.bound);
            if !(&b % &a).is_zero() {
                return impossible();
            }
            let value = b / a;
            if value.is_negative() {
                return impossible();
            }
            if point[j].as_ref().is_some_and(|v| v != &value) {
                return impossible();
            }
            point[j] = Some(value);
        }
    }
    let exact = point.iter().all(Option::is_some);
    let d = if exact { n } else { n + 2 * p.target.len() };
    let mut states = if exact { 1 } else { 2 };
    let mut arcs = vec![];
    for t in &p.transitions {
        let mut pre = vec![BigInt::zero(); d];
        let mut post = pre.clone();
        for &(j, w) in &t.pre {
            pre[j] = w.into();
        }
        for &(j, w) in &t.post {
            post[j] = w.into();
        }
        add(&mut arcs, &mut states, 0, 0, pre, post);
    }
    let mut initial: Vec<_> = p.initial.iter().copied().map(BigInt::from).collect();
    initial.resize(d, BigInt::zero());
    if exact {
        let target: Vec<BigInt> = point.into_iter().map(Option::unwrap).collect();
        for c in &p.target {
            let v: BigInt = c
                .coefficients
                .iter()
                .zip(&target)
                .map(|(&a, v)| BigInt::from(a) * v)
                .sum();
            let b = BigInt::from(c.bound);
            if if c.equality { v != b } else { v < b } {
                return impossible();
            }
        }
        return PointVass {
            states,
            arcs,
            initial_state: 0,
            final_state: 0,
            initial,
            final_marking: target,
        };
    }
    let mut constants = vec![BigInt::zero(); d];
    for (i, c) in p.target.iter().enumerate() {
        let b = BigInt::from(c.bound);
        if b.is_negative() {
            constants[n + 2 * i] = -b;
        } else {
            constants[n + 2 * i + 1] = b;
        }
    }
    add(
        &mut arcs,
        &mut states,
        0,
        1,
        vec![BigInt::zero(); d],
        constants,
    );
    for j in 0..n {
        let mut pre = vec![BigInt::zero(); d];
        let mut post = pre.clone();
        pre[j] = BigInt::one();
        for (i, c) in p.target.iter().enumerate() {
            let a = BigInt::from(c.coefficients[j]);
            post[n + 2 * i + usize::from(a.is_negative())] = a.abs();
        }
        add(&mut arcs, &mut states, 1, 1, pre, post);
    }
    for (i, c) in p.target.iter().enumerate() {
        let mut pre = vec![BigInt::zero(); d];
        pre[n + 2 * i] = BigInt::one();
        pre[n + 2 * i + 1] = BigInt::one();
        add(&mut arcs, &mut states, 1, 1, pre, vec![BigInt::zero(); d]);
        if !c.equality {
            let mut pre = vec![BigInt::zero(); d];
            pre[n + 2 * i] = BigInt::one();
            add(&mut arcs, &mut states, 1, 1, pre, vec![BigInt::zero(); d]);
        }
    }
    PointVass {
        states,
        arcs,
        initial_state: 0,
        final_state: 1,
        initial,
        final_marking: vec![BigInt::zero(); d],
    }
}
