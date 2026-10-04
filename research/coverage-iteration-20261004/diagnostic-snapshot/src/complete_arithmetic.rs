//! Exact arithmetic used by the complete decomposition procedure.
//!
//! Integer feasibility uses a finite small-solution bound. A componentwise
//! minimal solution of A x = b gives an indecomposable zero-sum multiset of
//! columns of [A|-b], with the last column used once. The Steinitz rearrangement
//! lemma puts its partial sums in [-m M,m M]^m. Distinct partial sums therefore
//! give sum(x)+1 <= (2 m M+1)^m. Repeated partial sums would remove a nonempty
//! zero-sum submultiset and contradict minimality. Bounding each x by this
//! number is consequently sufficient for feasibility, even when the solution
//! set itself is unbounded. Exact rational elimination and finite integer
//! branching then decide feasibility when no resource budget is imposed.
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Signed, Zero};
use std::{collections::HashMap, time::Instant};

type Q = BigRational;

#[derive(Clone, Debug)]
pub struct System {
    pub variables: usize,
    pub a: Vec<Vec<BigInt>>,
    pub b: Vec<BigInt>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Answer<T> {
    Feasible(T),
    Infeasible,
    Unknown(&'static str),
}

#[derive(Clone, Debug, Default)]
pub struct Limits {
    pub deadline: Option<Instant>,
    pub max_rows: Option<usize>,
    pub max_nodes: Option<usize>,
}
impl Limits {
    fn check(&self) -> Result<(), &'static str> {
        if self.deadline.is_some_and(|t| Instant::now() >= t) {
            Err("arithmetic deadline")
        } else {
            Ok(())
        }
    }
}
impl System {
    fn valid(&self) -> bool {
        self.a.len() == self.b.len() && self.a.iter().all(|a| a.len() == self.variables)
    }
}
#[derive(Clone)]
struct Row {
    a: Vec<Q>,
    b: Q,
}
fn integer(x: BigInt) -> Q {
    Q::from_integer(x)
}

/// A sufficient bound for a smallest nonnegative integer solution.
/// Also bounds every bounded coordinate of the rational polyhedron: a finite
/// maximum occurs at a basic feasible solution; Cramer's rule bounds its
/// numerator by m! M^m <= (2mM+1)^m and its nonzero integer denominator by >=1.
pub fn small_solution_bound(system: &System) -> BigInt {
    let m = system.a.len();
    let largest = system
        .a
        .iter()
        .flatten()
        .chain(&system.b)
        .map(Signed::abs)
        .max()
        .unwrap_or_else(BigInt::zero);
    let base = BigInt::from(2usize) * BigInt::from(m) * largest + BigInt::one();
    // Repeated squaring avoids narrowing the equation count to u32.
    let (mut exponent, mut power, mut result) = (m, base, BigInt::one());
    while exponent != 0 {
        if exponent % 2 == 1 {
            result *= &power;
        }
        exponent /= 2;
        if exponent != 0 {
            power = &power * &power;
        }
    }
    result
}

fn simplify(rows: Vec<Row>, limits: &Limits) -> Result<Option<Vec<Row>>, &'static str> {
    let mut unique: HashMap<Vec<Q>, Q> = HashMap::new();
    for mut row in rows {
        limits.check()?;
        let Some(scale) = row.a.iter().find(|v| !v.is_zero()).map(Signed::abs) else {
            if row.b.is_negative() {
                return Ok(None);
            }
            continue;
        };
        for v in &mut row.a {
            *v /= &scale;
        }
        row.b /= scale;
        unique
            .entry(row.a)
            .and_modify(|b| {
                if row.b < *b {
                    *b = row.b.clone();
                }
            })
            .or_insert(row.b);
        if limits.max_rows.is_some_and(|n| unique.len() > n) {
            return Err("arithmetic row limit");
        }
    }
    Ok(Some(
        unique.into_iter().map(|(a, b)| Row { a, b }).collect(),
    ))
}

