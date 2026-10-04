use num_bigint::{BigInt, BigUint};
use num_traits::Zero;
use std::{
    collections::{HashSet, VecDeque},
    time::{Duration, Instant},
};
use vass_reach::{
    dag::{self, Encoding},
    model::{Constraint, Problem, Transition},
};

fn satisfies(p: &Problem, m: &[BigUint]) -> bool {
    p.target.iter().all(|c| {
        let value = c
            .coefficients
            .iter()
            .zip(m)
            .fold(BigInt::zero(), |sum, (&a, x)| {
                sum + BigInt::from(a) * BigInt::from(x.clone())
            });
        if c.equality {
            value == BigInt::from(c.bound)
        } else {
            value >= BigInt::from(c.bound)
        }
    })
}
fn fire(p: &Problem, m: &[BigUint], t: usize) -> Option<Vec<BigUint>> {
    let tr = &p.transitions[t];
    if tr.pre.iter().any(|&(i, w)| m[i] < BigUint::from(w)) {
        return None;
    }
    let mut result = m.to_vec();
    for &(i, w) in &tr.pre {
        result[i] -= BigUint::from(w);
    }
    for &(i, w) in &tr.post {
        result[i] += BigUint::from(w);
    }
    Some(result)
}
fn reachable(p: &Problem) -> bool {
    let initial: Vec<_> = p.initial.iter().copied().map(BigUint::from).collect();
    let mut seen = HashSet::from([initial.clone()]);
    let mut queue = VecDeque::from([initial]);
    while let Some(m) = queue.pop_front() {
        if satisfies(p, &m) {
            return true;
        }
        for t in 0..p.transitions.len() {
            if let Some(next) = fire(p, &m, t)
                && seen.insert(next.clone())
            {
                queue.push_back(next);
            }
        }
    }
    false
}
fn propagate(encoding: &Encoding, choices: usize) -> bool {
    let mut values = vec![None; encoding.variables + 1];
    for (i, &(_, literal)) in encoding.choices.iter().enumerate() {
        values[literal as usize] = Some((choices >> i) & 1 == 1);
    }
    loop {
        let mut changed = false;
        for clause in &encoding.clauses {
            let mut unassigned = vec![];
            let mut satisfied = false;
            for &literal in clause {
                match values[literal.unsigned_abs() as usize] {
                    Some(value) if value == (literal > 0) => {
                        satisfied = true;
                        break;
                    }
                    Some(_) => {}
                    None => {
                        if !unassigned.contains(&literal) {
                            unassigned.push(literal);
                        }
                    }
                }
            }
            if satisfied {
                continue;
            }
            if unassigned.is_empty() {
                return false;
            }
            if unassigned.len() == 1 {
                let literal = unassigned[0];
                values[literal.unsigned_abs() as usize] = Some(literal > 0);
                changed = true;
            }
        }
        if !changed {
            assert!(
                values.iter().skip(1).all(Option::is_some),
                "All gate outputs must follow from assigned choices."
            );
            return true;
        }
    }
}
fn compare(p: &Problem, controls: &[usize]) {
    let encoding = dag::encode(
        p,
        controls,
        Instant::now() + Duration::from_secs(10),
        2_000_000,
    )
    .unwrap();
    assert!(encoding.choices.len() <= 12);
    let mut any = false;
    for assignment in 0..1usize << encoding.choices.len() {
        let sat = propagate(&encoding, assignment);
        if !sat {
            continue;
        }
        any = true;
        let mut marking: Vec<_> = p.initial.iter().copied().map(BigUint::from).collect();
        for (i, &(t, _)) in encoding.choices.iter().enumerate() {
            if (assignment >> i) & 1 == 1 {
                marking = fire(p, &marking, t).expect("CNF model selected a disabled transition");
            }
        }
        assert!(satisfies(p, &marking), "CNF model failed the full target");
    }
    assert_eq!(any, reachable(p), "{p:?}");
}
fn problem(initial: Vec<u64>, transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target,
    }
}
fn tr(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "step".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}

