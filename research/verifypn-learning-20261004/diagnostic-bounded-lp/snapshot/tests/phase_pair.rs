use std::{
    collections::{HashSet, VecDeque},
    io::Write,
    process::{Command, Stdio},
    time::{Duration, Instant},
};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    phase_pair::{self, Certificate},
};

fn ring(size: usize) -> Problem {
    let mut p = Problem {
        places: (0..size * size + 2).map(|i| format!("p{i}")).collect(),
        initial: vec![0; size * size + 2],
        transitions: vec![],
        target: vec![],
    };
    for i in 0..size {
        p.initial[i * size + i] = 1;
    }
    p.initial[size * size] = 1;
    p.initial[size * size + 1] = 1;
    for i in 1..size {
        for old in 0..size {
            for value in 0..size {
                if old != value {
                    p.transitions.push(Transition {
                        name: format!("copy-{i}-{old}-{value}"),
                        pre: vec![((i - 1) * size + value, 1), (i * size + old, 1)],
                        post: vec![((i - 1) * size + value, 1), (i * size + value, 1)],
                    });
                }
            }
        }
    }
    for value in 0..size {
        p.transitions.push(Transition {
            name: format!("change-{value}"),
            pre: vec![(value, 1), ((size - 1) * size + value, 1)],
            post: vec![((value + 1) % size, 1), ((size - 1) * size + value, 1)],
        });
    }
    for place in [size + size - 1, 2 * size + 1] {
        let mut coefficients = vec![0; p.places.len()];
        coefficients[place] = 1;
        p.target.push(Constraint {
            coefficients,
            bound: 1,
            equality: false,
        });
    }
    p
}
fn exhaustive(p: &Problem) -> bool {
    let mut todo = VecDeque::from([p.initial.clone()]);
    let mut seen = HashSet::from([p.initial.clone()]);
    while let Some(m) = todo.pop_front() {
        if p.accepts(&m).unwrap() {
            return true;
        }
        for t in &p.transitions {
            if t.pre.iter().all(|&(i, w)| m[i] >= w) {
                let mut next = m.clone();
                for &(i, w) in &t.pre {
                    next[i] -= w;
                }
                for &(i, w) in &t.post {
                    next[i] += w;
                }
                if seen.insert(next.clone()) {
                    todo.push_back(next);
                }
            }
        }
        assert!(seen.len() < 10000);
    }
    false
}
fn proof(p: &Problem) -> Certificate {
    let out = phase_pair::solve(p, Duration::from_secs(10), 1_000_000);
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    serde_json::from_value(out.proof.unwrap()).unwrap()
}
fn python(p: &Problem, c: &Certificate) -> bool {
    let mut child=Command::new("python3").args(["-c","import json,sys;sys.path.insert(0,'scripts');from phase_pair_checker import verify_phase_pair;p,c=json.load(sys.stdin);verify_phase_pair(p,c)"]).current_dir(env!("CARGO_MANIFEST_DIR")).stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(&serde_json::to_vec(&(p, c)).unwrap())
        .unwrap();
    child.wait().unwrap().success()
}
#[test]
fn phase_partition_refutes_a_safe_net_and_independent_checker_accepts() {
    let p = ring(4);
    assert!(!exhaustive(&p));
    let c = proof(&p);
    phase_pair::verify(&p, &c, Instant::now() + Duration::from_secs(5)).unwrap();
    assert!(python(&p, &c));
}
#[test]
fn cross_phase_frame_pairs_are_mandatory() {
    let p = ring(4);
    let mut c = proof(&p);
    let a = p.places.len() - 2;
    let b = a + 1;
    assert_ne!(c.relations[1][a][b / 64] & (1 << (b % 64)), 0);
    c.relations[1][a][b / 64] &= !(1 << (b % 64));
    c.relations[1][b][a / 64] &= !(1 << (a % 64));
    assert!(phase_pair::verify(&p, &c, Instant::now() + Duration::from_secs(5)).is_err());
    assert!(!python(&p, &c));
}
#[test]
fn forged_safety_initial_pairs_conflicts_and_padding_are_rejected() {
    let p = ring(4);
    let c = proof(&p);
    let mut bad = c.clone();
    bad.groups[0].push(p.places.len());
    assert!(!python(&p, &bad));
    let mut changed = p.clone();
    changed.transitions.push(Transition {
        name: "source".into(),
        pre: vec![],
        post: vec![(0, 1)],
    });
    assert!(!python(&changed, &c));
    assert!(phase_pair::verify(&changed, &c, Instant::now() + Duration::from_secs(5)).is_err());
    let mut bad = c.clone();
    bad.relations[0][0][0] &= !1;
    assert!(!python(&p, &bad));
    let mut bad = c.clone();
    bad.conflicts[0].left.negated = true;
    assert!(!python(&p, &bad));
    let mut bad = c.clone();
    bad.relations[0][0][0] |= 1 << 63;
    assert!(!python(&p, &bad));
}
#[test]
fn phase_closure_never_refutes_exhaustively_reachable_targets() {
    let mut p = ring(3);
    for a in 0..9 {
        for b in a..9 {
            for (row, place) in p.target.iter_mut().zip([a, b]) {
                row.coefficients.fill(0);
                row.coefficients[place] = 1;
            }
            let reachable = exhaustive(&p);
            let out = phase_pair::solve(&p, Duration::from_secs(2), 100000);
            if reachable {
                assert_eq!(out.verdict, "unknown", "incorrect refutation of {a},{b}");
            }
            if out.verdict == "unreachable" {
                assert!(!reachable);
            }
        }
    }
}
#[test]
fn zero_deadlines_and_pair_limits_do_not_prove_anything() {
    let p = ring(4);
    assert_eq!(
        phase_pair::solve(&p, Duration::ZERO, 100000).verdict,
        "unknown"
    );
    assert_eq!(
        phase_pair::solve(&p, Duration::from_secs(5), 0).verdict,
        "unknown"
    );
}

