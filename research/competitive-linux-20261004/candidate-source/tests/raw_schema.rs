use std::time::{Duration, Instant};
use vass_reach::raw_invariant::{Certificate as Invariant, Credit, Node};
use vass_reach::raw_schema::{Certificate, Schema, Segment, check, semilinear_query};
use vass_reach::raw_target::RawQuery;

fn fixture() -> (RawQuery, Certificate) {
    let q = serde_json::from_value(serde_json::json!({
        "format":"ser-raw-v2", "places":["response","pending"],"initial":[0,1],
        "transitions":[{"name":"finish","pre":[[1,1]],"post":[[0,2]]}],
        "target":{"kind":"completed-outside-automaton","zero_places":[1],"response_places":[0],
            "excluded_automaton":{"states":2,"initial":0,"accepting":[0],"edges":[
                {"source":0,"target":1,"response":0},{"source":1,"target":0,"response":0}]}}
    }))
    .unwrap();
    let proof = Certificate {
        format: "raw-automaton-invariant-v1".into(),
        schemas: vec![Schema {
            segments: vec![Segment {
                path: vec![],
                cycles: vec![vec![0, 1]],
            }],
        }],
        invariant: Invariant {
            format: "raw-component-invariant-v1".into(),
            control_places: vec![],
            credits: vec![Credit {
                place: 1,
                terms: vec![(0, 2)],
            }],
            initial_node: 0,
            initial_coefficients: vec![(0, 1)],
            nodes: vec![Node {
                control: vec![],
                component: 0,
                edges: vec![],
            }],
        },
    };
    (q, proof)
}
fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(2)
}

#[test]
fn checked_serial_sublanguage_proves_original_automaton_target() {
    let (q, proof) = fixture();
    check(&q, &proof, deadline(), 10_000).unwrap();
    let (subset, _) = semilinear_query(&q, &proof.schemas, deadline(), 10_000).unwrap();
    assert_eq!(
        subset.target.excluded_semilinear[0].periods,
        vec![vec![(0, 2)]]
    );
    assert!(subset.target.excluded_semilinear[0].base.is_empty());
    assert!(!q.accepts(&[2, 0], deadline(), 10_000).unwrap());
    assert!(q.accepts(&[1, 0], deadline(), 10_000).unwrap());
}

#[test]
fn forged_paths_cycles_and_original_net_are_rejected() {
    let (q, proof) = fixture();
    for path in [vec![0], vec![1, 0], vec![2], vec![]] {
        let mut bad = proof.clone();
        bad.schemas[0].segments[0].cycles = vec![path];
        assert!(check(&q, &bad, deadline(), 10_000).is_err());
    }
    let mut bad = proof.clone();
    bad.schemas[0].segments[0].path = vec![0];
    assert!(check(&q, &bad, deadline(), 10_000).is_err());
    let mut changed = q.clone();
    changed.transitions[0].post = vec![(0, 1)];
    assert!(check(&changed, &proof, deadline(), 10_000).is_err());
    assert!(check(&q, &proof, deadline(), 0).is_err());
    assert!(check(&q, &proof, Instant::now(), 10_000).is_err());
}