/// Rational feasibility with explicit nonnegative lower and optional upper
/// bounds. All rows use a*x=b; inequalities are internal to elimination.
pub fn solve_rational(
    system: &System,
    lower: &[BigInt],
    upper: &[Option<BigInt>],
    limits: &Limits,
) -> Answer<Vec<Q>> {
    match rational(system, lower, upper, limits) {
        Ok(Some(x)) => Answer::Feasible(x),
        Ok(None) => Answer::Infeasible,
        Err(reason) => Answer::Unknown(reason),
    }
}
fn rational(
    system: &System,
    lower: &[BigInt],
    upper: &[Option<BigInt>],
    limits: &Limits,
) -> Result<Option<Vec<Q>>, &'static str> {
    limits.check()?;
    let n = system.variables;
    if !system.valid()
        || lower.len() != n
        || upper.len() != n
        || lower.iter().any(Signed::is_negative)
    {
        return Err("invalid arithmetic system");
    }
    let mut rows = Vec::new();
    for (a, b) in system.a.iter().zip(&system.b) {
        rows.push(Row {
            a: a.iter().cloned().map(integer).collect(),
            b: integer(b.clone()),
        });
        rows.push(Row {
            a: a.iter().cloned().map(|x| integer(-x)).collect(),
            b: integer(-b),
        });
    }
    for j in 0..n {
        if upper[j].as_ref().is_some_and(|u| u < &lower[j]) {
            return Ok(None);
        }
        let mut a = vec![Q::zero(); n];
        a[j] = -Q::one();
        rows.push(Row {
            a: a.clone(),
            b: integer(-&lower[j]),
        });
        if let Some(u) = &upper[j] {
            a[j] = Q::one();
            rows.push(Row {
                a,
                b: integer(u.clone()),
            });
        }
    }
    let Some(mut rows) = simplify(rows, limits)? else {
        return Ok(None);
    };
    let mut active = vec![true; n];
    let mut history = Vec::new();
    for _ in 0..n {
        limits.check()?;
        let positions: HashMap<_, _> = rows
            .iter()
            .enumerate()
            .map(|(i, r)| ((r.a.clone(), r.b.clone()), i))
            .collect();
        let equality = rows
            .iter()
            .enumerate()
            .filter_map(|(i, r)| {
                let opposite = (r.a.iter().map(|x| -x).collect::<Vec<_>>(), -&r.b);
                positions
                    .get(&opposite)
                    .copied()
                    .filter(|&k| i < k)
                    .map(|k| (i, k))
            })
            .min_by_key(|&(i, _)| rows[i].a.iter().filter(|x| !x.is_zero()).count());
        let j = (0..n)
            .filter(|&j| active[j] && equality.is_none_or(|(i, _)| !rows[i].a[j].is_zero()))
            .min_by_key(|&j| {
                let p = rows.iter().filter(|r| r.a[j].is_positive()).count();
                let q = rows.iter().filter(|r| r.a[j].is_negative()).count();
                p.saturating_mul(q)
            })
            .unwrap();
        let pos: Vec<_> = rows.iter().filter(|r| r.a[j].is_positive()).collect();
        let neg: Vec<_> = rows.iter().filter(|r| r.a[j].is_negative()).collect();
        let mut next: Vec<_> = rows.iter().filter(|r| r.a[j].is_zero()).cloned().collect();
        let pairs: Box<dyn Iterator<Item = (&Row, &Row)>> = if let Some((a, b)) = equality {
            let (p, q) = if rows[a].a[j].is_positive() {
                (&rows[a], &rows[b])
            } else {
                (&rows[b], &rows[a])
            };
            Box::new(
                pos.iter()
                    .map(move |&row| (row, q))
                    .chain(neg.iter().map(move |&row| (p, row))),
            )
        } else {
            Box::new(pos.iter().flat_map(|&p| neg.iter().map(move |&q| (p, q))))
        };
        for (p, q) in pairs {
            limits.check()?;
            let ps = -&q.a[j];
            let qs = &p.a[j];
            next.push(Row {
                a: p.a
                    .iter()
                    .zip(&q.a)
                    .map(|(x, y)| x * &ps + y * qs)
                    .collect(),
                b: &p.b * &ps + &q.b * qs,
            });
            if limits
                .max_rows
                .is_some_and(|cap| next.len() > cap.saturating_mul(2).max(1))
            {
                let Some(compacted) = simplify(next, limits)? else {
                    return Ok(None);
                };
                next = compacted;
            }
        }
        history.push((j, rows));
        active[j] = false;
        let Some(compacted) = simplify(next, limits)? else {
            return Ok(None);
        };
        rows = compacted;
    }
    let mut model = vec![Q::zero(); n];
    for (j, rows) in history.into_iter().rev() {
        limits.check()?;
        let (mut lo, mut hi): (Option<Q>, Option<Q>) = (None, None);
        for row in rows {
            if row.a[j].is_zero() {
                continue;
            }
            let remainder: Q = row.a.iter().zip(&model).map(|(a, x)| a * x).sum();
            let bound = (row.b - remainder) / &row.a[j];
            if row.a[j].is_positive() {
                if hi.as_ref().is_none_or(|h| bound < *h) {
                    hi = Some(bound);
                }
            } else if lo.as_ref().is_none_or(|l| bound > *l) {
                lo = Some(bound);
            }
        }
        if let Some(l) = lo {
            model[j] = model[j].clone().max(l);
        }
        if let Some(h) = hi {
            model[j] = model[j].clone().min(h);
        }
    }
    debug_assert!(system.a.iter().zip(&system.b).all(|(a, b)| {
        a.iter()
            .zip(&model)
            .map(|(a, x)| integer(a.clone()) * x)
            .sum::<Q>()
            == integer(b.clone())
    }));
    Ok(Some(model))
}

