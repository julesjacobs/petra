use num_bigint::BigInt;
use vass_reach::{
    accelerated_bmc::{self, Segment},
    model::{Constraint, Problem, Transition},
};

fn problem(initial: u64, pre: u64, post: u64) -> Problem {
    Problem {
        places: vec!["p".into()],
        initial: vec![initial],
        transitions: vec![Transition {
            name: "t".into(),
            pre: if pre == 0 { vec![] } else { vec![(0, pre)] },
            post: if post == 0 { vec![] } else { vec![(0, post)] },
        }],
        target: vec![],
    }
}

#[test]
fn compressed_replay_matches_every_small_prefix() {
    for initial in 0..8 {
        for pre in 0..5 {
            for post in 0..5 {
                let p = problem(initial, pre, post);
                for count in 0..12 {
                    let mut actual = Some(p.initial.clone());
                    for _ in 0..count {
                        actual = actual.and_then(|m| p.fire(&m, 0).unwrap());
                    }
                    let segment = Segment {
                        word: vec![0],
                        repetitions: count.to_string(),
                    };
                    let checked = accelerated_bmc::check(&p, &[segment]).ok();
                    assert_eq!(
                        checked,
                        actual.map(|m| m.into_iter().map(BigInt::from).collect())
                    );
                }
            }
        }
    }
}

#[test]
fn repeated_word_preserves_internal_read_guard() {
    let mut p = problem(0, 0, 1);
    p.transitions.push(Transition {
        name: "read_then_consume".into(),
        pre: vec![(0, 2)],
        post: vec![(0, 1)],
    });
    let word = Segment {
        word: vec![0, 1],
        repetitions: "1000000000000000000000000000000".into(),
    };
    assert!(accelerated_bmc::check(&p, std::slice::from_ref(&word)).is_err());
    p.initial[0] = 1;
    assert_eq!(
        accelerated_bmc::check(&p, &[word]).unwrap(),
        vec![BigInt::from(1)]
    );
}

#[test]
fn arbitrary_precision_witness_and_signed_target() {
    let mut p = problem(0, 0, 1);
    let segments = vec![Segment {
        word: vec![0],
        repetitions: "1000000000000000000000000000000".into(),
    }];
    p.target.push(Constraint {
        coefficients: vec![1],
        bound: i64::MAX,
        equality: false,
    });
    assert!(accelerated_bmc::check(&p, &segments).is_ok());
    p.target[0].coefficients[0] = -1;
    assert!(accelerated_bmc::check(&p, &segments).is_err());
}

#[test]
fn malformed_models_and_words_are_rejected() {
    let words = vec![vec![0]];
    for model in [
        "unsat",
        "sat ((w0 0) (n0 -1))",
        "sat ((w0 0) (w0 0))",
        "sat ((w0 1) (n0 1))",
        "sat ((w0 0))",
    ] {
        assert!(
            accelerated_bmc::decode(&words, 1, model).is_err(),
            "{model}"
        );
    }
    assert!(accelerated_bmc::encode(&problem(0, 0, 1), &[vec![2]], 1).is_err());
    assert!(
        accelerated_bmc::check(
            &problem(0, 0, 1),
            &[Segment {
                word: vec![],
                repetitions: "0".into()
            }]
        )
        .is_err()
    );
}
