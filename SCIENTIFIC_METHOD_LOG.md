# PharmaGuard Scientific Method Log

Last updated: 2026-02-19
Owner: PharmaGuard engineering

## 1. Purpose
This file is the single source of truth for improvement work.
Every change should follow:
1. Observation
2. Hypothesis
3. Intervention (code/data change)
4. Measurement
5. Decision

## 2. Primary Outcome Metrics
- Schema compliance rate (`% responses matching strict evaluator schema`)
- Clinical rule accuracy on golden set (`% expected risk labels`)
- Pipeline robustness (`% successful analyses without fallback errors`)
- Explanation quality (`% responses with non-placeholder clinical text`)
- Latency (`p50/p95 /analyze and /analyze-strict`)

## 3. Baseline/Controls
- Control endpoint: `/analyze` (UI-compatible wrapper)
- Strict endpoint: `/analyze-strict` (evaluator-compatible output list)
- Golden VCF cases: `sample_vcf/*`
- Test command: `uv run python -m unittest discover -s tests -v`

## 4. Implemented Experiments

### EXP-001: Vertex endpoint integration reliability
- Observation: LLM step failed with 404/400 and fallback triggered.
- Hypothesis: Endpoint routing/payload schema was incorrect.
- Intervention:
  - Dedicated/shared endpoint handling in `backend/pipeline/llm_explainer.py`
  - Correct payload field `prompt` instead of `content`
  - Better error-body logging
- Measurement: LLM stage logs report successful narrative + structured output.
- Result: Fixed.
- Decision: Keep; monitor with integration logs.

### EXP-002: Placeholder explanation suppression
- Observation: UI showed `...` fields in explanation.
- Hypothesis: Model output sometimes returns placeholders/malformed structured JSON.
- Intervention:
  - Placeholder detection + field-level fallback in `backend/pipeline/llm_explainer.py`
  - Fallback to deterministic template content
- Measurement: `test_placeholder_fields_are_replaced_by_template_text` passes.
- Result: Fixed.
- Decision: Keep; extend with quality scoring later.

### EXP-003: VCF quality filtering validity
- Observation: Unknown/low quality variants could pass parser.
- Hypothesis: Quality threshold logic allowed non-informative variants.
- Intervention:
  - Strict `qual < min_qual` filter in `backend/pipeline/vcf_parser.py`
- Measurement: `test_vcf_parser_skips_low_and_unknown_quality` passes.
- Result: Fixed.
- Decision: Keep; add QUAL distribution reporting in future.

### EXP-004: Reference genotype contamination of diplotypes
- Observation: `0/0` and `*1` calls polluted detected variants/diplotypes.
- Hypothesis: Reference alleles should not be treated as actionable variant evidence.
- Intervention:
  - Reference genotype checks in `backend/pipeline/variant_extractor.py`
  - Ignore `*1` for actionable detected variants
- Measurement: `test_reference_calls_do_not_create_actionable_variants` passes.
- Result: Fixed.
- Decision: Keep.

### EXP-005: Exact schema hardening
- Observation: Schema drift risk for evaluator strict checks.
- Hypothesis: Forbidding extra fields and strict endpoint improves compliance.
- Intervention:
  - `extra="forbid"` across schema models in `backend/models/schemas.py`
  - Added `/analyze-strict` in `backend/main.py`
- Measurement:
  - `test_analyze_strict_returns_plain_result_list` passes
  - `test_analyze_strict_fails_if_any_drug_errors` passes
- Result: Fixed.
- Decision: Use `/analyze-strict` for judge-mode/testing.

### EXP-006: CPIC reference quality control
- Observation: Some references looked weak/generic from sparse TSV rows.
- Hypothesis: Curated CPIC map should override weak dynamic rows.
- Intervention:
  - Curated CPIC reference priority in `backend/pipeline/risk_engine.py`
  - Better unknown-combination guidance text
- Measurement:
  - Golden tests pass
  - Unknown path test passes (`test_unknown_combination_has_explicit_unknown_action`)
- Result: Improved.
- Decision: Keep; audit all 6 target pairs manually before submission.

## 5. Current Test Status
- Total tests: 27
- Pass: 27
- Fail: 0
- Command: `uv run python -m unittest discover -s tests -v`

## 6. Next Scientific Iterations (Prioritized)

### EXP-007 (P0): Externalize hardcoded clinical tables
- Observation: Core logic depended on hardcoded dictionaries.
- Hypothesis: Versioned JSON rules increase traceability and reduce code-coupled clinical logic.
- Intervention:
  - Added `backend/data/clinical_rules/rules.v1.json`
  - Added loader: `backend/pipeline/rules_loader.py`
  - Refactored pipeline modules to read active rules via loader
  - Added `quality_metrics.clinical_rules_version`
- Measurement:
  - Existing golden + contract suite still passes
  - Output includes rules version metadata
- Result: Implemented.
- Decision: Keep; next phase can split `rules.v1.json` into smaller domain files.

