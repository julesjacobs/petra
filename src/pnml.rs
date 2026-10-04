//! Ordinary weighted PNML and MCC EF/AG reachability queries.
//!
//! AG properties are translated to existential counterexample targets. Arithmetic
//! is exact until final coefficients/bounds are checked against the solver's i64
//! interface. Unsupported constructs fail explicitly; no net reduction occurs.
use crate::model::{Constraint, Problem, Transition};
use anyhow::{Context, Result, bail, ensure};
use num_bigint::BigInt;
use num_traits::{ToPrimitive, Zero};
use roxmltree::{Document, Node};
use serde::Serialize;
use std::collections::{BTreeMap, HashMap, HashSet};

const BRANCH_LIMIT: usize = 1024;
const EXPRESSION_DEPTH_LIMIT: usize = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum PropertyKind {
    EF,
    AG,
}

#[derive(Clone, Debug)]
pub struct ParsedQuery {
    pub net: Problem,
    pub property_id: String,
    pub kind: PropertyKind,
    pub targets: Vec<Vec<Constraint>>,
}

fn children<'a, 'input>(node: Node<'a, 'input>) -> impl Iterator<Item = Node<'a, 'input>> {
    node.children().filter(Node::is_element)
}

fn leaf_text(node: Node<'_, '_>) -> Result<String> {
    ensure!(
        children(node).next().is_none(),
        "unexpected element in {}",
        node.tag_name().name()
    );
    Ok(node
        .children()
        .filter(Node::is_text)
        .filter_map(|child| child.text())
        .collect())
}

fn only<'a, 'input>(node: Node<'a, 'input>) -> Result<Node<'a, 'input>> {
    let mut elements = children(node);
    let child = elements.next().context("expected one element child")?;
    ensure!(
        elements.next().is_none(),
        "expected one child in {}",
        node.tag_name().name()
    );
    Ok(child)
}

fn named_child<'a, 'input>(node: Node<'a, 'input>, name: &str) -> Result<Option<Node<'a, 'input>>> {
    let mut matching = children(node).filter(|child| child.tag_name().name() == name);
    let child = matching.next();
    ensure!(matching.next().is_none(), "duplicate {name}");
    Ok(child)
}

fn required_attribute<'a, 'input>(node: Node<'a, 'input>, name: &str) -> Result<&'a str> {
    node.attribute(name)
        .with_context(|| format!("missing {name} on {}", node.tag_name().name()))
}

fn ignored_metadata(node: Node<'_, '_>) -> bool {
    node.tag_name().name() == "toolspecific"
        && (node.attribute("tool") == Some("nupn")
            || (node.attribute("tool") == Some("Tina")
                && children(node).all(|child| {
                    matches!(child.tag_name().name(), "size" | "color")
                        && children(child).next().is_none()
                })))
}

fn number(node: Node<'_, '_>, tag: &str, default: u64) -> Result<u64> {
    let Some(container) = named_child(node, tag)? else {
        return Ok(default);
    };
    ensure!(
        children(container)
            .filter(|child| !ignored_metadata(*child))
            .all(|child| { matches!(child.tag_name().name(), "text" | "graphics") }),
        "expected text in {tag}"
    );
    let text = named_child(container, "text")?.with_context(|| format!("missing text in {tag}"))?;
    let value: BigInt = leaf_text(text)?
        .trim()
        .parse()
        .with_context(|| format!("invalid integer in {tag}"))?;
    value
        .to_u64()
        .with_context(|| format!("{tag} outside u64 range"))
}

