use std::time::{Duration, Instant};
use vass_reach::{
    capacity, linear,
    model::{Constraint, Problem, Transition},
    place_bounds,
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(5)
}

fn query(coefficients: Vec<i64>, bound: i64, equality: bool) -> Problem {
    Problem {
        places: vec!["a".into(), "b".into(), "guard".into()],
        initial: vec![1, 0, 1],
        transitions: vec![Transition {
            name: "advance".into(),
            pre: vec![(0, 1), (2, 1)],
            post: vec![(1, 1), (2, 1)],
        }],
        target: vec![Constraint {
            coefficients,
            bound,
            equality,
        }],
    }
}

fn xml(units: &str) -> String {
    format!(
        "<pnml><net><toolspecific tool='nupn'><structure root='root' safe='false'>{units}</structure></toolspecific></net></pnml>"
    )
}

fn hints() -> String {
    xml(
        "<unit id='root'><places>a</places><subunits>child</subunits></unit><unit id='child'><places>b</places><subunits/></unit>",
    )
}

fn discover(p: &Problem, xml: &str) -> capacity::Capacities {
    let seeds = capacity::target_places(std::slice::from_ref(&p.target));
    capacity::discover(p, xml, &seeds, deadline(), 100_000)
}

#[test]
fn checked_ancestry_preserves_original_indices_and_ignores_safety_assertions() {
    let p = query(vec![0, 1, 0], 2, false);
    let capacities = discover(&p, &hints());
    assert_eq!(capacities.len(), 1);
    assert_eq!(
        place_bounds::check(&p, &capacities.certificate()).unwrap(),
        vec![Some(1.into()), Some(1.into()), None]
    );
    let outcome = capacities.refute(&p, deadline()).unwrap();
    assert_eq!(outcome.method, "checked-capacity");
    assert_eq!(outcome.verdict, "unreachable");
    assert_eq!(outcome.proof.as_ref().unwrap()["kind"], "sparse-farkas-v1");
    linear::verify_certificate(&p, outcome.proof.as_ref().unwrap()).unwrap();
}

#[test]
fn signed_targets_equalities_and_minimum_integer_use_exact_row_numbers() {
    for target in [
        Constraint {
            coefficients: vec![-2, 3, 0],
            bound: 4,
            equality: false,
        },
        Constraint {
            coefficients: vec![-1, -1, 0],
            bound: -2,
            equality: true,
        },
        Constraint {
            coefficients: vec![i64::MIN, 0, 0],
            bound: 1,
            equality: false,
        },
    ] {
        let mut p = query(vec![0, 0, 0], 0, true);
        p.target.push(target);
        let capacities = discover(&p, &hints());
        let outcome = capacities.refute(&p, deadline()).unwrap();
        linear::verify_certificate(&p, outcome.proof.as_ref().unwrap()).unwrap();
    }
}

#[test]
fn false_safety_metadata_cannot_certify_a_weighted_increase() {
    let mut p = query(vec![0, 1, 0], 2, false);
    p.transitions[0].post[0].1 = 2;
    let capacities = discover(&p, &hints().replace("safe='false'", "safe='true'"));
    assert!(capacities.is_empty());
    assert!(capacities.refute(&p, deadline()).is_none());
    assert_eq!(p.check_witness(&[0]).unwrap(), vec![0, 2, 1]);
}

#[test]
fn malformed_unit_graphs_only_disable_hints() {
    let p = query(vec![0, 1, 0], 2, false);
    let malformed = [
        hints().replace("<subunits/>", "<subunits>root</subunits>"),
        hints().replace("<subunits>child</subunits>", "<subunits>missing</subunits>"),
        hints().replace("<places>b</places>", "<places>unknown</places>"),
        hints().replace("<places>b</places>", "<places>a b</places>"),
        hints().replace("id='child'", "id='root'"),
        hints().replace("<subunits>child</subunits>", "<subunits/>"),
        hints().replace("<places>b</places>", "<places>b</places><places>b</places>"),
        "not XML".into(),
    ];
    for xml in malformed {
        let capacities = discover(&p, &xml);
        assert!(capacities.is_empty(), "{xml}");
        assert!(capacities.refute(&p, deadline()).is_none());
    }
}

#[test]
fn metadata_free_backward_implications_are_independently_checked() {
    let mut p = query(vec![0, 1, 0], 2, false);
    p.transitions[0].pre.pop();
    p.transitions[0].post.pop();
    let capacities = discover(&p, "<pnml/>");
    assert_eq!(capacities.len(), 1);
    let proof = capacities.refute(&p, deadline()).unwrap().proof.unwrap();
    linear::verify_certificate(&p, &proof).unwrap();
    p.transitions[0].post[0].1 = 2;
    assert!(discover(&p, "<pnml/>").refute(&p, deadline()).is_none());
    assert!(capacities.refute(&p, deadline()).is_none());
}

#[test]
fn exhausted_discovery_and_checking_return_no_result() {
    let p = query(vec![0, 1, 0], 2, false);
    assert!(capacity::discover(&p, &hints(), &[1], Instant::now(), 100_000).is_empty());
    assert!(capacity::discover(&p, &hints(), &[1], deadline(), 0).is_empty());
    assert!(discover(&p, &hints()).refute(&p, Instant::now()).is_none());
}