fn gcd(mut a: BigInt, mut b: BigInt) -> BigInt {
    a = a.abs();
    b = b.abs();
    while !b.is_zero() {
        let remainder = &a % &b;
        a = b;
        b = remainder;
    }
    a
}
fn integer_equalities(system: &System, limits: &Limits) -> Result<Option<System>, &'static str> {
    let mut rows: Vec<_> = system
        .a
        .iter()
        .cloned()
        .zip(system.b.iter().cloned())
        .collect();
    fn primitive(a: &mut [BigInt], b: &mut BigInt) -> bool {
        let g = a.iter().fold(BigInt::zero(), |g, x| gcd(g, x.clone()));
        if g.is_zero() {
            return b.is_zero();
        }
        if !(&*b % &g).is_zero() {
            return false;
        }
        for x in a {
            *x /= &g;
        }
        *b /= g;
        true
    }
    for (a, b) in &mut rows {
        if !primitive(a, b) {
            return Ok(None);
        }
    }
    let mut pivot = 0;
    for j in 0..system.variables {
        limits.check()?;
        let Some(k) = (pivot..rows.len())
            .filter(|&i| !rows[i].0[j].is_zero())
            .min_by_key(|&i| rows[i].0[j].abs())
        else {
            continue;
        };
        rows.swap(pivot, k);
        let (a, b) = rows[pivot].clone();
        for (i, (other, rhs)) in rows.iter_mut().enumerate() {
            if i == pivot || other[j].is_zero() {
                continue;
            }
            let u = a[j].clone();
            let v = other[j].clone();
            for (x, y) in other.iter_mut().zip(&a) {
                *x = &u * &*x - &v * y;
            }
            *rhs = &u * &*rhs - &v * &b;
            if !primitive(other, rhs) {
                return Ok(None);
            }
        }
        pivot += 1;
    }
    rows.retain(|(a, _)| a.iter().any(|x| !x.is_zero()));
    let (a, b) = rows.into_iter().unzip();
    Ok(Some(System {
        variables: system.variables,
        a,
        b,
    }))
}

