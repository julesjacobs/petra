use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{fs, path::Path};
use vass_reach::{model::Problem, pnml};

fn equal(left: &Problem, right: &Problem) -> bool {
    left.places == right.places
        && left.initial == right.initial
        && left.transitions.len() == right.transitions.len()
        && left
            .transitions
            .iter()
            .zip(&right.transitions)
            .all(|(a, b)| a.name == b.name && a.pre == b.pre && a.post == b.post)
        && left.target.len() == right.target.len()
        && left.target.iter().zip(&right.target).all(|(a, b)| {
            a.coefficients == b.coefficients && a.bound == b.bound && a.equality == b.equality
        })
}

fn main() -> Result<()> {
    let arguments: Vec<_> = std::env::args().collect();
    ensure!(
        arguments.len() == 3,
        "usage: check_original_import CORPUS QUERY"
    );
    let corpus = Path::new(&arguments[1]);
    let manifest: Value = serde_json::from_slice(&fs::read(corpus.join("manifest.json"))?)?;
    let matching: Vec<_> = manifest["queries"]
        .as_array()
        .context("queries")?
        .iter()
        .filter(|q| q["name"].as_str() == Some(&arguments[2]))
        .collect();
    ensure!(matching.len() == 1, "query identity must be unique");
    let query = matching[0];
    ensure!(query["status"] == "imported", "query unavailable");
    let mut parsed = pnml::parse(
        &fs::read_to_string(corpus.join(query["pnml"].as_str().context("pnml")?))?,
        &fs::read_to_string(corpus.join(query["xml"].as_str().context("xml")?))?,
        query["property_id"].as_str().context("property id")?,
    )?;
    ensure!(
        serde_json::to_value(parsed.kind)? == query["kind"],
        "property polarity differs"
    );
    ensure!(
        parsed.property_id == query["property_id"].as_str().context("property id")?,
        "property identity differs"
    );
    let branches = query["branches"].as_array().context("branches")?;
    ensure!(
        branches.len() == parsed.targets.len(),
        "branch count differs"
    );
    for (index, (target, branch)) in parsed.targets.into_iter().zip(branches).enumerate() {
        let canonical: Problem = serde_json::from_slice(&fs::read(
            corpus.join(branch["path"].as_str().context("branch path")?),
        )?)?;
        canonical.validate()?;
        parsed.net.target = target;
        ensure!(
            equal(&parsed.net, &canonical),
            "canonical branch {index} differs from Rust original-input parser"
        );
    }
    println!(
        "{}",
        json!({"status":"matched", "query":arguments[2],
        "property_id":parsed.property_id, "kind":parsed.kind, "branches":branches.len()})
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn comparison_checks_marking_arcs_and_every_target_row() {
        let original: Problem = serde_json::from_value(json!({
            "places":["p"], "initial":[2],
            "transitions":[{"name":"t","pre":[[0,2]],"post":[[0,3]]}],
            "target":[{"coefficients":[-1],"bound":-4,"equality":false}]
        }))
        .unwrap();
        assert!(equal(&original, &original));
        let value = serde_json::to_value(&original).unwrap();
        for (pointer, replacement) in [
            ("/initial/0", json!(1)),
            ("/places/0", json!("q")),
            ("/transitions/0/pre/0/1", json!(1)),
            ("/transitions/0/post/0/1", json!(2)),
            ("/transitions/0/name", json!("u")),
            ("/target/0/bound", json!(-3)),
            ("/target/0/coefficients/0", json!(1)),
            ("/target/0/equality", json!(true)),
            ("/target", json!([])),
            ("/transitions", json!([])),
        ] {
            let mut changed = value.clone();
            *changed.pointer_mut(pointer).unwrap() = replacement;
            assert!(
                !equal(&original, &serde_json::from_value(changed).unwrap()),
                "{pointer}"
            );
        }
    }
}
