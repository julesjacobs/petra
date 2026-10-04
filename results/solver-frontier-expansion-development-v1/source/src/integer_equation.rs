//! Integer Fourier–Motzkin relaxation with independently replayable rounding cuts.
use crate::{
    model::Problem,
    search::Outcome,
    state_equation::{original_row_count, original_rows},
};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use num_traits::{Signed, Zero};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::HashMap,
    time::{Duration, Instant},
};

#[derive(Clone)]
struct Row {
    a: Vec<BigInt>,
    b: BigInt,
    proof: usize,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(tag = "rule", rename_all = "kebab-case")]
enum Node {
    Original {
        index: usize,
    },
    Combine {
        left: usize,
        right: usize,
        left_weight: String,
        right_weight: String,
    },
}
#[derive(Serialize, Deserialize)]
struct Certificate {
    kind: String,
    nodes: Vec<Node>,
    contradiction: usize,
}
fn gcd(mut a: BigInt, mut b: BigInt) -> BigInt {
    a = a.abs();
    b = b.abs();
    while !b.is_zero() {
        let r = &a % &b;
        a = b;
        b = r;
    }
    a
}
fn normalize(row: &mut Row) {
    let divisor = row.a.iter().fold(BigInt::zero(), |g, x| gcd(g, x.clone()));
    if divisor.is_zero() {
        return;
    }
    for a in &mut row.a {
        *a /= &divisor;
    }
    let rem = &row.b % &divisor;
    row.b /= divisor;
    if rem.is_positive() {
        row.b += 1;
    }
}
fn originals(p: &Problem) -> Vec<Row> {
    original_rows(p)
        .into_iter()
        .map(|(a, b)| Row {
            a: a.into_iter().map(|q| q.to_integer()).collect(),
            b: b.to_integer(),
            proof: 0,
        })
        .collect()
}
fn combine(a: &Row, b: &Row, u: &BigInt, v: &BigInt, proof: usize) -> Row {
    let mut out = Row {
        a: a.a.iter().zip(&b.a).map(|(x, y)| u * x + v * y).collect(),
        b: u * &a.b + v * &b.b,
        proof,
    };
    normalize(&mut out);
    out
}
pub fn verify_certificate(p: &Problem, value: &Value) -> Result<()> {
    p.validate()?;
    let cert: Certificate = serde_json::from_value(value.clone())?;
    ensure!(
        cert.kind == "integer-cuts-v1",
        "unexpected certificate kind"
    );
    let originals = originals(p);
    let mut rows: Vec<Row> = Vec::new();
    for node in cert.nodes {
        let mut row = match node {
            Node::Original { index } => originals
                .get(index)
                .ok_or_else(|| anyhow::anyhow!("invalid original row"))?
                .clone(),
            Node::Combine {
                left,
                right,
                left_weight,
                right_weight,
            } => {
                ensure!(
                    left < rows.len() && right < rows.len(),
                    "invalid cut dependency"
                );
                let u: BigInt = left_weight.parse()?;
                let v: BigInt = right_weight.parse()?;
                ensure!(!u.is_negative() && !v.is_negative(), "negative cut weight");
                combine(&rows[left], &rows[right], &u, &v, 0)
            }
        };
        normalize(&mut row);
        rows.push(row);
    }
    let row = rows
        .get(cert.contradiction)
        .ok_or_else(|| anyhow::anyhow!("invalid contradiction index"))?;
    ensure!(
        row.a.iter().all(Zero::is_zero) && row.b.is_positive(),
        "invalid integer contradiction"
    );
    Ok(())
}
fn certificate(nodes: &[Node], last: usize) -> Value {
    fn visit(
        id: usize,
        nodes: &[Node],
        map: &mut HashMap<usize, usize>,
        out: &mut Vec<Node>,
    ) -> usize {
        if let Some(&i) = map.get(&id) {
            return i;
        }
        let node = match &nodes[id] {
            Node::Original { index } => Node::Original { index: *index },
            Node::Combine {
                left,
                right,
                left_weight,
                right_weight,
            } => Node::Combine {
                left: visit(*left, nodes, map, out),
                right: visit(*right, nodes, map, out),
                left_weight: left_weight.clone(),
                right_weight: right_weight.clone(),
            },
        };
        let i = out.len();
        out.push(node);
        map.insert(id, i);
        i
    }
    let mut out = Vec::new();
    let contradiction = visit(last, nodes, &mut HashMap::new(), &mut out);
    serde_json::to_value(Certificate {
        kind: "integer-cuts-v1".into(),
        nodes: out,
        contradiction,
    })
    .unwrap()
}
fn finish(p: &Problem, nodes: &[Node], row: &Row) -> Outcome {
    let proof = certificate(nodes, row.proof);
    if let Err(e) = verify_certificate(p, &proof) {
        return Outcome::unknown(
            "integer-state-equation",
            &format!("certificate check failed: {e}"),
            0,
        );
    }
    let mut out = Outcome::unknown(
        "integer-state-equation",
        "checked integer rounding-cut contradiction",
        0,
    );
    out.verdict = "unreachable";
    out.proof = Some(proof);
    out
}
pub fn solve(p: &Problem, timeout: Duration, max_rows: usize) -> Outcome {
    let start = Instant::now();
    let mut last = Outcome::unknown("integer-state-equation", "time limit", 0);
    for order in 0..4 {
        let left = timeout.saturating_sub(start.elapsed());
        if left.is_zero() {
            break;
        }
        last = solve_order(p, left / (4 - order) as u32, max_rows, order);
        if last.verdict != "unknown" {
            return last;
        }
    }
    last
}
fn solve_order(p: &Problem, timeout: Duration, max_rows: usize, order: usize) -> Outcome {
    let start = Instant::now();
    if timeout.is_zero() {
        return Outcome::unknown("integer-state-equation", "time limit", 0);
    }
    if original_row_count(p).is_none_or(|count| count > max_rows) {
        return Outcome::unknown("integer-state-equation", "row limit", 0);
    }
    let mut nodes = Vec::new();
    let mut rows = originals(p);
    for (i, row) in rows.iter_mut().enumerate() {
        row.proof = i;
        nodes.push(Node::Original { index: i });
        normalize(row);
    }
    let mut remaining: Vec<_> = (0..p.transitions.len()).collect();
    if order % 2 == 1 {
        remaining.reverse();
    }
    let n = remaining.len();
    if n > 0 {
        remaining.rotate_left((order / 2 * (n / 2)) % n);
    }
    loop {
        if let Some(row) = rows
            .iter()
            .find(|r| r.a.iter().all(Zero::is_zero) && r.b.is_positive())
        {
            return finish(p, &nodes, row);
        }
        if start.elapsed() >= timeout {
            return Outcome::unknown("integer-state-equation", "time limit", 0);
        }
        let by_lhs: HashMap<Vec<BigInt>, usize> = rows
            .iter()
            .enumerate()
            .map(|(i, r)| (r.a.clone(), i))
            .collect();
        let equality = rows.iter().enumerate().find_map(|(i, r)| {
            let opposite: Vec<_> = r.a.iter().map(|x| -x).collect();
            by_lhs
                .get(&opposite)
                .filter(|&&j| rows[j].b == -&r.b)
                .and_then(|&j| {
                    remaining
                        .iter()
                        .position(|&v| !r.a[v].is_zero())
                        .map(|index| (index, i, j))
                })
        });
        let choice = if let Some((index, _, _)) = equality {
            Some((index, &remaining[index]))
        } else {
            remaining.iter().enumerate().min_by_key(|(_, v)| {
                let pos = rows.iter().filter(|r| r.a[**v].is_positive()).count();
                let neg = rows.iter().filter(|r| r.a[**v].is_negative()).count();
                pos.saturating_mul(neg)
            })
        };
        let Some((index, &var)) = choice else {
            return Outcome::unknown(
                "integer-state-equation",
                "integer projection relaxation feasible",
                0,
            );
        };
        remaining.swap_remove(index);
        let pos: Vec<_> = rows.iter().filter(|r| r.a[var].is_positive()).collect();
        let neg: Vec<_> = rows.iter().filter(|r| r.a[var].is_negative()).collect();
        let mut next: Vec<Row> = Vec::new();
        let mut strongest: HashMap<Vec<BigInt>, usize> = HashMap::new();
        for row in rows.iter().filter(|r| r.a[var].is_zero()) {
            if let Some(&i) = strongest.get(&row.a) {
                if row.b > next[i].b {
                    next[i] = row.clone();
                }
            } else {
                strongest.insert(row.a.clone(), next.len());
                next.push(row.clone());
            }
        }
        let pairs: Box<dyn Iterator<Item = (&Row, &Row)>> = if let Some((_, i, j)) = equality {
            let (ep, en) = if rows[i].a[var].is_positive() {
                (&rows[i], &rows[j])
            } else {
                (&rows[j], &rows[i])
            };
            Box::new(
                pos.iter()
                    .map(move |&a| (a, en))
                    .chain(neg.iter().map(move |&b| (ep, b))),
            )
        } else {
            Box::new(pos.iter().flat_map(|&a| neg.iter().map(move |&b| (a, b))))
        };
        for (a, b) in pairs {
            if start.elapsed() >= timeout {
                return Outcome::unknown("integer-state-equation", "time limit", 0);
            }
            let divisor = gcd(a.a[var].clone(), b.a[var].clone());
            let u = -&b.a[var] / &divisor;
            let v = &a.a[var] / divisor;
            let row = combine(a, b, &u, &v, nodes.len());
            if row
                .a
                .iter()
                .chain(std::iter::once(&row.b))
                .any(|x| x.bits() > 4096)
            {
                return Outcome::unknown("integer-state-equation", "coefficient size limit", 0);
            }
            if row.a.iter().all(Zero::is_zero) && !row.b.is_positive() {
                continue;
            }
            if strongest.get(&row.a).is_some_and(|&i| next[i].b >= row.b) {
                continue;
            }
            if nodes.len() >= max_rows.saturating_mul(64) {
                return Outcome::unknown("integer-state-equation", "proof size limit", 0);
            }
            nodes.push(Node::Combine {
                left: a.proof,
                right: b.proof,
                left_weight: u.to_string(),
                right_weight: v.to_string(),
            });
            if row.a.iter().all(Zero::is_zero) {
                return finish(p, &nodes, &row);
            }
            if let Some(&i) = strongest.get(&row.a) {
                next[i] = row;
            } else {
                if next.len() >= max_rows {
                    return Outcome::unknown("integer-state-equation", "elimination row limit", 0);
                }
                strongest.insert(row.a.clone(), next.len());
                next.push(row);
            }
        }
        rows = next;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    fn instance(step: u64, target: i64) -> Problem {
        Problem {
            places: vec!["p".into()],
            initial: vec![0],
            transitions: vec![Transition {
                name: "grow".into(),
                pre: vec![],
                post: vec![(0, step)],
            }],
            target: vec![Constraint {
                coefficients: vec![1],
                bound: target,
                equality: true,
            }],
        }
    }
    #[test]
    fn exhausted_budget_is_unknown() {
        let p = instance(2, 1);
        assert_eq!(solve(&p, Duration::ZERO, 100).verdict, "unknown");
        assert_eq!(
            crate::state_equation::solve(&p, Duration::ZERO, 100).verdict,
            "unknown"
        );
    }
    #[test]
    fn parity_has_replayable_cut_certificate() {
        let p = instance(2, 1);
        let out = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(out.verdict, "unreachable");
        let proof = out.proof.unwrap();
        verify_certificate(&p, &proof).unwrap();
        assert!(verify_certificate(&instance(2, 2), &proof).is_err());
        let mut forged = proof;
        forged["nodes"][0]["index"] = serde_json::json!(10000);
        assert!(verify_certificate(&p, &forged).is_err());
    }
    #[test]
    fn integer_rounding_uses_ceiling_for_negative_bounds() {
        for b in -9..10 {
            let mut row = Row {
                a: vec![BigInt::from(-3)],
                b: BigInt::from(b),
                proof: 0,
            };
            normalize(&mut row);
            for x in -10..10 {
                assert_eq!(-3 * x >= b, &row.a[0] * BigInt::from(x) >= row.b);
            }
        }
    }
    #[test]
    fn one_dimensional_differential() {
        for step in 1..8 {
            for target in 0..20 {
                let p = instance(step, target);
                let out = solve(&p, Duration::from_secs(1), 100);
                if target % step as i64 == 0 {
                    assert_eq!(out.verdict, "unknown");
                } else {
                    assert_eq!(out.verdict, "unreachable");
                    verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
                }
            }
        }
    }
    #[test]
    fn bounded_two_place_differential() {
        for initial in 0..6 {
            for step in 1..4 {
                for target in 0..7 {
                    let p = Problem {
                        places: vec!["p".into(), "q".into()],
                        initial: vec![initial, 5 - initial],
                        transitions: vec![
                            Transition {
                                name: "forward".into(),
                                pre: vec![(0, step)],
                                post: vec![(1, step)],
                            },
                            Transition {
                                name: "backward".into(),
                                pre: vec![(1, 2)],
                                post: vec![(0, 2)],
                            },
                        ],
                        target: vec![Constraint {
                            coefficients: vec![1, 0],
                            bound: target,
                            equality: true,
                        }],
                    };
                    let bfs = crate::search::solve(&p, false, Duration::from_secs(1), 100);
                    assert_ne!(bfs.verdict, "unknown");
                    for out in [
                        solve(&p, Duration::from_secs(1), 100),
                        crate::state_equation::solve(&p, Duration::from_secs(1), 100),
                    ] {
                        if out.verdict == "unreachable" {
                            assert_eq!(bfs.verdict, "unreachable");
                        }
                        if let Some(proof) = out.proof {
                            verify_certificate(&p, &proof).unwrap();
                        }
                        if let Some(proof) = out.certificate {
                            crate::state_equation::verify_certificate(&p, &proof).unwrap();
                        }
                    }
                }
            }
        }
    }
    #[test]
    fn negative_weights_and_forward_references_are_rejected() {
        let p = instance(2, 1);
        let proof = serde_json::json!({"kind":"integer-cuts-v1","nodes":[{"rule":"original","index":0},{"rule":"combine","left":0,"right":0,"left_weight":"-1","right_weight":"0"}],"contradiction":1});
        assert!(verify_certificate(&p, &proof).is_err());
        let mut proof = proof;
        proof["nodes"][1]["left_weight"] = serde_json::json!("1");
        proof["nodes"][1]["right"] = serde_json::json!(1);
        assert!(verify_certificate(&p, &proof).is_err());
    }
}