pub fn solve_integer(system: &System, limits: &Limits) -> Answer<Vec<BigInt>> {
    if limits.max_nodes == Some(0) || limits.max_rows == Some(0) {
        return Answer::Unknown("arithmetic zero resource budget");
    }
    if !system.valid() {
        return Answer::Unknown("invalid arithmetic system");
    }
    if let Err(reason) = limits.check() {
        return Answer::Unknown(reason);
    }
    let reduced = match integer_equalities(system, limits) {
        Ok(Some(s)) => s,
        Ok(None) => return Answer::Infeasible,
        Err(s) => return Answer::Unknown(s),
    };
    let system = &reduced;
    let n = system.variables;
    let bound = small_solution_bound(system);
    let mut stack = vec![(vec![BigInt::zero(); n], vec![Some(bound); n])];
    let mut nodes = 0usize;
    while let Some((lo, hi)) = stack.pop() {
        if let Err(reason) = limits.check() {
            return Answer::Unknown(reason);
        }
        if limits.max_nodes.is_some_and(|max| nodes >= max) {
            return Answer::Unknown("arithmetic node limit");
        }
        nodes = nodes.saturating_add(1);
        let model = match solve_rational(system, &lo, &hi, limits) {
            Answer::Feasible(x) => x,
            Answer::Infeasible => continue,
            Answer::Unknown(reason) => return Answer::Unknown(reason),
        };
        let Some(j) = model.iter().position(|x| !x.is_integer()) else {
            return Answer::Feasible(model.into_iter().map(|x| x.to_integer()).collect());
        };
        // Models are nonnegative, so truncation is floor.
        let floor = model[j].to_integer();
        let mut high_lo = lo.clone();
        high_lo[j] = &floor + BigInt::one();
        let mut low_hi = hi.clone();
        low_hi[j] = Some(floor);
        stack.push((high_lo, hi));
        stack.push((lo, low_hi));
    }
    Answer::Infeasible
}

