# PharmaGuard Research Evidence Log

Last updated: 2026-02-20  
Scope: paper-backed justifications for model components and UI decisions, with conservative claim language.

## Core Evidence Mapping

| Paper | Supports | Notes for use |
|---|---|---|
| Whirl-Carrillo et al., 2021 (PMC8457105) | PharmGKB evidence hierarchy in confidence component | Supports evidence tier ordering; does not by itself validate exact numeric weights. |
| Whirl-Carrillo et al., 2012 (PMC3660037) | Curated LOE definitions and confidence concept | Use to justify graduated evidence confidence, not absolute probabilities. |
| Kidwai-Khan et al., 2022 (DOI:10.3389/fdata.2022.1059088) | Rule-actionability framing | Supports importance of actionable guideline mapping. |
| O'Donnell et al., 2017 (PMC5636653) | Traffic-light CDS patterns | Supports clinician-friendly risk signaling conventions. |
| JMIR Med Inform, 2024 (DOI:10.2196/49230) | Need for transparent, linked evidence in CDS | Directly supports `/evidence-trace` style design. |
| Cicali et al., 2021 (PMID:34231197) | Phenoconversion relevance and inhibitor-aware PGx interpretation | Supports adding inhibitor context; implementation should match code truth table. |
| Nahid & Johnson, 2023 (PMC9891304) | Clinical gap in EHR-integrated phenoconversion support | Supports problem framing. |
| Wake et al., 2021 (PMC9291515, PMID:34365648) | Clinician confidence gap in PGx interpretation | Supports need for decision support UX. |
| PREPARE RCT (Lancet 2023, cited in JMIR 2024) | PGx-guided prescribing improves ADR outcomes in trial context | Avoid direct deterministic population extrapolation claims. |

## Formula Positioning

Current confidence architecture:

`score = w_e * evidence + w_g * genotype + w_p * phenotype + w_r * rule_coverage`

- `evidence` component: PharmGKB evidence-level mapped.
- `genotype` component: VCF quality + annotation completeness + gene support.
- `phenotype` component: phenotype certainty map.
- `rule_coverage` component: matched rule vs fallback behavior.

Important wording:
- "Evidence-informed and calibrated"
- Not: "directly proven exact weights from literature"

## Phenoconversion Positioning

Implemented behavior is rule-table based in:
- `backend/pipeline/phenoconversion_detector.py`

Demo phrasing:
- "Concurrent inhibitors can shift functional phenotype, and PharmaGuard applies gene-specific downgrade rules before risk mapping."

Avoid:
- claiming universal consensus phenoconversion algorithm
- claiming strong inhibitor always forces PM unless code does so

## Impact Wording (Judge-safe)

Recommended:
- "Trial data suggests PGx-guided prescribing can reduce clinically relevant ADRs; actual deployment impact depends on adoption and workflow."

Not recommended:
- "This app will prevent exactly X deaths/year."
