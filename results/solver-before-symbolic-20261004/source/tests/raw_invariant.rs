use std::time::{Duration, Instant};
use vass_reach::model::Transition;
use vass_reach::raw_invariant::{Certificate, Credit, Edge, Node, check};
use vass_reach::raw_target::{LinearSet, RawQuery, RawTarget};

fn query(
    initial: Vec<u64>,
    transitions: Vec<Transition>,
    periods: Vec<Vec<(usize, u64)>>,
) -> RawQuery {
    RawQuery {
        format: "ser-raw-v1".into(),
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target: RawTarget {
            excluded_automaton: None,
            kind: "completed-outside-semilinear".into(),
            zero_places: vec![],
            response_places: vec![0],
            excluded_semilinear: vec![LinearSet {
                base: vec![],
                periods,
            }],
        },
    }
}

fn transition(pre: Vec<(usize, u64)>, post: Vec<(usize, u64)>) -> Transition {
    Transition {
        name: "t".into(),
        pre,
        post,
    }
}

fn certificate(edges: Vec<Edge>) -> Certificate {
    Certificate {
        format: "raw-component-invariant-v1".into(),
        control_places: vec![],
        credits: vec![],
        initial_node: 0,
        initial_coefficients: vec![],
        nodes: vec![Node {
            control: vec![],
            component: 0,
            edges,
        }],
    }
}

fn growth() -> (RawQuery, Certificate) {
    (
        query(
            vec![0],
            vec![transition(vec![], vec![(0, 1)])],
            vec![vec![(0, 1)]],
        ),
        certificate(vec![Edge {
            transition: 0,
            target: 0,
            base_coefficients: vec![(0, 1)],
            period_coefficients: vec![vec![(0, 1)]],
        }]),
    )
}

fn checked(q: &RawQuery, c: &Certificate) -> anyhow::Result<()> {
    check(q, c, Instant::now() + Duration::from_secs(10), 100_000)
}

#[test]
fn proves_unbounded_growth_and_preserves_original_period_positions() {
    let (mut q, mut c) = growth();
    checked(&q, &c).unwrap();
    q.target.excluded_semilinear[0].periods.insert(0, vec![]);
    c.nodes[0].edges[0].base_coefficients = vec![(1, 1)];
    c.nodes[0].edges[0].period_coefficients = vec![vec![], vec![(1, 1)]];
    checked(&q, &c).unwrap();
}

#[test]
fn rejects_forged_omissions_and_maps() {
    let (q, c) = growth();
    let mutations: Vec<fn(&mut Certificate)> = vec![
        |c| c.nodes[0].edges.clear(),
        |c| c.nodes[0].edges[0].base_coefficients.clear(),
        |c| c.nodes[0].edges[0].period_coefficients[0].clear(),
        |c| c.nodes[0].edges[0].period_coefficients.clear(),
        |c| c.nodes[0].edges[0].period_coefficients.push(vec![]),
        |c| c.initial_coefficients = vec![(0, 1)],
        |c| c.nodes[0].edges[0].base_coefficients = vec![(1, 1)],
        |c| c.nodes[0].edges[0].base_coefficients = vec![(0, 0)],
        |c| c.nodes[0].edges[0].base_coefficients = vec![(0, 1), (0, 1)],
        |c| c.nodes[0].edges[0].transition = usize::MAX,
        |c| c.nodes[0].edges[0].target = usize::MAX,
        |c| c.nodes[0].component = usize::MAX,
        |c| c.initial_node = usize::MAX,
        |c| c.nodes[0].control.push(0),
        |c| c.control_places.push(usize::MAX),
        |c| c.nodes.push(c.nodes[0].clone()),
        |c| {
            let duplicate = c.nodes[0].edges[0].clone();
            c.nodes[0].edges.push(duplicate);
        },
        |c| c.format.push('x'),
    ];
    for (index, mutate) in mutations.into_iter().enumerate() {
        let mut forged = c.clone();
        mutate(&mut forged);
        assert!(checked(&q, &forged).is_err(), "mutation {index}");
    }
}