/// Nonnegative integer kernel vector positive in every requested coordinate.
/// Rational and integer existence coincide by clearing denominators. An empty
/// requested set returns zero. With a feasible base solution, positivity in a
/// coordinate is equivalent to that coordinate being unbounded above.
pub fn homogeneous_direction(
    system: &System,
    positive: &[usize],
    limits: &Limits,
) -> Answer<Vec<BigInt>> {
    if positive.iter().any(|&j| j >= system.variables) || !system.valid() {
        return Answer::Unknown("invalid arithmetic system");
    }
    let homogeneous = System {
        variables: system.variables,
        a: system.a.clone(),
        b: vec![BigInt::zero(); system.b.len()],
    };
    let mut lo = vec![BigInt::zero(); system.variables];
    for &j in positive {
        lo[j] = BigInt::one();
    }
    match solve_rational(&homogeneous, &lo, &vec![None; system.variables], limits) {
        Answer::Feasible(x) => {
            // Product suffices; no integer-gcd dependency needed.
            let scale: BigInt = x.iter().map(|x| x.denom()).product();
            Answer::Feasible(
                x.into_iter()
                    .map(|x| x.numer() * (&scale / x.denom()))
                    .collect(),
            )
        }
        Answer::Infeasible => Answer::Infeasible,
        Answer::Unknown(reason) => Answer::Unknown(reason),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn system(a: &[&[i64]], b: &[i64], n: usize) -> System {
        System {
            variables: n,
            a: a.iter()
                .map(|r| r.iter().copied().map(BigInt::from).collect())
                .collect(),
            b: b.iter().copied().map(BigInt::from).collect(),
        }
    }
    fn verifies(s: &System, x: &[BigInt]) -> bool {
        x.iter().all(|v| !v.is_negative())
            && s.a
                .iter()
                .zip(&s.b)
                .all(|(a, b)| a.iter().zip(x).map(|(a, x)| a * x).sum::<BigInt>() == *b)
    }
    #[test]
    fn distinguishes_integer_and_rational_feasibility() {
        let s = system(&[&[2]], &[1], 1);
        assert_eq!(
            solve_rational(&s, &[0.into()], &[None], &Limits::default()),
            Answer::Feasible(vec![Q::new(1.into(), 2.into())])
        );
        assert_eq!(solve_integer(&s, &Limits::default()), Answer::Infeasible);
        let s = system(&[&[2, -3]], &[1], 2);
        let Answer::Feasible(x) = solve_integer(&s, &Limits::default()) else {
            panic!("missed integer solution")
        };
        assert!(verifies(&s, &x));
    }
    #[test]
    fn homogeneous_directions_classify_unbounded_coordinates() {
        let s = system(&[&[1, -1, 0], &[0, 0, 1]], &[3, 7], 3);
        let Answer::Feasible(x) = homogeneous_direction(&s, &[0, 1], &Limits::default()) else {
            panic!("missed ray")
        };
        assert!(x[0].is_positive() && x[1].is_positive() && x[2].is_zero());
        assert_eq!(
            homogeneous_direction(&s, &[2], &Limits::default()),
            Answer::Infeasible
        );
        let s = system(&[], &[], 2);
        assert_eq!(
            solve_integer(&s, &Limits::default()),
            Answer::Feasible(vec![0.into(), 0.into()])
        );
        assert_eq!(
            homogeneous_direction(&s, &[1], &Limits::default()),
            Answer::Feasible(vec![0.into(), 1.into()])
        );
    }
    #[test]
    fn empty_and_inconsistent_systems() {
        assert_eq!(
            solve_integer(&system(&[&[]], &[1], 0), &Limits::default()),
            Answer::Infeasible
        );
        assert_eq!(
            solve_integer(&system(&[], &[], 0), &Limits::default()),
            Answer::Feasible(vec![])
        );
        assert_eq!(
            solve_integer(&system(&[&[1], &[1]], &[0, 1], 1), &Limits::default()),
            Answer::Infeasible
        );
        assert_eq!(
            solve_integer(&system(&[&[1]], &[-1], 1), &Limits::default()),
            Answer::Infeasible
        );
    }
    #[test]
    fn resources_never_prove_infeasibility() {
        let s = system(&[&[2]], &[1], 1);
        assert!(matches!(
            solve_integer(
                &s,
                &Limits {
                    max_nodes: Some(0),
                    ..Limits::default()
                }
            ),
            Answer::Unknown(_)
        ));
        assert!(matches!(
            solve_integer(
                &s,
                &Limits {
                    max_rows: Some(0),
                    ..Limits::default()
                }
            ),
            Answer::Unknown(_)
        ));
        assert!(matches!(
            solve_integer(
                &s,
                &Limits {
                    deadline: Some(Instant::now()),
                    ..Limits::default()
                }
            ),
            Answer::Unknown(_)
        ));
    }
    #[test]
    fn exhaustive_bounded_two_variable_instances() {
        // x+y+slack=4 bounds x and y, allowing an independent finite oracle.
        for a in -3..=3 {
            for b in -3..=3 {
                for rhs in -5..=5 {
                    let s = system(&[&[a, b, 0], &[1, 1, 1]], &[rhs, 4], 3);
                    let expected = (0..=4).any(|x| (0..=4 - x).any(|y| a * x + b * y == rhs));
                    match solve_integer(&s, &Limits::default()) {
                        Answer::Feasible(x) => {
                            assert!(expected);
                            assert!(verifies(&s, &x));
                        }
                        Answer::Infeasible => assert!(!expected, "a={a} b={b} rhs={rhs}"),
                        Answer::Unknown(r) => panic!("unexpected {r}"),
                    }
                }
            }
        }
    }
}