#[test]
fn cli_exports_and_verifies_phase_pair_proof() {
    let dir = std::env::temp_dir().join(format!("pvass-phase-pair-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let input = dir.join("input.json");
    let answer = dir.join("answer.json");
    std::fs::write(&input, serde_json::to_vec(&ring(4)).unwrap()).unwrap();
    let exe = env!("CARGO_BIN_EXE_vass-reach");
    let out = Command::new(exe)
        .args([
            "--json",
            input.to_str().unwrap(),
            "--method",
            "phase-pair",
            "--seconds",
            "5",
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let decoded: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(decoded["verdict"], "unreachable");
    std::fs::write(&answer, out.stdout).unwrap();
    let checked = Command::new(exe)
        .args([
            "--json",
            input.to_str().unwrap(),
            "--verify",
            answer.to_str().unwrap(),
            "--seconds",
            "5",
        ])
        .output()
        .unwrap();
    assert!(
        checked.status.success(),
        "{}",
        String::from_utf8_lossy(&checked.stderr)
    );
    std::fs::remove_file(input).unwrap();
    std::fs::remove_file(answer).unwrap();
    std::fs::remove_dir(dir).unwrap();
}

#[test]
fn uniform_closure_is_checked_but_loses_the_phase_distinction() {
    let mut p = ring(4);
    let out = phase_pair::solve_uniform(&p, Duration::from_secs(5), 100000);
    assert_eq!(out.verdict, "unknown");
    assert_eq!(
        out.reason,
        "closed pair abstraction does not exclude target"
    );
    for (row, place) in p.target.iter_mut().zip([0, 1]) {
        row.coefficients.fill(0);
        row.coefficients[place] = 1;
    }
    assert!(!exhaustive(&p));
    let out = phase_pair::solve_uniform(&p, Duration::from_secs(5), 100000);
    assert_eq!(out.verdict, "unreachable");
    let c: Certificate = serde_json::from_value(out.proof.unwrap()).unwrap();
    assert!(c.landmarks.is_empty());
    assert!(c.relations[1].iter().flatten().all(|&word| word == 0));
    phase_pair::verify(&p, &c, Instant::now() + Duration::from_secs(5)).unwrap();
    assert!(python(&p, &c));
}

#[test]
fn weighted_safe_nets_and_signed_targets_match_explicit_reachability() {
    let mut checked = Vec::new();
    let mut positives = 0;
    let mut negatives = 0;
    for seed in 0..8usize {
        let mut p = Problem {
            places: (0..7).map(|i| format!("p{i}")).collect(),
            initial: vec![1, 0, 0, 1, 0, 0, 1],
            transitions: vec![],
            target: vec![],
        };
        for group in 0..2 {
            for source in 0..3 {
                for dest in 0..3 {
                    if source == dest {
                        continue;
                    }
                    let mut pre = vec![(3 * group + source, 1)];
                    let mut post = vec![(3 * group + dest, 1)];
                    let guard = (source + 2 * dest + seed) % 4;
                    if guard < 3 {
                        let place = 3 * (1 - group) + guard;
                        pre.push((place, 1));
                        post.push((place, 1));
                    }
                    if (source + dest + seed).is_multiple_of(3) {
                        pre.push((6, 1));
                        post.push((6, 1));
                    }
                    p.transitions.push(Transition {
                        name: format!("move-{group}-{source}-{dest}"),
                        pre,
                        post,
                    });
                }
            }
        }
        p.transitions.push(Transition {
            name: "disabled-weighted".into(),
            pre: vec![(0, 2)],
            post: vec![(1, 2)],
        });
        if seed.is_multiple_of(2) {
            p.transitions.push(Transition {
                name: "consume".into(),
                pre: vec![(2, 1)],
                post: vec![],
            });
        }
        for left in 0..6 {
            for right in left..6 {
                p.target = [left, right]
                    .into_iter()
                    .enumerate()
                    .map(|(index, place)| {
                        let mut coefficients = vec![0; 7];
                        let negated = (seed + index).is_multiple_of(2);
                        let value = if negated {
                            if seed == 0 { i64::MIN } else { -1 }
                        } else {
                            1
                        };
                        coefficients[place] = value;
                        Constraint {
                            coefficients,
                            bound: value,
                            equality: negated,
                        }
                    })
                    .collect();
                let reachable = exhaustive(&p);
                positives += usize::from(reachable);
                for solve in [phase_pair::solve, phase_pair::solve_uniform] {
                    let answer = solve(&p, Duration::from_secs(2), 100000);
                    if reachable {
                        assert_eq!(
                            answer.verdict, "unknown",
                            "seed={seed}, pair={left},{right}"
                        );
                    } else if answer.verdict == "unreachable" {
                        negatives += 1;
                        let c: Certificate = serde_json::from_value(answer.proof.unwrap()).unwrap();
                        phase_pair::verify(&p, &c, Instant::now() + Duration::from_secs(2))
                            .unwrap();
                        checked.push((p.clone(), c));
                    }
                }
            }
        }
    }
    assert!(positives > 0 && negatives > 0);
    let mut child = Command::new("python3")
        .args(["-c", "import json,sys;sys.path.insert(0,'scripts');from phase_pair_checker import verify_phase_pair;[(verify_phase_pair(p,c)) for p,c in json.load(sys.stdin)]"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(&serde_json::to_vec(&checked).unwrap())
        .unwrap();
    assert!(child.wait().unwrap().success());
}