fn flush() -> (RawQuery, Certificate) {
    let mut q = query(
        vec![0, 1],
        vec![transition(vec![(1, 1)], vec![(0, 1)])],
        vec![],
    );
    q.target.zero_places = vec![1];
    q.target.excluded_semilinear[0].base = vec![(0, 1)];
    let mut c = certificate(vec![]);
    c.credits = vec![Credit {
        place: 1,
        terms: vec![(0, 1)],
    }];
    (q, c)
}

#[test]
fn credited_stutter_is_implicit_and_bound_to_original_arcs() {
    let (q, c) = flush();
    checked(&q, &c).unwrap();
    let mut extra = c.clone();
    extra.nodes[0].edges.push(Edge {
        transition: 0,
        target: 0,
        base_coefficients: vec![],
        period_coefficients: vec![],
    });
    assert!(checked(&q, &extra).is_err());
    let mut changed = q.clone();
    changed.transitions[0].post[0].1 = 2;
    assert!(checked(&changed, &c).is_err());
    let mut changed = c.clone();
    changed.credits.clear();
    assert!(checked(&q, &changed).is_err());
}

#[test]
fn rejects_invalid_credit_columns() {
    let (q, c) = flush();
    let mutations: Vec<fn(&mut Certificate)> = vec![
        |c| c.credits[0].place = 0,
        |c| c.credits[0].place = usize::MAX,
        |c| c.credits[0].terms = vec![(1, 1)],
        |c| c.credits[0].terms = vec![(0, 0)],
        |c| c.credits[0].terms = vec![(0, 1), (0, 1)],
        |c| c.credits.push(c.credits[0].clone()),
    ];
    for mutate in mutations {
        let mut forged = c.clone();
        mutate(&mut forged);
        assert!(checked(&q, &forged).is_err());
    }
}

#[test]
fn selected_guards_are_weighted_and_controller_moves_need_edges() {
    let q = query(
        vec![0, 2, 0],
        vec![
            transition(vec![(1, 2)], vec![(2, 1)]),
            transition(vec![(2, 1)], vec![(1, 2)]),
        ],
        vec![],
    );
    let mut c = certificate(vec![]);
    c.control_places = vec![1, 2];
    c.nodes = vec![
        Node {
            control: vec![2, 0],
            component: 0,
            edges: vec![Edge {
                transition: 0,
                target: 1,
                base_coefficients: vec![],
                period_coefficients: vec![],
            }],
        },
        Node {
            control: vec![0, 1],
            component: 0,
            edges: vec![Edge {
                transition: 1,
                target: 0,
                base_coefficients: vec![],
                period_coefficients: vec![],
            }],
        },
    ];
    checked(&q, &c).unwrap();
    let mut forged = c.clone();
    forged.nodes[1].edges.clear();
    assert!(checked(&q, &forged).is_err());
    let mut forged = c.clone();
    forged.nodes[0].edges.push(c.nodes[1].edges[0].clone());
    assert!(checked(&q, &forged).is_err());
    let mut forged = c.clone();
    forged.nodes[1].control = vec![0, 2];
    assert!(checked(&q, &forged).is_err());
    let mut forged = c.clone();
    forged.control_places = vec![2, 1];
    assert!(checked(&q, &forged).is_err());
    let mut forged = c.clone();
    forged.control_places = vec![1, 1];
    assert!(checked(&q, &forged).is_err());
}

#[test]
fn unselected_guards_cannot_justify_omitted_edges() {
    let (mut q, c) = growth();
    q.places.push("blocked".into());
    q.initial.push(0);
    q.transitions[0].pre = vec![(1, 1)];
    checked(&q, &c).unwrap();
    let mut forged = c;
    forged.nodes[0].edges.clear();
    assert!(checked(&q, &forged).is_err());
}

