# PharmaGuard Claims Matrix

Last updated: 2026-02-20  
Purpose: keep demo/README/judge answers scientifically defensible and aligned with implementation.

## Claim Boundaries

| Claim | Evidence strength | Allowed wording | Avoid wording |
|---|---|---|---|
| PharmGKB evidence tiers inform confidence | High (PharmGKB framework papers) | "Confidence uses PharmGKB evidence tiers as a primary component." | "Our confidence is fully clinically validated." |
| Current confidence weights (evidence/genotype/phenotype/rule) | Medium (design + calibration tooling) | "Weights are evidence-informed initial priors and are post-hoc calibrated." | "These exact weights are directly derived from one paper." |
| CPIC rule coverage matters for actionability | Medium-high | "Rule coverage is explicitly modeled; unmatched combinations are penalized." | "Rule absence proves no clinical utility." |
| Traffic-light UI improves interpretability | Medium | "Color coding follows established PGx CDS conventions." | "Our specific UI causes 26x better outcomes." |
| Phenoconversion is clinically important | High | "The system applies inhibitor-aware phenotype adjustment rules for CYP2D6/CYP2C19/CYP2C9." | "We solved phenoconversion consensus globally." |
| EHR PGx tooling gaps exist | High | "Literature reports limited integrated PGx decision support in routine EHR workflows." | "All EHR systems cannot do PGx." |
| PREPARE showed ADR reduction with PGx-guided prescribing | High | "PREPARE reported lower clinically relevant ADRs in trial conditions." | "Our app will prevent exactly 30,000 deaths/year." |

## Implemented Phenoconversion Logic (Code-Truth)

Source of truth: `backend/pipeline/phenoconversion_detector.py`

- Supported genes: `CYP2D6`, `CYP2C19`, `CYP2C9`
- Input: genetic phenotype (`PM/IM/NM/RM/URM`) + concurrent meds
- Output: functional phenotype shift + confidence penalty

Current downgrade table:

- `strong`: `URM->NM`, `RM->IM`, `NM->IM`, `IM->PM`, `PM->PM`
- `moderate`: `URM->RM`, `RM->NM`, `NM->NM`, `IM->IM`, `PM->PM`
- `weak`: unchanged

Use this table in demos/docs. Do not claim "strong inhibitor always -> PM" because that is not current code behavior.

## Confidence Model Positioning

- Formula in production:
  - `score = w_e*evidence + w_g*genotype + w_p*phenotype + w_r*rule_coverage`
- Weights are configured in `backend/data/clinical_rules/rules.v1.json`
- Calibration:
  - runtime calibrator in `backend/pipeline/confidence_calibrator.py`
  - audit script in `backend/scripts/evaluate_confidence_calibration.py` (ECE/Brier)

Allowed statement:
- "Confidence is component-based, evidence-informed, and calibration-aware."

## Safe Impact Statement

Use:
- "Randomized PGx studies (e.g., PREPARE) report reduced clinically relevant ADRs under trial conditions."
- "Expected real-world impact depends on adoption, adherence, and workflow integration."

Avoid:
- deterministic population extrapolations (for example exact deaths prevented per year).

## Citation Hygiene Checklist

- Every clinical claim should include at least one PMID/DOI in docs or evidence trace.
- No placeholder references in user-facing output.
- If a PharmGKB row is sparse, prefer curated CPIC citation mapping.
- Keep citation fields consistent: `authors`, `year`, `pmid/doi`, `guideline`.
