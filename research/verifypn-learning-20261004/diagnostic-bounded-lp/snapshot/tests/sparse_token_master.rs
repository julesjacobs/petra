use num_bigint::BigInt;
use num_traits::Zero;
use std::collections::BTreeMap;
use vass_reach::{
    control::{self, Control},
    linear::{Row, System},
    model::{Constraint, Problem, Transition},
    token_cut, token_flow,
};

fn row(terms: impl IntoIterator<Item = (usize, BigInt)>, bound: BigInt) -> Row {
    let mut coefficients = BTreeMap::<usize, BigInt>::new();
    for (index, coefficient) in terms {
        *coefficients.entry(index).or_default() += coefficient;
    }
    Row {
        coefficients: coefficients
            .into_iter()
            .filter(|(_, a)| !a.is_zero())
            .collect(),
        bound,
    }
}

fn equality(system: &mut System, row: Row) {
    system.rows.push(Row {
        coefficients: row.coefficients.iter().map(|(i, a)| (*i, -a)).collect(),
        bound: -&row.bound,
    });
    system.rows.push(row);
}

fn dense_master(p: &Problem, graph: &Control, terminal: usize) -> System {
    let edges = graph.edges.len();
    let mut system = System {
        variables: edges + p.places.len(),
        rows: vec![],
    };
    for i in 0..p.places.len() {
        let mut terms = vec![(edges + i, 1.into())];
        terms.extend(graph.edges.iter().enumerate().map(|(e, edge)| {
            let transition = &p.transitions[edge.transition];
            let pre = transition
                .pre
                .iter()
                .find(|&&(j, _)| j == i)
                .map_or(0, |&(_, w)| w);
            let post = transition
                .post
                .iter()
                .find(|&&(j, _)| j == i)
                .map_or(0, |&(_, w)| w);
            (e, BigInt::from(pre) - BigInt::from(post))
        }));
        equality(&mut system, row(terms, p.initial[i].into()));
    }
    for &i in &graph.places {
        equality(
            &mut system,
            row(
                [(edges + i, 1.into())],
                u8::from(graph.modes[terminal] == i).into(),
            ),
        );
    }
    for c in &p.target {
        let target = row(
            c.coefficients
                .iter()
                .enumerate()
                .map(|(i, &a)| (edges + i, a.into())),
            c.bound.into(),
        );
        if c.equality {
            equality(&mut system, target);
        } else {
            system.rows.push(target);
        }
    }
    for q in 0..graph.modes.len() {
        let terms = graph.edges.iter().enumerate().map(|(e, edge)| {
            (
                e,
                (i32::from(edge.source == q) - i32::from(edge.target == q)).into(),
            )
        });
        equality(
            &mut system,
            row(
                terms,
                (i32::from(q == graph.initial) - i32::from(q == terminal)).into(),
            ),
        );
    }
    system
}

fn fixture(variant: usize) -> Problem {
    let weight = [1, 2, 7, u64::MAX][variant % 4];
    let mut initial = vec![weight, 0, 1, 0, 0, 0];
    initial[[1, 3, 5][variant % 3]] = 1;
    let transition = |name: &str, pre, post| Transition {
        name: name.into(),
        pre,
        post,
    };
    Problem {
        places: ["x", "A", "y", "B", "z", "C"].map(String::from).to_vec(),
        initial,
        transitions: vec![
            transition(
                "read-and-advance",
                vec![(1, 1), (0, weight)],
                vec![(3, 1), (0, weight)],
            ),
            transition(
                "convert-and-advance",
                vec![(3, 1), (2, 1)],
                vec![(5, 1), (0, weight)],
            ),
            transition("return", vec![(5, 1)], vec![(1, 1)]),
            transition("source", vec![], vec![(4, weight)]),
            transition("sink", vec![(4, weight)], vec![]),
            transition("read", vec![(0, weight)], vec![(0, weight)]),
            transition("control-self-loop", vec![(3, 1)], vec![(3, 1), (2, weight)]),
            transition(
                "disabled-two-controls",
                vec![(1, 1), (3, 1)],
                vec![(1, 1), (3, 1)],
            ),
        ],
        target: vec![
            Constraint {
                coefficients: vec![-3, 0, 2, 0, 0, 0],
                bound: -2,
                equality: variant.is_multiple_of(2),
            },
            Constraint {
                coefficients: vec![0, 1, i64::MIN, -1, 0, 0],
                bound: i64::MIN,
                equality: variant.is_multiple_of(3),
            },
        ],
    }
}

fn same_rows(actual: &[Row], expected: &[Row]) {
    assert_eq!(actual.len(), expected.len());
    for (index, (actual, expected)) in actual.iter().zip(expected).enumerate() {
        assert_eq!(
            actual.coefficients, expected.coefficients,
            "coefficients at row {index}"
        );
        assert_eq!(actual.bound, expected.bound, "bound at row {index}");
    }
}

#[test]
fn sparse_master_preserves_dense_rows_and_reference_moment_rows() {
    for variant in 0..24 {
        let p = fixture(variant);
        let graph = control::build(&p, &[1, 3, 5], 100).unwrap();
        assert_eq!(graph.modes.len(), 3);
        assert!(!graph.edges.iter().any(|edge| edge.transition == 7));
        for terminal in 0..graph.modes.len() {
            let sparse = token_cut::master(&p, &graph, terminal).unwrap();
            let dense = dense_master(&p, &graph, terminal);
            assert_eq!(sparse.variables, dense.variables);
            same_rows(&sparse.rows, &dense.rows);
            let reference = token_flow::relaxation(&p, &graph, terminal).unwrap();
            let prefix = 2 * (p.places.len() + graph.places.len())
                + p.target
                    .iter()
                    .map(|c| 1 + usize::from(c.equality))
                    .sum::<usize>();
            same_rows(&sparse.rows[..prefix], &reference.rows[..prefix]);
            for mode in 0..graph.modes.len() {
                let reference_offset = prefix + mode * 2 * (p.places.len() + 1);
                same_rows(
                    &sparse.rows[prefix + mode * 2..prefix + mode * 2 + 2],
                    &reference.rows[reference_offset..reference_offset + 2],
                );
            }
        }
    }
}

#[test]
fn edgeless_projection_preserves_unreachable_control_coordinates() {
    let mut p = fixture(0);
    p.transitions.clear();
    let graph = control::build(&p, &[1, 3, 5], 100).unwrap();
    assert_eq!(graph.modes.len(), 1);
    same_rows(
        &token_cut::master(&p, &graph, 0).unwrap().rows,
        &dense_master(&p, &graph, 0).rows,
    );
}

#[test]
fn dimensions_and_invalid_coordinates_return_errors() {
    let p = fixture(0);
    let graph = control::build(&p, &[1, 3, 5], 100).unwrap();
    assert!(token_cut::master(&p, &graph, graph.modes.len()).is_err());
    for variant in 0..6 {
        let mut changed = graph.clone();
        match variant {
            0 => changed.initial = usize::MAX,
            1 => changed.modes[0] = usize::MAX,
            2 => changed.places[0] = usize::MAX,
            3 => changed.edges[0].source = usize::MAX,
            4 => changed.edges[0].target = usize::MAX,
            _ => changed.edges[0].transition = usize::MAX,
        }
        assert!(token_cut::master(&p, &changed, 0).is_err());
    }
    let mut invalid = p.clone();
    invalid.initial.pop();
    assert!(token_cut::master(&invalid, &graph, 0).is_err());
    let mut large = p;
    large.places.resize(100_001, String::new());
    assert!(token_cut::master(&large, &graph, 0).is_err());
}