#[test]
fn maps_between_different_component_period_bases() {
    let mut q = query(
        vec![0, 1],
        vec![transition(vec![(1, 1)], vec![])],
        vec![vec![(0, 2)]],
    );
    q.target.excluded_semilinear.push(LinearSet {
        base: vec![],
        periods: vec![vec![(0, 1)]],
    });
    let mut c = certificate(vec![Edge {
        transition: 0,
        target: 1,
        base_coefficients: vec![],
        period_coefficients: vec![vec![(0, 2)]],
    }]);
    c.control_places = vec![1];
    c.nodes[0].control = vec![1];
    c.nodes.push(Node {
        control: vec![0],
        component: 1,
        edges: vec![],
    });
    checked(&q, &c).unwrap();
    c.nodes[0].edges[0].period_coefficients[0][0].1 = 1;
    assert!(checked(&q, &c).is_err());
}

#[test]
fn credit_products_use_exact_arithmetic() {
    let mut q = query(vec![0, u64::MAX], vec![], vec![vec![(0, u64::MAX)]]);
    q.target.zero_places = vec![1];
    let mut c = certificate(vec![]);
    c.credits = vec![Credit {
        place: 1,
        terms: vec![(0, u64::MAX)],
    }];
    c.initial_coefficients = vec![(0, u64::MAX)];
    checked(&q, &c).unwrap();
    c.initial_coefficients[0].1 = 1;
    assert!(checked(&q, &c).is_err());
}

#[test]
fn projected_control_overflow_cannot_wrap() {
    let q = query(
        vec![0, u64::MAX],
        vec![transition(vec![], vec![(1, 1)])],
        vec![],
    );
    let mut c = certificate(vec![Edge {
        transition: 0,
        target: 1,
        base_coefficients: vec![],
        period_coefficients: vec![],
    }]);
    c.control_places = vec![1];
    c.nodes[0].control = vec![u64::MAX];
    c.nodes.push(Node {
        control: vec![0],
        component: 0,
        edges: vec![],
    });
    assert!(
        checked(&q, &c)
            .unwrap_err()
            .to_string()
            .contains("successor")
    );
}

#[test]
fn sparse_coefficients_must_be_sorted() {
    let q = query(vec![2], vec![], vec![vec![(0, 1)], vec![(0, 1)]]);
    let mut c = certificate(vec![]);
    c.initial_coefficients = vec![(0, 1), (1, 1)];
    checked(&q, &c).unwrap();
    c.initial_coefficients.reverse();
    assert!(checked(&q, &c).is_err());
}

#[test]
fn resource_exhaustion_never_accepts_partial_certificate() {
    let (q, c) = growth();
    assert!(check(&q, &c, Instant::now(), usize::MAX).is_err());
    let mut threshold = None;
    for budget in 0..1000 {
        if check(&q, &c, Instant::now() + Duration::from_secs(10), budget).is_ok() {
            threshold = Some(budget);
            break;
        }
    }
    let threshold = threshold.unwrap();
    assert!(threshold > 10);
    let mut forged = c;
    forged.nodes[0].edges[0].period_coefficients[0].clear();
    for budget in 0..=threshold + 10 {
        assert!(
            check(
                &q,
                &forged,
                Instant::now() + Duration::from_secs(10),
                budget
            )
            .is_err()
        );
    }
}

#[test]
fn schema_rejects_signed_coefficients_and_unknown_fields() {
    let (_, c) = growth();
    let mut value = serde_json::to_value(&c).unwrap();
    value["initial_coefficients"] = serde_json::json!([[0, -1]]);
    assert!(serde_json::from_value::<Certificate>(value).is_err());
    let mut value = serde_json::to_value(&c).unwrap();
    value["nodes"][0]["assume_safe"] = serde_json::json!(true);
    assert!(serde_json::from_value::<Certificate>(value).is_err());
}
