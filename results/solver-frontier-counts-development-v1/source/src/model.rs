use anyhow::{Result, bail, ensure};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Transition {
    pub name: String,
    pub pre: Vec<(usize, u64)>,
    pub post: Vec<(usize, u64)>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Constraint {
    pub coefficients: Vec<i64>,
    pub bound: i64,
    pub equality: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Problem {
    pub places: Vec<String>,
    pub initial: Vec<u64>,
    pub transitions: Vec<Transition>,
    /// Every constraint is a dot product >= bound, or == bound.
    pub target: Vec<Constraint>,
}
impl Problem {
    pub fn validate(&self) -> Result<()> {
        let n = self.places.len();
        ensure!(
            self.initial.len() == n,
            "initial marking dimension mismatch"
        );
        for t in &self.transitions {
            for arcs in [&t.pre, &t.post] {
                let mut used = std::collections::HashSet::new();
                for &(p, w) in arcs {
                    ensure!(
                        p < n && w > 0 && used.insert(p),
                        "invalid or repeated arc in {}",
                        t.name
                    );
                }
            }
        }
        for c in &self.target {
            ensure!(c.coefficients.len() == n, "constraint dimension mismatch");
        }
        Ok(())
    }
    pub fn accepts(&self, m: &[u64]) -> Result<bool> {
        for c in &self.target {
            let mut value = 0i128;
            for (&a, &x) in c.coefficients.iter().zip(m) {
                value = value
                    .checked_add(i128::from(a) * i128::from(x))
                    .ok_or_else(|| anyhow::anyhow!("target arithmetic overflow"))?;
            }
            if (c.equality && value != i128::from(c.bound))
                || (!c.equality && value < i128::from(c.bound))
            {
                return Ok(false);
            }
        }
        Ok(true)
    }
    pub fn fire(&self, m: &[u64], t: usize) -> Result<Option<Vec<u64>>> {
        let t = &self.transitions[t];
        if t.pre.iter().any(|&(p, w)| m[p] < w) {
            return Ok(None);
        }
        let mut next = m.to_vec();
        for &(p, w) in &t.pre {
            next[p] -= w;
        }
        for &(p, w) in &t.post {
            next[p] = next[p]
                .checked_add(w)
                .ok_or_else(|| anyhow::anyhow!("counter overflow"))?;
        }
        Ok(Some(next))
    }
    pub fn check_witness(&self, trace: &[usize]) -> Result<Vec<u64>> {
        let mut m = self.initial.clone();
        for &t in trace {
            ensure!(t < self.transitions.len(), "invalid transition index");
            // Independent replay using dense input/output multiplicities.
            let tr = &self.transitions[t];
            for &(p, w) in &tr.pre {
                ensure!(m[p] >= w, "disabled witness transition");
            }
            for (p, x) in m.iter_mut().enumerate() {
                let pre = tr.pre.iter().find(|&&(q, _)| p == q).map_or(0, |&(_, w)| w);
                let post = tr
                    .post
                    .iter()
                    .find(|&&(q, _)| p == q)
                    .map_or(0, |&(_, w)| w);
                *x = (*x - pre)
                    .checked_add(post)
                    .ok_or_else(|| anyhow::anyhow!("witness overflow"))?;
            }
        }
        if !self.accepts(&m)? {
            bail!("witness does not reach target");
        }
        Ok(m)
    }
}