#[test]
fn weighted_dag_nets_match_independent_big_integer_bfs() {
    let mut seed = 573987u64;
    let mut random = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for _ in 0..36 {
        let modes = 3;
        let dimensions = 6;
        let mut permutation: Vec<_> = (0..dimensions).collect();
        for i in (1..dimensions).rev() {
            permutation.swap(i, random() as usize % (i + 1));
        }
        let mut initial = vec![0; dimensions];
        initial[permutation[0]] = 1;
        for &place in &permutation[modes..] {
            initial[place] = random() % 3;
        }
        let mut transitions = vec![];
        for source in 0..modes {
            for destination in source + 1..modes {
                for _ in 0..2 {
                    let mut pre = vec![(permutation[source], 1)];
                    let mut post = vec![(permutation[destination], 1)];
                    for &place in &permutation[modes..] {
                        let input = random() % 3;
                        let output = random() % 3;
                        if input > 0 {
                            pre.push((place, input));
                        }
                        if output > 0 {
                            post.push((place, output));
                        }
                    }
                    transitions.push(tr(&pre, &post));
                }
            }
        }
        transitions.reverse();
        transitions.push(tr(
            &[(permutation[0], 2)],
            &[(permutation[0], 2), (permutation[5], 1)],
        ));
        let mut controls = permutation[..modes].to_vec();
        controls.sort_unstable();
        for variant in 0..3 {
            let coefficients = (0..dimensions).map(|_| (random() % 5) as i64 - 2).collect();
            let bound = (random() % 9) as i64 - 4;
            let target = vec![Constraint {
                coefficients,
                bound,
                equality: variant == 0,
            }];
            compare(
                &problem(initial.clone(), transitions.clone(), target),
                &controls,
            );
        }
    }
}

#[test]
fn merges_read_guards_empty_paths_and_disabled_edges() {
    let transitions = vec![
        tr(&[(3, 1), (4, 2)], &[(0, 1), (4, 2)]),
        tr(&[(3, 1)], &[(2, 1), (4, 1)]),
        tr(&[(0, 1)], &[(1, 1), (5, 2)]),
        tr(&[(2, 1), (4, 3)], &[(1, 1)]),
        tr(&[(0, 1), (2, 1)], &[(0, 1), (2, 1), (5, 1)]),
    ];
    for weight in 0..4 {
        for bound in -2..4 {
            compare(
                &problem(
                    vec![0, 0, 0, 1, weight, 0],
                    transitions.clone(),
                    vec![Constraint {
                        coefficients: vec![0, 1, 0, 0, -1, 1],
                        bound,
                        equality: true,
                    }],
                ),
                &[0, 1, 2, 3],
            );
        }
    }
    compare(&problem(vec![1], vec![], vec![]), &[0]);
    compare(
        &problem(
            vec![1],
            vec![],
            vec![Constraint {
                coefficients: vec![0],
                bound: 1,
                equality: false,
            }],
        ),
        &[0],
    );
}

#[test]
fn arithmetic_is_exact_beyond_u64_and_with_minimum_signed_coefficients() {
    let p = problem(
        vec![1, 0, 0, u64::MAX],
        vec![
            tr(&[(0, 1)], &[(1, 1), (3, 1)]),
            tr(&[(1, 1), (3, u64::MAX)], &[(2, 1)]),
        ],
        vec![
            Constraint {
                coefficients: vec![0, 0, 1, 0],
                bound: 1,
                equality: true,
            },
            Constraint {
                coefficients: vec![0, 0, 0, i64::MIN],
                bound: i64::MIN,
                equality: true,
            },
        ],
    );
    compare(&p, &[0, 1, 2]);
    let disabled = problem(
        vec![1, 0, 0],
        vec![tr(&[(0, 1), (2, u64::MAX)], &[(1, 1)])],
        vec![Constraint {
            coefficients: vec![0, 1, 0],
            bound: 1,
            equality: true,
        }],
    );
    compare(&disabled, &[0, 1]);
    let p = problem(
        vec![1, 0],
        vec![tr(&[(0, 1), (1, u64::MAX)], &[(0, 1)])],
        vec![],
    );
    assert!(dag::encode(&p, &[0], Instant::now() + Duration::from_secs(1), 10000).is_err());
}

