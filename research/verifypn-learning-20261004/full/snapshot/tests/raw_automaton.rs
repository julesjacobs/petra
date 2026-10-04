use std::{
    collections::HashSet,
    time::{Duration, Instant},
};
use vass_reach::raw_target::{RawQuery, RawTarget, SerialAutomaton, SerialEdge};

fn query(a: SerialAutomaton) -> RawQuery {
    RawQuery {
        format: "ser-raw-v2".into(),
        places: vec!["a".into(), "b".into()],
        initial: vec![0, 0],
        transitions: vec![],
        target: RawTarget {
            kind: "completed-outside-automaton".into(),
            zero_places: vec![],
            response_places: vec![0, 1],
            excluded_semilinear: vec![],
            excluded_automaton: Some(a),
        },
    }
}

#[test]
fn membership_matches_explicit_word_enumeration() {
    for seed in 0..64usize {
        let a = SerialAutomaton {
            states: 3,
            initial: seed % 3,
            accepting: (0..3).filter(|s| seed & (1 << s) != 0).collect(),
            edges: (0..9)
                .filter(|i| (seed * 17 + i * 13) % 5 < 2)
                .map(|i| SerialEdge {
                    source: i / 3,
                    target: i % 3,
                    response: (seed + i) % 2,
                })
                .collect(),
        };
        let mut words = vec![(a.initial, [0u64, 0])];
        let mut parikh = HashSet::new();
        for length in 0..=6 {
            let mut next = vec![];
            for (state, counts) in words {
                if a.accepting.contains(&state) {
                    parikh.insert(counts);
                }
                if length < 6 {
                    for e in a.edges.iter().filter(|e| e.source == state) {
                        let mut c = counts;
                        c[e.response] += 1;
                        next.push((e.target, c));
                    }
                }
            }
            words = next;
        }
        let q = query(a);
        let goals = vass_reach::raw_potential::goals(&q, Instant::now() + Duration::from_secs(1));
        for counts in &parikh {
            for goal in &goals {
                let value: i128 = counts
                    .iter()
                    .zip(&goal.coefficients)
                    .map(|(&n, &c)| i128::from(n) * i128::from(c))
                    .sum();
                assert!(
                    value < i128::from(goal.bound),
                    "serial word violates inferred bound"
                );
            }
        }
        for x in 0..=3 {
            for y in 0..=3 {
                assert_eq!(
                    q.accepts(&[x, y], Instant::now() + Duration::from_secs(1), 100_000)
                        .unwrap(),
                    !parikh.contains(&[x, y]),
                    "seed={seed}, ({x},{y})"
                );
            }
        }
    }
}

#[test]
fn validates_format_and_propagates_limits() {
    let mut q = query(SerialAutomaton {
        states: 1,
        initial: 0,
        accepting: vec![0],
        edges: vec![SerialEdge {
            source: 0,
            target: 0,
            response: 0,
        }],
    });
    assert!(
        q.accepts(&[2, 0], Instant::now() + Duration::from_secs(1), 0)
            .is_err()
    );
    assert!(q.accepts(&[2, 0], Instant::now(), 100).is_err());
    assert!(
        !q.accepts(&[0, 0], Instant::now() + Duration::from_secs(1), 100)
            .unwrap()
    );
    assert!(
        q.accepts(&[0, 1], Instant::now() + Duration::from_secs(1), 100)
            .unwrap()
    );
    q.format = "ser-raw-v1".into();
    assert!(q.validate().is_err());
    q.format = "ser-raw-v2".into();
    q.target.excluded_automaton.as_mut().unwrap().edges[0].response = 2;
    assert!(q.validate().is_err());
}

#[test]
fn missing_serial_target_is_not_an_empty_language() {
    let input = serde_json::json!({
        "format":"ser-raw-v1", "places":[], "initial":[], "transitions":[],
        "target":{"kind":"completed-outside-semilinear", "zero_places":[], "response_places":[]}
    });
    assert!(serde_json::from_value::<RawQuery>(input).is_err());
}

#[test]
fn automaton_potentials_bound_balanced_cycles_without_expansion() {
    let q = query(SerialAutomaton {
        states: 3,
        initial: 0,
        accepting: vec![0, 1, 2],
        edges: vec![
            SerialEdge {
                source: 0,
                target: 1,
                response: 0,
            },
            SerialEdge {
                source: 1,
                target: 0,
                response: 1,
            },
            SerialEdge {
                source: 2,
                target: 2,
                response: 0,
            },
        ],
    });
    let goals = vass_reach::raw_potential::goals(&q, Instant::now() + Duration::from_secs(1));
    assert!(
        goals
            .iter()
            .any(|c| c.coefficients == [1, -1] && c.bound == 2)
    );
    assert!(
        goals
            .iter()
            .any(|c| c.coefficients == [-1, 1] && c.bound == 1)
    );
    assert!(goals.iter().all(|c| c.coefficients.contains(&-1)));
    assert!(vass_reach::raw_potential::goals(&q, Instant::now()).is_empty());
}
