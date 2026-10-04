use crate::{model::Problem, search::Outcome};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{One, Signed, Zero};
use std::{
    collections::HashMap,
    time::{Duration, Instant},
};

#[derive(Clone)]
struct Row {
    a: Vec<Q>,
    b: Q,
    proof: Vec<Q>,
}
fn q(x: impl Into<BigInt>) -> Q {
    Q::from_integer(x.into())
}
pub(crate) fn original_row_count(p: &Problem) -> Option<usize> {
    p.target.iter().try_fold(
        p.transitions.len().checked_add(p.places.len())?,
        |count, target| count.checked_add(1 + usize::from(target.equality)),
    )
}
pub(crate) fn original_rows(p: &Problem) -> Vec<(Vec<Q>, Q)> {
    #[cfg(test)]
    tests::ORIGINAL_ROWS_CALLS.with(|calls| calls.set(calls.get() + 1));
    let n = p.transitions.len();
    let mut delta = vec![vec![BigInt::zero(); n]; p.places.len()];
    for (t, tr) in p.transitions.iter().enumerate() {
        for &(i, w) in &tr.pre {
            delta[i][t] -= BigInt::from(w);
        }
        for &(i, w) in &tr.post {
            delta[i][t] += BigInt::from(w);
        }
    }
    let mut rows = Vec::new();
    for t in 0..n {
        let mut a = vec![Q::zero(); n];
        a[t] = Q::one();
        rows.push((a, Q::zero()));
    }
    for (i, d) in delta.iter().enumerate() {
        rows.push((d.iter().cloned().map(q).collect(), -q(p.initial[i])));
    }
    for c in &p.target {
        let mut a = vec![Q::zero(); n];
        let mut b = BigInt::from(c.bound);
        for (i, &coeff) in c.coefficients.iter().enumerate() {
            b -= BigInt::from(coeff) * BigInt::from(p.initial[i]);
            for (x, d) in a.iter_mut().zip(&delta[i]) {
                *x += q(BigInt::from(coeff) * d);
            }
        }
        let b = q(b);
        rows.push((a.clone(), b.clone()));
        if c.equality {
            rows.push((a.into_iter().map(|x| -x).collect(), -b));
        }
    }
    rows
}
pub fn verify_certificate(p: &Problem, certificate: &[String]) -> Result<()> {
    let rows = original_rows(p);
    ensure!(
        rows.len() == certificate.len(),
        "certificate dimension mismatch"
    );
    let mut lhs = vec![Q::zero(); p.transitions.len()];
    let mut rhs = Q::zero();
    for ((a, b), weight) in rows.into_iter().zip(certificate) {
        let w: Q = weight.parse()?;
        ensure!(!w.is_negative(), "negative Farkas multiplier");
        for (x, y) in lhs.iter_mut().zip(a) {
            *x += &w * y;
        }
        rhs += w * b;
    }
    ensure!(
        lhs.iter().all(Zero::is_zero) && rhs.is_positive(),
        "invalid Farkas contradiction"
    );
    Ok(())
}
fn normalize(row: &mut Row) {
    if let Some(scale) = row
        .a
        .iter()
        .find(|x| !x.is_zero())
        .or_else(|| if row.b.is_zero() { None } else { Some(&row.b) })
        .map(Signed::abs)
    {
        for a in &mut row.a {
            *a /= &scale;
        }
        row.b /= &scale;
        for w in &mut row.proof {
            *w /= &scale;
        }
    }
}
fn contradiction(p: &Problem, rows: &[Row]) -> Option<Outcome> {
    for r in rows {
        if r.a.iter().all(Zero::is_zero) && r.b.is_positive() {
            let certificate: Vec<_> = r.proof.iter().map(ToString::to_string).collect();
            if verify_certificate(p, &certificate).is_err() {
                return Some(Outcome::unknown(
                    "state-equation",
                    "certificate verification failed",
                    0,
                ));
            }
            let mut out =
                Outcome::unknown("state-equation", "exact rational Farkas certificate", 0);
            out.verdict = "unreachable";
            out.certificate = Some(certificate);
            return Some(out);
        }
    }
    None
}
pub fn solve(p: &Problem, timeout: Duration, max_rows: usize) -> Outcome {
    let start = Instant::now();
    if timeout.is_zero() {
        return Outcome::unknown("state-equation", "time limit", 0);
    }
    let Some(count) = original_row_count(p).filter(|&count| count <= max_rows) else {
        return Outcome::unknown("state-equation", "row limit", 0);
    };
    let originals = original_rows(p);
    let mut rows: Vec<_> = originals
        .into_iter()
        .enumerate()
        .map(|(i, (a, b))| {
            let mut proof = vec![Q::zero(); count];
            proof[i] = Q::one();
            let mut row = Row { a, b, proof };
            normalize(&mut row);
            row
        })
        .collect();
    let mut remaining: Vec<_> = (0..p.transitions.len()).collect();
    loop {
        if let Some(result) = contradiction(p, &rows) {
            return result;
        }
        if start.elapsed() >= timeout {
            return Outcome::unknown("state-equation", "time limit", 0);
        }
        let by_lhs: HashMap<Vec<Q>, usize> = rows
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
            return Outcome::unknown("state-equation", "rational relaxation feasible", 0);
        };
        remaining.swap_remove(index);
        let pos: Vec<_> = rows.iter().filter(|r| r.a[var].is_positive()).collect();
        let neg: Vec<_> = rows.iter().filter(|r| r.a[var].is_negative()).collect();
        let mut next: Vec<_> = rows
            .iter()
            .filter(|r| r.a[var].is_zero())
            .cloned()
            .collect();
        let mut strongest: HashMap<Vec<Q>, usize> = HashMap::new();
        for (i, row) in next.iter_mut().enumerate() {
            normalize(row);
            strongest.insert(row.a.clone(), i);
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
                return Outcome::unknown("state-equation", "time limit", 0);
            }
            let u = -&b.a[var];
            let v = &a.a[var];
            let mut row = Row {
                a: a.a.iter().zip(&b.a).map(|(x, y)| &u * x + v * y).collect(),
                b: &u * &a.b + v * &b.b,
                proof: a
                    .proof
                    .iter()
                    .zip(&b.proof)
                    .map(|(x, y)| &u * x + v * y)
                    .collect(),
            };
            if row
                .a
                .iter()
                .chain(std::iter::once(&row.b))
                .any(|x| x.numer().bits() > 4096 || x.denom().bits() > 4096)
            {
                return Outcome::unknown("state-equation", "coefficient size limit", 0);
            }
            normalize(&mut row);
            if row.a.iter().all(Zero::is_zero) {
                if row.b.is_positive() {
                    return contradiction(p, &[row]).unwrap();
                }
                continue;
            }
            if let Some(&i) = strongest.get(&row.a) {
                if row.b > next[i].b {
                    next[i] = row;
                }
            } else {
                if next.len() >= max_rows {
                    return Outcome::unknown("state-equation", "elimination row limit", 0);
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
    use crate::{
        integer_equation,
        model::{Constraint, Transition},
    };
    use std::cell::Cell;

    thread_local! {
        pub(super) static ORIGINAL_ROWS_CALLS: Cell<usize> = const { Cell::new(0) };
    }

    fn sparse_problem(size: usize) -> Problem {
        Problem {
            places: (0..size).map(|i| format!("p{i}")).collect(),
            initial: vec![0; size],
            transitions: (0..size)
                .map(|i| Transition {
                    name: format!("t{i}"),
                    pre: vec![(i, 1)],
                    post: vec![(i, 1)],
                })
                .collect(),
            target: vec![Constraint {
                coefficients: vec![1; size],
                bound: 1,
                equality: true,
            }],
        }
    }

    #[test]
    fn row_limit_skips_dense_construction() {
        let p = sparse_problem(256);
        p.validate().unwrap();
        for integer in [false, true] {
            ORIGINAL_ROWS_CALLS.with(|calls| calls.set(0));
            let out = if integer {
                integer_equation::solve(&p, Duration::from_secs(1), 512)
            } else {
                solve(&p, Duration::from_secs(1), 512)
            };
            assert_eq!(out.verdict, "unknown");
            assert_eq!(out.reason, "row limit");
            ORIGINAL_ROWS_CALLS.with(|calls| assert_eq!(calls.get(), 0));
        }
    }

    #[test]
    fn exact_row_limit_preserves_checked_refutations() {
        let p = sparse_problem(1);
        assert_eq!(original_row_count(&p), Some(4));
        let rational = solve(&p, Duration::from_secs(1), 4);
        assert_eq!(rational.verdict, "unreachable");
        verify_certificate(&p, rational.certificate.as_ref().unwrap()).unwrap();
        let integer = integer_equation::solve(&p, Duration::from_secs(1), 4);
        assert_eq!(integer.verdict, "unreachable");
        integer_equation::verify_certificate(&p, integer.proof.as_ref().unwrap()).unwrap();
    }

    #[test]
    fn row_count_matches_mixed_targets_and_empty_problem() {
        for size in [0, 1, 3] {
            let mut p = sparse_problem(size);
            for targets in 0..4 {
                p.target = (0..targets)
                    .map(|i| Constraint {
                        coefficients: vec![1; size],
                        bound: 1,
                        equality: i % 2 == 0,
                    })
                    .collect();
                assert_eq!(original_row_count(&p), Some(original_rows(&p).len()));
            }
        }
    }
}
