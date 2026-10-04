use std::time::{Duration, Instant};
use vass_reach::{
    model::{Problem, Transition},
    word_discovery::{Limits, discover},
};
fn cyclic() -> Problem {
    Problem {
        places: vec!["a".into(), "b".into(), "count".into()],
        initial: vec![1, 0, 0],
        target: vec![],
        transitions: vec![
            Transition {
                name: "a-to-b".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1), (2, 1)],
            },
            Transition {
                name: "b-to-a".into(),
                pre: vec![(1, 1)],
                post: vec![(0, 1)],
            },
        ],
    }
}
fn limits() -> Limits {
    Limits {
        max_work: 1000,
        max_length: 8,
        extra_words: 16,
    }
}
#[test]
fn finds_control_cycle_rotations_and_keeps_all_singletons() {
    let result = discover(&cyclic(), limits(), Instant::now() + Duration::from_secs(1)).unwrap();
    assert_eq!(result.words, vec![vec![0], vec![1], vec![0, 1], vec![1, 0]]);
    assert!(!result.truncated);
}
#[test]
fn work_exhaustion_preserves_complete_singleton_vocabulary() {
    let result = discover(
        &cyclic(),
        Limits {
            max_work: 2,
            ..limits()
        },
        Instant::now() + Duration::from_secs(1),
    )
    .unwrap();
    assert_eq!(result.words, vec![vec![0], vec![1]]);
    assert!(result.truncated);
    assert!(result.work <= 2);
}
#[test]
fn length_limit_and_deadline() {
    let result = discover(
        &cyclic(),
        Limits {
            max_length: 1,
            ..limits()
        },
        Instant::now() + Duration::from_secs(1),
    )
    .unwrap();
    assert_eq!(result.words, vec![vec![0], vec![1]]);
    assert!(discover(&cyclic(), limits(), Instant::now()).is_err());
}
#[test]
fn shared_read_arcs_do_not_create_production_dependencies() {
    let mut p = cyclic();
    for t in &mut p.transitions {
        t.pre = vec![(0, 1)];
        t.post = vec![(0, 1)];
    }
    let result = discover(&p, limits(), Instant::now() + Duration::from_secs(1)).unwrap();
    assert_eq!(result.words, vec![vec![0], vec![1]]);
}