#[test]
fn cyclic_stuttering_bad_controls_and_limits_are_rejected() {
    let deadline = Instant::now() + Duration::from_secs(1);
    for transitions in [
        vec![tr(&[(0, 1)], &[(0, 1)])],
        vec![tr(&[], &[(1, 1)])],
        vec![tr(&[(0, 1)], &[(1, 1)]), tr(&[(1, 1)], &[(0, 1)])],
    ] {
        let p = problem(vec![1, 0], transitions, vec![]);
        assert!(dag::encode(&p, &[0, 1], deadline, 10000).is_err());
    }
    let p = problem(
        vec![1, 0, 0],
        vec![tr(&[(1, 1)], &[(2, 1)]), tr(&[(2, 1)], &[(1, 1)])],
        vec![],
    );
    compare(&p, &[0, 1, 2]);
    assert!(dag::encode(&p, &[1, 0], deadline, 10000).is_err());
    assert!(dag::encode(&p, &[0, 1, 2], Instant::now(), 10000).is_err());
    assert!(dag::encode(&p, &[0, 1, 2], deadline, 1).is_err());
}

#[test]
fn python_and_rust_generate_identical_numbering_and_clauses() {
    use std::{
        io::Write,
        process::{Command, Stdio},
    };
    let fixtures = [
        (problem(vec![1], vec![], vec![]), vec![0]),
        (
            problem(
                vec![0, 0, 1, 2, 0],
                vec![
                    tr(&[(2, 1), (3, 2)], &[(0, 1), (3, 2), (4, 1)]),
                    tr(&[(2, 1)], &[(1, 1), (3, 3)]),
                    tr(&[(0, 1), (4, 1)], &[(1, 1), (3, 1)]),
                    tr(&[(0, 2)], &[(0, 2)]),
                ],
                vec![
                    Constraint {
                        coefficients: vec![0, 1, 0, -2, 3],
                        bound: -2,
                        equality: false,
                    },
                    Constraint {
                        coefficients: vec![0, 0, 0, 1, -1],
                        bound: 1,
                        equality: true,
                    },
                ],
            ),
            vec![0, 1, 2],
        ),
        (
            problem(
                vec![1, 0, 0, u64::MAX],
                vec![
                    tr(&[(0, 1)], &[(1, 1), (3, 1)]),
                    tr(&[(1, 1), (3, u64::MAX)], &[(2, 1)]),
                ],
                vec![Constraint {
                    coefficients: vec![0, 0, 1, i64::MIN],
                    bound: i64::MIN,
                    equality: true,
                }],
            ),
            vec![0, 1, 2],
        ),
        (
            problem(
                vec![1, 0, 0],
                vec![tr(&[(0, 1), (2, u64::MAX)], &[(1, 1)])],
                vec![Constraint {
                    coefficients: vec![0, 1, 0],
                    bound: 1,
                    equality: false,
                }],
            ),
            vec![0, 1],
        ),
    ];
    let inputs: Vec<_> = fixtures
        .iter()
        .map(|(p, c)| serde_json::json!({"problem":p,"control":c}))
        .collect();
    let mut child=Command::new("python3").args(["-c",
        "import json,sys; sys.path.insert(0,'scripts'); from dag_checker import encode; print(json.dumps([encode(x['problem'],x['control']).__dict__ for x in json.load(sys.stdin)]))"])
        .current_dir(env!("CARGO_MANIFEST_DIR")).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(&serde_json::to_vec(&inputs).unwrap())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let python: Vec<serde_json::Value> = serde_json::from_slice(&output.stdout).unwrap();
    for ((p, c), expected) in fixtures.iter().zip(python) {
        let actual =
            dag::encode(p, c, Instant::now() + Duration::from_secs(10), 2_000_000).unwrap();
        assert_eq!(
            serde_json::json!({"variables":actual.variables,"clauses":actual.clauses,"choices":actual.choices}),
            expected
        );
    }
}