### EXP-008 (P0): Evaluator fixture conformance test
- Status: Implemented
- Observation: Real evaluator may enforce exact key set/casing.
- Hypothesis: Fixture-based snapshot tests reduce disqualification risk.
- Intervention:
  - Added strict fixture `backend/tests/fixtures/analyze_strict_codeine_pm.json`
  - Added deep-equality snapshot test with timestamp normalization in `backend/tests/test_api_analyze.py`
- Measurement:
  - Snapshot test passes in CI/local test run
- Result: Implemented.
- Decision: Keep and expand fixtures for all sample VCF scenarios.

### EXP-009 (P1): Confidence calibration
- Status: Implemented (Evaluation Tooling)
- Observation: Confidence scores currently table-derived, not empirically calibrated.
- Hypothesis: Calibration against evidence levels + data quality improves reliability.
- Intervention:
  - Added calibration metrics script `backend/scripts/evaluate_confidence_calibration.py`
  - Added sample validation file `backend/data/calibration/validation.sample.jsonl`
- Measurement:
  - Script outputs `ece` and `brier_score` on sample/real JSONL labels
- Result: Implemented (evaluation stage complete, production post-hoc fit pending dataset scale-up).
- Decision: Keep this as gating tool for future calibration rollout.

### EXP-010 (P1): Explanation quality scoring
- Status: Implemented
- Observation: Explanation quality currently validity-checked but not scored.
- Hypothesis: Rule-based quality checks can catch low-clinical-value outputs.
- Intervention:
  - Added deterministic scorer `backend/pipeline/explanation_quality.py`
  - Integrated post-check scoring in analysis pipeline logs (`backend/main.py`)
  - Added scoring endpoint `POST /explanation-quality`
  - Added tests in `backend/tests/test_core_pipeline.py` and `backend/tests/test_api_analyze.py`
- Measurement:
  - New explanation quality tests pass
  - Endpoint returns `explanation_quality_score` + `quality_fail_reasons`
- Result: Implemented.
- Decision: Keep as quality gate and expand rubric thresholds with more data.

## 7. Operating Rules
- No production behavior change without:
  1. Hypothesis entry in this file
  2. Test updates
  3. Before/after measurement
- If experiment regresses golden outcomes, revert and log reason.

## 8. Completed Implementation List
- Stage 1 parser quality gate (`QUAL >= threshold`) and malformed-line handling
- Stage 2 diplotype extraction with reference-call suppression (`0/0`, `*1`)
- Stage 3 phenotype calling + phenotype abbreviation normalization
- Stage 4 PharmGKB lookup (TSV + fallback) with evidence-level mapping
- Stage 5 risk engine data externalization to versioned JSON rules (`rules.v1.json`)
- Stage 6 dual-LLM explanation with placeholder suppression and deterministic fallback
- Stage 7 strict schema enforcement (`extra="forbid"`)
- Strict evaluator endpoint (`/analyze-strict`)
- Rules metadata in output (`quality_metrics.clinical_rules_version`)
- Novel scientific feature: deterministic evidence provenance endpoint (`/evidence-trace`)
- Evaluator strict snapshot fixture (`backend/tests/fixtures/analyze_strict_codeine_pm.json`)
- Deterministic explanation quality scoring (`/explanation-quality`)
- Confidence calibration evaluation script (`backend/scripts/evaluate_confidence_calibration.py`)
- Phenoconversion detector + concurrent medication input support
- Cohort summary endpoint (`/cohort-summary`)
- Expanded snapshot conformance tests (`backend/tests/test_snapshot_conformance.py`)

### EXP-011 (P1): Deterministic Evidence Trace (Novel, Scientific)
- Observation: Judges/clinicians need auditable proof of how each decision was derived.
- Hypothesis: A deterministic trace endpoint improves explainability without changing prediction behavior.
- Intervention:
  - Added `build_evidence_trace()` in `backend/pipeline/risk_engine.py`
  - Added `POST /evidence-trace` in `backend/main.py`
- Measurement:
  - Endpoint returns rule key, rule match, selected risk row, PharmGKB evidence, CPIC reference, and rules version.
- Result: Implemented.
- Decision: Keep as non-breaking transparency layer.

### EXP-012 (P0): Component-based confidence scoring
- Observation: Confidence was mostly table-derived and weakly tied to observed data quality.
- Hypothesis: Decomposing confidence into evidence/genotype/phenotype/rule-coverage improves transparency and scientific defensibility.
- Intervention:
  - Added component calculator in `backend/pipeline/risk_engine.py`
  - Added weighted deterministic score function `calculate_confidence_score_v2()`
  - Wired calibrated score into `/analyze` path in `backend/main.py`
  - Added tests for bounded components and unknown-cap behavior
- Measurement:
  - Contract + golden test suite remains green
  - Unknown/fallback paths constrained (`<= 0.69`)
- Result: Implemented.
- Decision: Keep as default confidence method; add post-hoc calibration in next phase.

