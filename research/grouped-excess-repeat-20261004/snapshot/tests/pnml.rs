use serde_json::Value;
use std::{fs, path::Path};
use vass_reach::model;

#[path = "../src/pnml.rs"]
mod pnml;

fn net(body: &str) -> String {
    format!(
        "<pnml><net id='net' type='http://www.pnml.org/version-2009/grammar/ptnet'><page id='page'>{body}</page></net></pnml>"
    )
}
fn property(predicate: &str, invariant: bool) -> String {
    let (quantifier, temporal) = if invariant {
        ("all-paths", "globally")
    } else {
        ("exists-path", "finally")
    };
    format!(
        "<property-set><property><id>query</id><formula><{quantifier}><{temporal}>{predicate}</{temporal}></{quantifier}></formula></property></property-set>"
    )
}
fn constant(value: &str) -> String {
    format!("<integer-constant>{value}</integer-constant>")
}
fn count(places: &[&str]) -> String {
    format!(
        "<tokens-count>{}</tokens-count>",
        places
            .iter()
            .map(|p| format!("<place>{p}</place>"))
            .collect::<String>()
    )
}
fn le(left: &str, right: &str) -> String {
    format!("<integer-le>{left}{right}</integer-le>")
}
fn reject(xml: &str, predicate: &str) {
    assert!(pnml::parse(xml, &property(predicate, false), "query").is_err());
}
fn targets(query: &pnml::ParsedQuery) -> Value {
    serde_json::to_value(&query.targets).unwrap()
}

