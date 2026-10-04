/// Canonical for a fixed dimension; sparse storage is used only when it is smaller.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(crate) enum StoredMarking {
    Dense(Box<[u64]>),
    Sparse(Box<[(usize, u64)]>),
}

impl StoredMarking {
    pub fn new(marking: &[u64]) -> Self {
        Self::from_values(marking.iter().copied())
    }

    pub fn project(marking: &[u64], places: &[usize]) -> Self {
        Self::from_values(places.iter().map(|&i| marking[i]))
    }

    fn from_values(values: impl ExactSizeIterator<Item = u64> + Clone) -> Self {
        let nonzero = values.clone().filter(|&n| n != 0).count();
        if nonzero < values.len().div_ceil(2) {
            Self::Sparse(values.enumerate().filter(|&(_, n)| n != 0).collect())
        } else {
            Self::Dense(values.collect())
        }
    }

    pub fn write_to(&self, output: &mut [u64]) {
        match self {
            Self::Dense(values) => output.copy_from_slice(values),
            Self::Sparse(values) => {
                output.fill(0);
                for &(i, n) in values {
                    output[i] = n;
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn every_encoding_restores_exact_markings_and_hash_identity() {
        for n in 0usize..=6 {
            let mut encodings = HashSet::new();
            for code in 0..3usize.pow(n as u32) {
                let mut digits = code;
                let original: Vec<_> = (0..n)
                    .map(|_| {
                        let value = [0, 1, u64::MAX][digits % 3];
                        digits /= 3;
                        value
                    })
                    .collect();
                let stored = StoredMarking::new(&original);
                let mut restored = vec![u64::MAX; n];
                stored.write_to(&mut restored);
                assert_eq!(restored, original);
                assert_eq!(stored, StoredMarking::new(&restored));
                assert!(encodings.insert(stored));
            }
        }
    }

    #[test]
    fn projection_positions_and_sparse_size_are_exact() {
        let mut m = vec![0; 10_000];
        m[17] = u64::MAX;
        match StoredMarking::new(&m) {
            StoredMarking::Sparse(values) => assert_eq!(&*values, &[(17, u64::MAX)]),
            _ => panic!("expected sparse encoding"),
        }
        let projected = StoredMarking::project(&m, &[2, 17, 5]);
        let mut restored = vec![0; 3];
        projected.write_to(&mut restored);
        assert_eq!(restored, vec![0, u64::MAX, 0]);
        assert!(matches!(
            StoredMarking::new(&[1, 0]),
            StoredMarking::Dense(_)
        ));
    }
}
