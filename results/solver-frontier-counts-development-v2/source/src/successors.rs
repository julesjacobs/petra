use crate::model::Problem;

/// Every non-source transition has exactly one anchor in its preset.
pub(crate) struct TransitionIndex {
    sources: Vec<usize>,
    anchors: Vec<(usize, Vec<(usize, u64)>)>,
    active: Vec<usize>,
}

impl TransitionIndex {
    pub fn new(p: &Problem) -> Self {
        let presets: Vec<_> = p.transitions.iter().map(|t| t.pre.as_slice()).collect();
        Self::from_presets(p.places.len(), &presets)
    }

    pub fn from_presets(places: usize, presets: &[&[(usize, u64)]]) -> Self {
        let mut readers = vec![0usize; places];
        for &pre in presets {
            for &(place, _) in pre {
                readers[place] += 1;
            }
        }
        let active = (0..readers.len()).filter(|&i| readers[i] != 0).collect();
        let mut sources = Vec::new();
        let mut buckets = vec![Vec::new(); places];
        for (t, pre) in presets.iter().enumerate() {
            match pre
                .iter()
                .min_by_key(|&&(place, _)| (readers[place], place))
            {
                Some(&(place, weight)) => buckets[place].push((t, weight)),
                None => sources.push(t),
            }
        }
        let anchors = buckets
            .into_iter()
            .enumerate()
            .filter(|(_, ts)| !ts.is_empty())
            .collect();
        Self {
            sources,
            anchors,
            active,
        }
    }

    pub fn active_places(&self) -> &[usize] {
        &self.active
    }

    /// Returns a superset of enabled transitions in original transition order.
    /// Callers must still check the complete weighted preset before firing.
    pub fn candidates(&self, marking: &[u64], output: &mut Vec<usize>) {
        output.clear();
        output.extend_from_slice(&self.sources);
        for (place, ts) in &self.anchors {
            if marking[*place] != 0 {
                output.extend(
                    ts.iter()
                        .filter_map(|&(t, w)| (marking[*place] >= w).then_some(t)),
                );
            }
        }
        output.sort_unstable();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Transition;

    #[test]
    fn indexed_successors_match_full_scan_on_weighted_nets() {
        let mut seed = 20260928u64;
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for case in 0..256 {
            let n = 1 + case % 9;
            let mut p = Problem {
                places: (0..n).map(|i| format!("p{i}")).collect(),
                initial: vec![0; n],
                transitions: vec![],
                target: vec![],
            };
            for t in 0..case % 17 {
                let mut arcs = || {
                    (0..n)
                        .filter_map(|i| {
                            let w = next() % 7;
                            (w < 3).then_some((i, w + 1))
                        })
                        .collect()
                };
                p.transitions.push(Transition {
                    name: format!("t{t}"),
                    pre: arcs(),
                    post: arcs(),
                });
            }
            p.validate().unwrap();
            let index = TransitionIndex::new(&p);
            let mut candidates = vec![];
            for _ in 0..32 {
                let marking: Vec<_> = (0..n)
                    .map(|_| match next() % 9 {
                        0 => u64::MAX,
                        v => v % 5,
                    })
                    .collect();
                index.candidates(&marking, &mut candidates);
                assert!(candidates.windows(2).all(|w| w[0] < w[1]));
                let successors = |ts: Vec<usize>| {
                    ts.into_iter()
                        .filter_map(|t| match p.fire(&marking, t) {
                            Ok(None) => None,
                            Ok(Some(m)) => Some((t, Ok(m))),
                            Err(e) => Some((t, Err(e.to_string()))),
                        })
                        .collect::<Vec<_>>()
                };
                assert_eq!(
                    successors(candidates.clone()),
                    successors((0..p.transitions.len()).collect()),
                    "case {case}"
                );
            }
        }
    }

    #[test]
    fn sparse_marking_skips_unmarked_presets_and_keeps_sources() {
        let mut p = Problem {
            places: (0..1000).map(|i| format!("p{i}")).collect(),
            initial: vec![0; 1000],
            transitions: vec![],
            target: vec![],
        };
        for i in 0..1000 {
            p.transitions.push(Transition {
                name: format!("t{i}"),
                pre: vec![(i, 2)],
                post: vec![],
            });
        }
        p.transitions.push(Transition {
            name: "source".into(),
            pre: vec![],
            post: vec![(0, 1)],
        });
        let index = TransitionIndex::new(&p);
        assert_eq!(index.active_places().len(), 1000);
        let mut candidates = vec![];
        p.initial[13] = 2;
        p.initial[20] = 1;
        index.candidates(&p.initial, &mut candidates);
        assert_eq!(candidates, vec![13, 1000]);
        p.initial[13] = 0;
        index.candidates(&p.initial, &mut candidates);
        assert_eq!(candidates, vec![1000]);
    }
}