#[test]
fn weighted_duplicate_arcs_nested_pages_namespaces_and_source_order() {
    let xml = net("<place id='second'><name><text>display-name</text></name><initialMarking><text>7</text></initialMarking></place>
        <transition id='move'/><page id='inner'><place id='first'/>
        <arc id='a1' source='second' target='move'><inscription><text>2</text></inscription></arc>
        <arc id='a2' source='second' target='move'><inscription><text>3</text></inscription></arc>
        <arc id='a3' source='move' target='first'/></page>
        <toolspecific tool='nupn'><structure><place id='ignored'/></structure></toolspecific>
        <toolspecific tool='Tina'><size/><color/></toolspecific>")
        .replace("<pnml>", "<pnml xmlns='http://www.pnml.org/version-2009/grammar/pnml'>");
    let prop = property(&le(&constant("1"), &count(&["first"])), false).replace(
        "<property-set>",
        "<property-set xmlns='http://mcc.lip6.fr/'>",
    );
    let result = pnml::parse(&xml, &prop, "query").unwrap();
    assert_eq!(result.property_id, "query");
    assert_eq!(result.kind, pnml::PropertyKind::EF);
    assert_eq!(result.net.places, ["second", "first"]);
    assert_eq!(result.net.initial, [7, 0]);
    assert!(result.net.target.is_empty());
    assert_eq!(result.net.transitions[0].name, "move");
    assert_eq!(result.net.transitions[0].pre, [(0, 5)]);
    assert_eq!(result.net.transitions[0].post, [(1, 1)]);
    assert_eq!(
        targets(&result),
        serde_json::json!([[{"coefficients":[0,1],"bound":1,"equality":false}]])
    );
}

#[test]
fn leaf_text_concatenates_comments_and_processing_instructions() {
    for separator in ["<!-- comment -->", "<?annotation ignored?>"] {
        for leading in ["", separator] {
            let number = format!("{leading} 1{separator}2 ");
            let place = format!("{leading} p{separator}12 ");
            let id = format!("{leading}que{separator}ry");
            let xml = net(&format!(
                "<place id='p12'><initialMarking><text>{number}</text></initialMarking></place>
                <transition id='t'/><arc source='p12' target='t'><inscription><text>{number}</text></inscription></arc>"
            ));
            let prop = property(&le(&constant(&number), &count(&[&place])), false)
                .replace("<id>query</id>", &format!("<id>{id}</id>"));
            let parsed = pnml::parse(&xml, &prop, "query").unwrap();
            assert_eq!(parsed.property_id, "query");
            assert_eq!(parsed.net.initial, [12]);
            assert_eq!(parsed.net.transitions[0].pre, [(0, 12)]);
            assert_eq!(
                targets(&parsed),
                serde_json::json!([[{"coefficients":[1],"bound":12,"equality":false}]])
            );
            assert!(pnml::parse(&xml, &prop, "que").is_err());
        }
    }
}

#[test]
fn split_marking_preserves_initial_target_witness() {
    let xml = net(
        "<place id='p'><initialMarking><text>1<!-- comment -->2</text></initialMarking></place>",
    );
    let prop = property(&le(&constant("10"), &count(&["p"])), false);
    let mut parsed = pnml::parse(&xml, &prop, "query").unwrap();
    parsed.net.target = parsed.targets.pop().unwrap();
    assert_eq!(parsed.net.check_witness(&[]).unwrap(), [12]);
}

#[test]
fn leaf_text_rejects_elements_and_preserves_exact_property_id_whitespace() {
    let xml = net("<place id='p'/>");
    for leaf in ["<element/>", "1<element/>2"] {
        reject(
            &net(&format!(
                "<place id='p'><initialMarking><text>{leaf}</text></initialMarking></place>"
            )),
            "<true/>",
        );
        reject(
            &net(&format!(
                "<place id='p'/><transition id='t'/><arc source='p' target='t'><inscription><text>{leaf}</text></inscription></arc>"
            )),
            "<true/>",
        );
        reject(&xml, &le(&constant(leaf), &count(&["p"])));
        reject(&xml, &le(&constant("0"), &count(&[leaf])));
        let prop =
            property("<true/>", false).replace("<id>query</id>", &format!("<id>query{leaf}</id>"));
        assert!(pnml::parse(&xml, &prop, "query").is_err());
    }
    let prop =
        property("<true/>", false).replace("<id>query</id>", "<id> que<!-- comment -->ry </id>");
    assert!(pnml::parse(&xml, &prop, "query").is_err());
    assert!(pnml::parse(&xml, &prop, " query ").is_ok());
}

#[test]
fn ag_counterexample_and_nested_negation_preserve_mixed_signs() {
    let xml = net("<place id='p'/><place id='q'/>");
    let relation = le(&count(&["p"]), &count(&["q"]));
    let ag = pnml::parse(&xml, &property(&relation, true), "query").unwrap();
    assert_eq!(ag.kind, pnml::PropertyKind::AG);
    assert_eq!(
        targets(&ag),
        serde_json::json!([[{"coefficients":[1,-1],"bound":1,"equality":false}]])
    );
    let nested = format!("<negation>{relation}</negation>");
    let restored = pnml::parse(&xml, &property(&nested, true), "query").unwrap();
    assert_eq!(
        targets(&restored),
        serde_json::json!([[{"coefficients":[-1,1],"bound":0,"equality":false}]])
    );
    let predicate =
        format!("<conjunction>{relation}<disjunction><true/><false/></disjunction></conjunction>");
    assert_eq!(
        pnml::parse(&xml, &property(&predicate, true), "query")
            .unwrap()
            .targets
            .len(),
        1
    );
}

#[test]
fn exact_big_integer_cancellation_precedes_i64_conversion() {
    let xml = net("<place id='p'/><place id='q'/>");
    let huge = "99999999999999999999999999999999999999999999999999999999999999999";
    let left = format!(
        "<integer-sum>{}{}{}</integer-sum>",
        constant(huge),
        count(&["p", "p"]),
        constant("-2")
    );
    let right = format!(
        "<integer-add>{}{}</integer-add>",
        constant(huge),
        count(&["q"])
    );
    let result = pnml::parse(&xml, &property(&le(&left, &right), false), "query").unwrap();
    assert_eq!(
        targets(&result),
        serde_json::json!([[{"coefficients":[-2,1],"bound":-2,"equality":false}]])
    );
    reject(&xml, &le(&constant(huge), &constant("0")));
    let minimum = le(&constant("-9223372036854775808"), &constant("0"));
    assert!(pnml::parse(&xml, &property(&minimum, false), "query").is_ok());
    let over = le(&constant("0"), &constant("9223372036854775807"));
    assert!(pnml::parse(&xml, &property(&over, true), "query").is_err());
}

#[test]
fn dnf_order_limits_and_empty_boolean_operators() {
    let xml = net("<place id='p'/>");
    let a = le(&constant("1"), &count(&["p"]));
    let b = le(&constant("2"), &count(&["p"]));
    let c = le(&constant("3"), &count(&["p"]));
    let predicate = format!("<conjunction><disjunction>{a}{b}</disjunction>{c}</conjunction>");
    let parsed = pnml::parse(&xml, &property(&predicate, false), "query").unwrap();
    assert_eq!(
        parsed
            .targets
            .iter()
            .map(|branch| branch.iter().map(|c| c.bound).collect::<Vec<_>>())
            .collect::<Vec<_>>(),
        [vec![1, 3], vec![2, 3]]
    );
    for (predicate, branches) in [
        ("<true/>", 1),
        ("<false/>", 0),
        ("<conjunction/>", 1),
        ("<disjunction/>", 0),
    ] {
        assert_eq!(
            pnml::parse(&xml, &property(predicate, false), "query")
                .unwrap()
                .targets
                .len(),
            branches
        );
    }
    let at_limit = format!("<disjunction>{}</disjunction>", "<true/>".repeat(1024));
    assert_eq!(
        pnml::parse(&xml, &property(&at_limit, false), "query")
            .unwrap()
            .targets
            .len(),
        1024
    );
    let over_limit = format!(
        "<conjunction><disjunction>{}</disjunction><disjunction><true/><true/></disjunction></conjunction>",
        "<true/>".repeat(513)
    );
    reject(&xml, &over_limit);
}

#[test]
fn property_selection_is_exact_and_unique() {
    let xml = net("<place id='p'/>");
    let selected = "<property><id>query</id><formula><exists-path><finally><true/></finally></exists-path></formula></property>";
    let document = format!(
        "<property-set><property><id>other</id><formula><unsupported/></formula></property>{selected}</property-set>"
    );
    assert!(pnml::parse(&xml, &document, "query").is_ok());
    assert!(pnml::parse(&xml, &document, "quer").is_err());
    assert!(
        pnml::parse(
            &xml,
            &format!("<property-set>{selected}{selected}</property-set>"),
            "query"
        )
        .is_err()
    );
    assert!(
        pnml::parse(
            &xml,
            &property("<true/>", false)
                .replace("<finally>", "<globally>")
                .replace("</finally>", "</globally>"),
            "query"
        )
        .is_err()
    );
}

#[test]
fn malformed_and_unsupported_nets_fail_explicitly() {
    let bodies = [
        "<place id='p'/><place id='p'/>",
        "<place id='p'/><transition id='p'/>",
        "<place/>",
        "<place id='p'/><transition id='t'/><arc source='p' target='missing'/>",
        "<place id='p'/><place id='q'/><arc source='p' target='q'/>",
        "<place id='p'/><transition id='t'/><arc source='p' target='t' type='inhibitor'/>",
        "<place id='p'/><transition id='t'/><arc source='p' target='t'><type><text>reset</text></type></arc>",
        "<place id='p'><capacity><text>1</text></capacity></place>",
        "<toolspecific tool='other'><size/></toolspecific>",
        "<toolspecific tool='Tina'><inhibitor/></toolspecific>",
        "<place id='p' unsupported='yes'/>",
        "<place id='p'><initialMarking><text>1</text><text>2</text></initialMarking></place>",
        "<place id='p'><initialMarking><text>1</text></initialMarking><initialMarking><text>2</text></initialMarking></place>",
    ];
    for body in bodies {
        reject(&net(body), "<true/>");
    }
    reject(&net("").replace("/ptnet", "/symmetricnet"), "<true/>");
    reject(
        "<pnml><net type='x/ptnet'/><net type='x/ptnet'/></pnml>",
        "<true/>",
    );
    reject("<pnml>", "<true/>");
}

#[test]
fn u64_numbers_and_arc_accumulation_are_checked() {
    for number in ["-1", "18446744073709551616", "not-a-number"] {
        reject(
            &net(&format!(
                "<place id='p'><initialMarking><text>{number}</text></initialMarking></place>"
            )),
            "<true/>",
        );
    }
    let base = "<place id='p'/><transition id='t'/>";
    let arc = |weight| {
        format!("<arc source='p' target='t'><inscription><text>{weight}</text></inscription></arc>")
    };
    reject(&net(&format!("{base}{}", arc("0"))), "<true/>");
    reject(
        &net(&format!(
            "{base}{}{}",
            arc("18446744073709551615"),
            arc("1")
        )),
        "<true/>",
    );
    let parsed = pnml::parse(
        &net(&format!("{base}{}", arc("18446744073709551615"))),
        &property("<true/>", false),
        "query",
    )
    .unwrap();
    assert_eq!(parsed.net.transitions[0].pre, [(0, u64::MAX)]);
}

#[test]
fn unsupported_predicates_and_expressions_are_rejected() {
    let xml = net("<place id='p'/>");
    for predicate in [
        "<is-fireable><transition>t</transition></is-fireable>",
        "<integer-le/>",
        "<negation/>",
        "<negation><true/><false/></negation>",
        "<true><false/></true>",
    ] {
        reject(&xml, predicate);
    }
    for expression in [
        "<tokens-count/>",
        "<tokens-count><place>unknown</place></tokens-count>",
        "<integer-product><integer-constant>2</integer-constant></integer-product>",
        "<integer-constant><integer-constant>1</integer-constant></integer-constant>",
    ] {
        reject(&xml, &le(expression, &constant("0")));
    }
    let deeply_nested = format!(
        "{}<true/>{}",
        "<negation>".repeat(300),
        "</negation>".repeat(300)
    );
    reject(&xml, &deeply_nested);
}

#[test]
fn development_original_inputs_equal_frozen_canonical_branches() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let corpus = root.join("benchmarks/mcc-publication-development");
    let manifest: Value =
        serde_json::from_str(&fs::read_to_string(corpus.join("manifest.json")).unwrap()).unwrap();
    for query in manifest["queries"].as_array().unwrap() {
        if query["status"] != "imported" {
            continue;
        }
        let net_xml = fs::read_to_string(corpus.join(query["pnml"].as_str().unwrap())).unwrap();
        let property_xml = fs::read_to_string(corpus.join(query["xml"].as_str().unwrap())).unwrap();
        let parsed = pnml::parse(
            &net_xml,
            &property_xml,
            query["property_id"].as_str().unwrap(),
        )
        .unwrap_or_else(|e| panic!("{}: {e:#}", query["name"]));
        assert_eq!(serde_json::to_value(parsed.kind).unwrap(), query["kind"]);
        let branches = query["branches"].as_array().unwrap();
        assert_eq!(parsed.targets.len(), branches.len(), "{}", query["name"]);
        for (target, branch) in parsed.targets.iter().zip(branches) {
            let expected: Value = serde_json::from_str(
                &fs::read_to_string(corpus.join(branch["path"].as_str().unwrap())).unwrap(),
            )
            .unwrap();
            let mut problem = parsed.net.clone();
            problem.target = target.clone();
            assert_eq!(
                serde_json::to_value(problem).unwrap(),
                expected,
                "{}",
                branch["path"]
            );
        }
    }
}