### EXP-013 (P1): Frontend confidence graph + evidence panel
- Observation: Confidence method was implemented in backend but not visible/auditable in the dashboard.
- Hypothesis: A per-drug confidence breakdown graph improves explainability for judges and clinicians.
- Intervention:
  - Added frontend API enrichment via `POST /evidence-trace`
  - Added `Evidence` tab with bar-graph breakdown of confidence components
  - Added CPIC/evidence/rule-match summary in UI cards
- Measurement:
  - Frontend build succeeds
  - Evidence tab renders component bars and metadata for each analyzed drug
- Result: Implemented.
- Decision: Keep and include in demo walkthrough.

### EXP-014 (P0): Phenoconversion Detector
- Observation: Genetic phenotype can be functionally shifted by strong/moderate inhibitors.
- Hypothesis: Rule-based inhibitor detection improves clinical realism for risk assessment.
- Intervention:
  - Added `backend/pipeline/phenoconversion_detector.py`
  - Added optional `concurrent_medications` to `/analyze` and `/analyze-strict`
  - Wired functional phenotype override into risk/recommendation path
  - Exposed dedicated endpoint `POST /phenoconversion-check` (strict schema remains unchanged)
- Measurement:
  - `test_phenoconversion_changes_effective_risk` passes (CODEINE + fluoxetine case)
- Result: Implemented.
- Decision: Keep as clinician-facing cautionary logic layer.

### EXP-015 (P0): Snapshot Conformance Tests
- Observation: Evaluator schema/field checks require stable conformance assertions.
- Hypothesis: Dedicated golden field conformance tests reduce submission risk.
- Intervention:
  - Added `backend/tests/test_snapshot_conformance.py`
  - Added multi-case golden checks for PM/NM paths and key risk fields
- Measurement:
  - Golden snapshot conformance tests pass in full suite.
- Result: Implemented.
- Decision: Keep and expand with additional fixtures as needed.

### EXP-016 (P1): Post-Hoc Calibration
- Observation: Raw confidence remains optimistic in some bins.
- Hypothesis: Post-hoc bin calibration improves honesty and interpretability.
- Intervention:
  - Added `backend/pipeline/confidence_calibrator.py`
  - Applied calibration in analysis confidence pipeline
  - Kept evaluation script for ECE/Brier auditing
- Measurement:
  - Calibrated confidence appears in outputs and tests remain green.
- Result: Implemented.
- Decision: Keep and refine bins with larger held-out validation sets.

### EXP-017 (P1): Evidence Trace Enhancement
- Observation: Existing trace lacked fully explicit step-by-step audit trail.
- Hypothesis: Decision-chain steps with sources improve explainability for judges.
- Intervention:
  - Enhanced `/evidence-trace` output with `decision_chain`, `total_steps`, `all_sources_cited`
  - Added step details for normalization, rule lookup, evidence, and confidence scoring
- Measurement:
  - `test_evidence_trace_contract` validates `decision_chain` availability.
- Result: Implemented.
- Decision: Keep and extend with optional variant-level provenance.

### EXP-018 (P2): Cohort Risk Matrix
- Observation: Single-patient outputs lack cohort-level operational view.
- Hypothesis: Aggregate risk matrix helps pharmacy/clinical triage workflows.
- Intervention:
  - Added `POST /cohort-summary` in `backend/main.py`
  - Returns `risk_matrix`, `high_risk_patients`, `high_risk_count`, and alert string
- Measurement:
  - `test_cohort_summary_endpoint` passes.
- Result: Implemented.
- Decision: Keep; frontend heatmap can consume this next.

### EXP-019 (P1): Frontend Clinical Ops Integration
- Observation: Backend had phenoconversion/cohort capabilities, but dashboard did not expose them.
- Hypothesis: A dedicated frontend panel for cohort risk + phenoconversion alerts improves clinical usability and demo clarity.
- Intervention:
  - Added `frontend/src/components/ClinicalOpsPanel.jsx`
  - Integrated `POST /phenoconversion-check` and `POST /cohort-summary` in `frontend/src/api.js`
  - Added `Clinical Ops` tab in `frontend/src/App.jsx`
  - Fixed drug dropdown overlap with run button using absolute dropdown positioning and z-index in `frontend/src/components/DrugInput.jsx`
- Measurement:
  - Frontend production build succeeds (`npm run build`)
  - Clinical Ops tab renders cohort snapshot and per-drug phenoconversion signals
- Result: Implemented.
- Decision: Keep and use in final demo flow.

### EXP-020 (P0): Scientific Claim Hardening
- Observation: Draft narrative mixed strong evidence with over-precise or overstated claims.
- Hypothesis: A formal claim-boundary matrix will improve judge defensibility and prevent overclaim risk.
- Intervention:
  - Added `CLAIMS_MATRIX.md` with allowed vs disallowed wording per claim class
  - Added `RESEARCH_EVIDENCE_LOG.md` mapping papers to implementation-level statements
  - Updated `README.md` with claim guardrail policy and doc links
- Measurement:
  - All major scientific claims now have constrained wording and explicit caveats where needed
- Result: Implemented.
- Decision: Keep as required pre-deployment documentation gate.
