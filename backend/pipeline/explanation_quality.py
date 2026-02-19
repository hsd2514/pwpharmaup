"""
Deterministic explanation quality checks.

Purpose:
- Score explanation quality without another model call.
- Provide concrete fail reasons for weak clinical narratives.
"""

from __future__ import annotations

import re
from typing import Dict, List

from models.schemas import DetectedVariant, LLMGeneratedExplanation


def _contains_any(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return any(n.lower() in t for n in needles)


def score_explanation_quality(
    *,
    explanation: LLMGeneratedExplanation,
    gene: str,
    drug: str,
    detected_variants: List[DetectedVariant],
    cpic_action: str,
) -> Dict[str, object]:
    reasons: List[str] = []
    checks_total = 5
    checks_passed = 0

    summary = (explanation.summary or "").strip()
    mechanism = (explanation.mechanism or "").strip()
    clinical_context = (explanation.clinical_context or "").strip()
    patient_summary = (explanation.patient_summary or "").strip()
    merged = " ".join([summary, mechanism, clinical_context, patient_summary])

    # 1) rsID mention when variants are present.
    if detected_variants:
        rsids = [v.rsid for v in detected_variants if v.rsid]
        if _contains_any(merged, rsids):
            checks_passed += 1
        else:
            reasons.append("missing_rsid_mention")
    else:
        checks_passed += 1

    # 2) Gene mention.
    if gene and gene.lower() in merged.lower():
        checks_passed += 1
    else:
        reasons.append("missing_gene_mention")

    # 3) Drug mention.
    if drug and drug.lower() in merged.lower():
        checks_passed += 1
    else:
        reasons.append("missing_drug_mention")

    # 4) Actionability signal in clinical context.
    action_keywords = ["avoid", "dose", "monitor", "alternative", "consult", "standard dosing"]
    if _contains_any(clinical_context, action_keywords):
        checks_passed += 1
    else:
        reasons.append("missing_actionable_guidance")

    # 5) Patient-facing text quality.
    if len(patient_summary.split()) >= 6:
        checks_passed += 1
    else:
        reasons.append("patient_summary_too_short")

    score = round(checks_passed / checks_total, 2)
    return {
        "explanation_quality_score": score,
        "quality_fail_reasons": reasons,
        "passed": score >= 0.8,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "cpic_action_present": bool(cpic_action and cpic_action.strip()),
    }