fn parse_net(xml: &str) -> Result<Problem> {
    let document = Document::parse(xml).context("invalid PNML XML")?;
    let root = document.root_element();
    ensure!(root.tag_name().name() == "pnml", "expected PNML root");
    let net = named_child(root, "net")?.context("expected one PNML net")?;
    ensure!(
        net.attribute("type")
            .is_some_and(|kind| kind.ends_with("/ptnet")),
        "only ordinary P/T nets are supported"
    );
    let mut pending = vec![net];
    let mut places = Vec::new();
    let mut transitions = Vec::new();
    let mut arcs = Vec::new();
    let mut identifiers = HashSet::new();
    while let Some(node) = pending.pop() {
        let tag = node.tag_name().name();
        let allowed: &[&str] = match tag {
            "net" => &["name", "page"],
            "page" => &["name", "page", "place", "transition", "arc", "graphics"],
            "place" => &["name", "initialMarking", "graphics"],
            "transition" => &["name", "graphics"],
            "arc" => &["name", "inscription", "graphics"],
            _ => unreachable!(),
        };
        ensure!(
            node.attributes()
                .all(|attribute| attribute.namespace().is_none()
                    && matches!(attribute.name(), "id" | "type" | "source" | "target")),
            "unsupported PNML attributes on {tag}"
        );
        if let Some(id) = node.attribute("id") {
            ensure!(identifiers.insert(id), "duplicate PNML ID {id}");
        }
        match tag {
            "place" => {
                required_attribute(node, "id")?;
                places.push(node);
            }
            "transition" => {
                required_attribute(node, "id")?;
                transitions.push(node);
            }
            "arc" => {
                ensure!(
                    node.attribute("type").is_none(),
                    "typed arcs are unsupported"
                );
                arcs.push(node);
            }
            _ => {}
        }
        let mut nested = Vec::new();
        for child in children(node) {
            if ignored_metadata(child) {
                continue;
            }
            let child_tag = child.tag_name().name();
            ensure!(
                allowed.contains(&child_tag),
                "unsupported {tag} extension: {child_tag}"
            );
            if matches!(child_tag, "page" | "place" | "transition" | "arc") {
                nested.push(child);
            }
        }
        pending.extend(nested.into_iter().rev());
    }
    let place_ids: HashMap<_, _> = places
        .iter()
        .enumerate()
        .map(|(i, p)| (p.attribute("id").unwrap(), i))
        .collect();
    let transition_ids: HashMap<_, _> = transitions
        .iter()
        .enumerate()
        .map(|(i, t)| (t.attribute("id").unwrap(), i))
        .collect();
    let mut weights =
        vec![(BTreeMap::<usize, u64>::new(), BTreeMap::<usize, u64>::new()); transitions.len()];
    for arc in arcs {
        let source = required_attribute(arc, "source")?;
        let target = required_attribute(arc, "target")?;
        let weight = number(arc, "inscription", 1)?;
        ensure!(weight > 0, "arc weight must be positive");
        let (bucket, place) = if let (Some(&p), Some(&t)) =
            (place_ids.get(source), transition_ids.get(target))
        {
            (&mut weights[t].0, p)
        } else if let (Some(&t), Some(&p)) = (transition_ids.get(source), place_ids.get(target)) {
            (&mut weights[t].1, p)
        } else {
            bail!("non-bipartite or unknown arc endpoints: {source}, {target}");
        };
        let total = bucket.entry(place).or_default();
        *total = total.checked_add(weight).context("arc weight overflow")?;
    }
    let problem = Problem {
        places: places
            .iter()
            .map(|p| p.attribute("id").unwrap().to_owned())
            .collect(),
        initial: places
            .iter()
            .map(|p| number(*p, "initialMarking", 0))
            .collect::<Result<_>>()?,
        transitions: transitions
            .iter()
            .zip(weights)
            .map(|(t, (pre, post))| Transition {
                name: t.attribute("id").unwrap().to_owned(),
                pre: pre.into_iter().collect(),
                post: post.into_iter().collect(),
            })
            .collect(),
        target: Vec::new(),
    };
    problem.validate()?;
    Ok(problem)
}

#[derive(Default)]
struct Expression {
    terms: BTreeMap<usize, BigInt>,
    constant: BigInt,
}

fn expression(node: Node<'_, '_>, ids: &HashMap<&str, usize>, depth: usize) -> Result<Expression> {
    ensure!(
        depth <= EXPRESSION_DEPTH_LIMIT,
        "integer expression nesting limit"
    );
    let mut result = Expression::default();
    match node.tag_name().name() {
        "integer-constant" => {
            result.constant = leaf_text(node)?
                .trim()
                .parse()
                .context("invalid integer constant")?;
        }
        "tokens-count" => {
            ensure!(children(node).next().is_some(), "empty tokens-count");
            for place in children(node) {
                ensure!(place.tag_name().name() == "place", "malformed tokens-count");
                let text = leaf_text(place)?;
                let name = text.trim();
                let &id = ids
                    .get(name)
                    .with_context(|| format!("unknown target place {name}"))?;
                *result.terms.entry(id).or_default() += 1;
            }
        }
        "integer-sum" | "integer-add" => {
            for child in children(node) {
                let part = expression(child, ids, depth + 1)?;
                result.constant += part.constant;
                for (place, coefficient) in part.terms {
                    *result.terms.entry(place).or_default() += coefficient;
                }
            }
        }
        tag => bail!("unsupported integer expression: {tag}"),
    }
    Ok(result)
}

