use crate::model::{Constraint, Problem, Transition};
use anyhow::{Context, Result, bail, ensure};
use roxmltree::Node;
use std::collections::BTreeMap;

fn intern(name: &str, places: &mut Vec<String>, ids: &mut BTreeMap<String, usize>) -> usize {
    if let Some(&p) = ids.get(name) {
        return p;
    }
    let p = places.len();
    places.push(name.into());
    ids.insert(name.into(), p);
    p
}
fn arcs(
    text: &str,
    places: &mut Vec<String>,
    ids: &mut BTreeMap<String, usize>,
) -> Result<Vec<(usize, u64)>> {
    let mut result = BTreeMap::<usize, u64>::new();
    for token in text.split_whitespace() {
        ensure!(
            !token.contains(['{', '}', '?', '!', '[', ']']),
            "unsupported TINA arc syntax: {token}"
        );
        let (name, weight) = match token.split_once('*') {
            Some((p, w)) => (p, w.parse()?),
            None => (token, 1),
        };
        ensure!(weight > 0, "zero arc weight");
        let p = intern(name, places, ids);
        let old = result.entry(p).or_default();
        *old = old.checked_add(weight).context("arc weight overflow")?;
    }
    Ok(result.into_iter().collect())
}
pub fn parse(net: &str, xml: &str) -> Result<Problem> {
    let (mut places, mut ids, mut transitions, mut initial) =
        (Vec::new(), BTreeMap::new(), Vec::new(), BTreeMap::new());
    for line in net
        .lines()
        .map(str::trim)
        .filter(|s| !s.is_empty() && !s.starts_with('#'))
    {
        if line.starts_with("net ") {
            continue;
        }
        if let Some(rest) = line.strip_prefix("pl ") {
            let fields: Vec<_> = rest.split_whitespace().collect();
            ensure!(fields.len() == 2, "expected pl NAME (TOKENS): {line}");
            let p = intern(fields[0], &mut places, &mut ids);
            let value: u64 = fields[1]
                .strip_prefix('(')
                .and_then(|s| s.strip_suffix(')'))
                .context("invalid marking")?
                .parse()?;
            ensure!(
                initial.insert(p, value).is_none(),
                "duplicate place declaration"
            );
        } else if let Some(rest) = line.strip_prefix("tr ") {
            let (name, rest) = rest
                .split_once(char::is_whitespace)
                .context("missing transition body")?;
            let (pre, post) = rest.split_once("->").context("missing transition arrow")?;
            ensure!(
                !transitions.iter().any(|t: &Transition| t.name == name),
                "duplicate transition name"
            );
            transitions.push(Transition {
                name: name.into(),
                pre: arcs(pre, &mut places, &mut ids)?,
                post: arcs(post, &mut places, &mut ids)?,
            });
        } else {
            bail!("unsupported TINA declaration: {line}");
        }
    }
    let doc = roxmltree::Document::parse(xml)?;
    let root = doc.root_element();
    ensure!(root.has_tag_name("property-set"), "expected property-set");
    let properties: Vec<_> = root.children().filter(Node::is_element).collect();
    ensure!(
        properties.len() == 1 && properties[0].has_tag_name("property"),
        "expected exactly one property"
    );
    let property = properties[0];
    let formulas: Vec<_> = property
        .children()
        .filter(|n| n.has_tag_name("formula"))
        .collect();
    ensure!(formulas.len() == 1, "expected one formula");
    let path = single(formulas[0])?;
    ensure!(
        path.has_tag_name("exists-path"),
        "only existential reachability supported"
    );
    let eventually = single(path)?;
    ensure!(eventually.has_tag_name("finally"), "expected finally");
    let mut target = Vec::new();
    parse_predicate(single(eventually)?, &ids, &mut target)?;
    let mut marking = vec![0; places.len()];
    for (p, v) in initial {
        marking[p] = v;
    }
    let problem = Problem {
        places,
        initial: marking,
        transitions,
        target,
    };
    problem.validate()?;
    Ok(problem)
}
fn single<'a, 'i>(n: Node<'a, 'i>) -> Result<Node<'a, 'i>> {
    let children: Vec<_> = n.children().filter(Node::is_element).collect();
    ensure!(
        children.len() == 1,
        "expected one child of {}",
        n.tag_name().name()
    );
    Ok(children[0])
}
fn expression(n: Node<'_, '_>, ids: &BTreeMap<String, usize>) -> Result<(Vec<i64>, i64)> {
    let mut coeff = vec![0i64; ids.len()];
    let children: Vec<_> = n.children().filter(Node::is_element).collect();
    match n.tag_name().name() {
        "integer-constant" => Ok((coeff, n.text().context("missing integer")?.trim().parse()?)),
        "tokens-count" => {
            ensure!(!children.is_empty(), "empty tokens-count");
            for child in children {
                ensure!(child.has_tag_name("place"), "invalid tokens-count child");
                let name = child.text().context("missing place name")?.trim();
                let &p = ids
                    .get(name)
                    .with_context(|| format!("unknown target place {name}"))?;
                coeff[p] = coeff[p].checked_add(1).context("coefficient overflow")?;
            }
            Ok((coeff, 0))
        }
        "integer-add" => {
            let mut constant = 0i64;
            for child in children {
                let (c, k) = expression(child, ids)?;
                for (a, b) in coeff.iter_mut().zip(c) {
                    *a = a.checked_add(b).context("coefficient overflow")?;
                }
                constant = constant.checked_add(k).context("constant overflow")?;
            }
            Ok((coeff, constant))
        }
        "integer-mul" => {
            ensure!(children.len() == 2, "multiplication must have two operands");
            let (mut a, mut k) = expression(children[0], ids)?;
            let (mut b, mut l) = expression(children[1], ids)?;
            if b.iter().any(|&x| x != 0) {
                std::mem::swap(&mut a, &mut b);
                std::mem::swap(&mut k, &mut l);
            }
            ensure!(b.iter().all(|&x| x == 0), "nonlinear target");
            for x in &mut a {
                *x = x.checked_mul(l).context("coefficient overflow")?;
            }
            Ok((a, k.checked_mul(l).context("constant overflow")?))
        }
        tag => bail!("unsupported arithmetic operator {tag}"),
    }
}
fn parse_predicate(
    n: Node<'_, '_>,
    ids: &BTreeMap<String, usize>,
    target: &mut Vec<Constraint>,
) -> Result<()> {
    let children: Vec<_> = n.children().filter(Node::is_element).collect();
    let tag = n.tag_name().name();
    match tag {
        "conjunction" => {
            for c in children {
                parse_predicate(c, ids, target)?;
            }
        }
        "integer-eq" | "integer-ge" | "integer-le" | "integer-lt" | "integer-gt" => {
            ensure!(children.len() == 2, "comparison must have two operands");
            let (mut left, mut lc) = expression(children[0], ids)?;
            let (mut right, mut rc) = expression(children[1], ids)?;
            if matches!(tag, "integer-le" | "integer-lt") {
                std::mem::swap(&mut left, &mut right);
                std::mem::swap(&mut lc, &mut rc);
            }
            for (a, b) in left.iter_mut().zip(right) {
                *a = a.checked_sub(b).context("coefficient overflow")?;
            }
            let mut bound = rc.checked_sub(lc).context("bound overflow")?;
            if matches!(tag, "integer-lt" | "integer-gt") {
                bound = bound.checked_add(1).context("bound overflow")?;
            }
            target.push(Constraint {
                coefficients: left,
                bound,
                equality: tag == "integer-eq",
            });
        }
        "true" => {}
        "false" => target.push(Constraint {
            coefficients: vec![0; ids.len()],
            bound: 1,
            equality: false,
        }),
        _ => bail!("unsupported predicate {tag}"),
    }
    Ok(())
}
