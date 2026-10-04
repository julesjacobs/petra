# Combined portfolio: complete development comparison

The combined portfolio solves 189/192 properties: 104 reachable, 85 unreachable,
and three unknown. Both frozen count and walk portfolios solve 186 (101 reachable,
85 unreachable); the frozen existing solver solves 183 (98 reachable,85 unreachable).

The candidate gains DoubleExponent-PT-003 RC05, RC06 and RC11 over count/walk, with
no positive or negative coverage losses. It also retains the three TokenRing gains
over the frozen existing solver. All 768 rows pass artifact audit with zero warnings
or answer disagreements. Every definitive native answer was independently checked.

This establishes the implemented combined solver's coverage in this screen, replacing
the earlier diagnostic union estimate. It does not establish stable timing or general
superiority. One second per property was shared across canonical branches; sampled
2 GiB memory limits and bounded independent checks were used. This is one shared-Mac
development repeat. Cloud/Refine original-input gains remain separate diagnostics.

Plan SHA256: f9bc9cae92da9b45ad20ebe5e3042a4ad3d264f9dcfd2d5a83be4bcf6ee2ffa4.
Frozen artifacts: results/solver-portfolio-reduced-development-v1.
Raw rows: results/portfolio-reduced-development-v1/runs.jsonl.
Paired results and resource diagnostics: audit.json and diagnostics.json here.

Next: complete the running Linux count-portfolio comparison, then qualify the combined
candidate with the extended frozen checker and matched strong competitors. Defaults
remain unchanged; held-out/repeated evidence and algorithmic novelty remain open.
