use vass_reach::model::{Constraint, Problem, Transition};

fn problem(pre: Vec<(usize, u64)>, post: Vec<(usize, u64)>) -> Problem {
    Problem {
        places: vec!["p".into(), "q".into(), "r".into()],
        initial: vec![0; 3],
        transitions: vec![Transition {
            name: "t".into(),
            pre,
            post,
        }],
        target: vec![],
    }
}

#[test]
fn arc_validation_matches_sorted_uniqueness() {
    let mut seed = 17u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for _ in 0..1000 {
        let arcs: Vec<_> = (0..next() % 6)
            .map(|_| ((next() % 4) as usize, next() % 3))
            .collect();
        let mut places: Vec<_> = arcs.iter().map(|&(p, _)| p).collect();
        places.sort_unstable();
        let expected =
            arcs.iter().all(|&(p, w)| p < 3 && w > 0) && places.windows(2).all(|w| w[0] != w[1]);
        let mut p = problem(arcs.clone(), arcs);
        p.transitions.push(p.transitions[0].clone());
        assert_eq!(p.validate().is_ok(), expected);
    }
}

#[test]
fn validates_dimensions_and_independent_read_arcs() {
    let mut p = problem(vec![(2, 3), (0, 1)], vec![(0, 2), (2, 3)]);
    p.transitions.push(p.transitions[0].clone());
    assert!(p.validate().is_ok());
    p.initial.pop();
    assert!(p.validate().is_err());
    p.initial.push(0);
    p.target.push(Constraint {
        coefficients: vec![1, 0],
        bound: 0,
        equality: false,
    });
    assert!(p.validate().is_err());
    p.target[0].coefficients.push(0);
    assert!(p.validate().is_ok());
}