fn dnf(
    node: Node<'_, '_>,
    ids: &HashMap<&str, usize>,
    negate: bool,
    depth: usize,
) -> Result<Vec<Vec<Constraint>>> {
    ensure!(
        depth <= EXPRESSION_DEPTH_LIMIT,
        "Boolean expression nesting limit"
    );
    let tag = node.tag_name().name();
    match tag {
        "negation" => dnf(only(node)?, ids, !negate, depth + 1),
        "true" | "false" => {
            ensure!(
                children(node).next().is_none(),
                "malformed Boolean constant"
            );
            Ok(if (tag == "true") != negate {
                vec![vec![]]
            } else {
                vec![]
            })
        }
        "conjunction" | "disjunction" => {
            let conjunction = (tag == "conjunction") != negate;
            let mut result = if conjunction { vec![vec![]] } else { vec![] };
            for child in children(node) {
                let terms = dnf(child, ids, negate, depth + 1)?;
                let size = if conjunction {
                    result.len().checked_mul(terms.len())
                } else {
                    result.len().checked_add(terms.len())
                };
                ensure!(
                    size.is_some_and(|size| size <= BRANCH_LIMIT),
                    "Boolean target exceeds branch limit"
                );
                if conjunction {
                    let mut product = Vec::with_capacity(size.unwrap());
                    for left in &result {
                        for right in &terms {
                            let mut branch = left.clone();
                            branch.extend(right.iter().cloned());
                            product.push(branch);
                        }
                    }
                    result = product;
                } else {
                    result.extend(terms);
                }
            }
            Ok(result)
        }
        "integer-le" => {
            let operands: Vec<_> = children(node).collect();
            ensure!(operands.len() == 2, "integer-le requires two operands");
            let left = expression(operands[0], ids, 0)?;
            let right = expression(operands[1], ids, 0)?;
            let (mut positive, negative, strict) = if negate {
                (left, right, 1)
            } else {
                (right, left, 0)
            };
            for (place, coefficient) in negative.terms {
                *positive.terms.entry(place).or_default() -= coefficient;
            }
            let bound = negative.constant - positive.constant + BigInt::from(strict);
            let mut coefficients = vec![0; ids.len()];
            for (place, coefficient) in positive.terms {
                if !coefficient.is_zero() {
                    coefficients[place] = coefficient
                        .to_i64()
                        .context("target coefficient exceeds i64 range")?;
                }
            }
            Ok(vec![vec![Constraint {
                coefficients,
                bound: bound.to_i64().context("target bound exceeds i64 range")?,
                equality: false,
            }]])
        }
        _ => bail!("unsupported predicate: {tag}"),
    }
}

/// Parse one exact property ID; targets denote EF reachability or AG violations.
/// The net retains source identifiers/order and has an empty target.
/// DNF expansion is capped at 1024 branches and expressions at 256 nesting levels.
pub fn parse(net_xml: &str, property_xml: &str, property_id: &str) -> Result<ParsedQuery> {
    let net = parse_net(net_xml)?;
    let document = Document::parse(property_xml).context("invalid property XML")?;
    let root = document.root_element();
    ensure!(
        root.tag_name().name() == "property-set",
        "expected property-set"
    );
    let mut selected = None;
    for property in children(root).filter(|node| node.tag_name().name() == "property") {
        let id = named_child(property, "id")?.map(leaf_text).transpose()?;
        if id.as_deref() == Some(property_id) {
            ensure!(
                selected.replace(property).is_none(),
                "requested property ID must occur exactly once"
            );
        }
    }
    let property = selected.context("requested property ID must occur exactly once")?;
    let formula = only(named_child(property, "formula")?.context("missing property formula")?)?;
    let temporal = only(formula)?;
    let kind = match (formula.tag_name().name(), temporal.tag_name().name()) {
        ("exists-path", "finally") => PropertyKind::EF,
        ("all-paths", "globally") => PropertyKind::AG,
        _ => bail!("only EF and AG are supported"),
    };
    let ids = net
        .places
        .iter()
        .enumerate()
        .map(|(i, name)| (name.as_str(), i))
        .collect();
    let targets = dnf(only(temporal)?, &ids, kind == PropertyKind::AG, 0)?;
    Ok(ParsedQuery {
        net,
        property_id: property_id.to_owned(),
        kind,
        targets,
    })
}