#[test]
fn all_small_executions_respect_discovered_potentials() {
    for initial in 0..=3 {
        for produced in 1..=3 {
            let mut p = query(vec![0, 1, 0], 0, false);
            p.initial[0] = initial;
            p.transitions[0].post[0].1 = produced;
            let capacities = discover(&p, &hints());
            let bounds = place_bounds::check(&p, &capacities.certificate()).unwrap();
            for count in 0..=initial {
                let marking = p.check_witness(&vec![0; count as usize]).unwrap();
                for (tokens, bound) in marking.iter().zip(&bounds) {
                    if let Some(bound) = bound {
                        assert!(num_bigint::BigInt::from(*tokens) <= *bound);
                    }
                }
            }
            for bound in 0..=10 {
                p.target[0].bound = bound;
                if capacities.refute(&p, deadline()).is_some() {
                    assert!(
                        (0..=initial)
                            .all(|count| p.check_witness(&vec![0; count as usize]).is_err())
                    );
                }
            }
        }
    }
}

fn joint_target(width: usize) -> Problem {
    let mut p = Problem {
        places: (0..width + 2).map(|i| format!("p{i}")).collect(),
        initial: vec![0; width + 2],
        transitions: (0..width)
            .map(|i| Transition {
                name: format!("source{i}"),
                pre: vec![],
                post: vec![(i, 1)],
            })
            .collect(),
        target: vec![],
    };
    p.initial[width] = 1;
    p.transitions.extend([
        Transition {
            name: "forward".into(),
            pre: vec![(width, 1)],
            post: vec![(width + 1, 1)],
        },
        Transition {
            name: "back".into(),
            pre: vec![(width + 1, 1)],
            post: vec![(width, 1)],
        },
    ]);
    let mut left = vec![1; width + 2];
    left[width] = 0;
    left[width + 1] = 0;
    let mut right = vec![-1; width + 2];
    right[width] = 1;
    right[width + 1] = 0;
    p.target = vec![
        Constraint {
            coefficients: left,
            bound: 2,
            equality: false,
        },
        Constraint {
            coefficients: right,
            bound: 0,
            equality: false,
        },
    ];
    p
}

#[test]
fn joint_target_refutation_survives_a_wide_first_target_row() {
    let p = joint_target(80);
    assert!(!capacity::target_places(std::slice::from_ref(&p.target)).contains(&80));
    let seeds = capacity::target_places_by_row(std::slice::from_ref(&p.target));
    assert_eq!(seeds[0], 80);
    assert_eq!(seeds.len(), 64);
    let capacities = capacity::discover(&p, "", &seeds, deadline(), 1000000);
    assert!(capacities.refute(&p, deadline()).is_none());
    let outcome = capacities.refute_combined(&p, deadline(), 1000000).unwrap();
    assert_eq!(outcome.method, "checked-capacity-combined");
    let proof = outcome.proof.unwrap();
    linear::verify_certificate(&p, &proof).unwrap();
    assert!(capacities.refute_combined(&p, deadline(), 0).is_none());
    assert!(
        capacities
            .refute_combined(&p, Instant::now(), 1000000)
            .is_none()
    );
}

#[test]
fn combined_capacity_uses_exact_signed_row_indices_and_large_bounds() {
    for variant in 0..3 {
        let mut p = joint_target(1);
        if variant == 1 {
            p.target[0].coefficients[0] = -1;
            p.target[0].bound = -2;
            p.target[0].equality = true;
        } else if variant == 2 {
            p.target[0].coefficients[0] = i64::MAX;
            p.target[0].bound = i64::MAX;
            p.target[1].coefficients[0] = -i64::MAX;
            p.target[1].coefficients[1] = i64::MAX;
            p.target[1].bound = 1;
        }
        let seeds = capacity::target_places_by_row(std::slice::from_ref(&p.target));
        let capacities = capacity::discover(&p, "", &seeds, deadline(), 100000);
        assert!(capacities.refute(&p, deadline()).is_none());
        let out = capacities.refute_combined(&p, deadline(), 100000).unwrap();
        let proof = out.proof.unwrap();
        linear::verify_certificate(&p, &proof).unwrap();
        use std::{
            io::Write,
            process::{Command, Stdio},
        };
        let mut child=Command::new("python3").args(["-c","import json,sys;sys.path.insert(0,'scripts');from benchmark import verify_proof;p,c=json.load(sys.stdin);assert verify_proof(p,c)=='python-sparse-farkas'"])
            .current_dir(env!("CARGO_MANIFEST_DIR")).stdin(Stdio::piped()).spawn().unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(&serde_json::to_vec(&(&p, &proof)).unwrap())
            .unwrap();
        assert!(child.wait().unwrap().success());
        p.transitions[1].post[0].1 = 2;
        assert!(linear::verify_certificate(&p, &proof).is_err());
        assert!(capacities.refute_combined(&p, deadline(), 100000).is_none());
    }
}
