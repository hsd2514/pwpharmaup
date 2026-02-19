"""
Stage 5: Risk Engine
Maps phenotype + drug to risk assessment with clinical recommendations.
"""

import logging
from typing import Optional, List, Dict, Any

from models.schemas import RiskAssessment, ClinicalRecommendation
from models.constants import RISK_TABLE, CPIC_REFERENCES
from pipeline.pharmgkb_lookup import lookup_annotation, normalize_drug_name, get_primary_gene

logger = logging.getLogger(__name__)


def assess_risk(
    drug: str,
    gene: str,
    phenotype: str
) -> RiskAssessment:
    """
    Assess pharmacogenomic risk for a drug-gene-phenotype combination.
    
    Args:
        drug: Drug name (will be normalized)
        gene: Gene symbol
        phenotype: Full phenotype string (e.g., 'Poor Metabolizer')
    
    Returns:
        RiskAssessment object
    """
    normalized_drug = normalize_drug_name(drug)
    
    # Look up in risk table
    key = (normalized_drug, gene, phenotype)
    
    if key in RISK_TABLE:
        risk_data = RISK_TABLE[key]
        return RiskAssessment(
            risk_label=risk_data["risk_label"],
            confidence_score=risk_data["confidence_score"],
            severity=risk_data["severity"]
        )
    
    # Try with function-based phenotype names (SLCO1B1)
    slco1b1_mapping = {
        "Normal Function": "Normal Metabolizer",
        "Decreased Function": "Intermediate Metabolizer",
        "Poor Function": "Poor Metabolizer",
    }
    
    if gene == "SLCO1B1":
        # Try reverse mapping
        for func_name, meta_name in slco1b1_mapping.items():
            if phenotype == func_name:
                alt_key = (normalized_drug, gene, func_name)
                if alt_key in RISK_TABLE:
                    risk_data = RISK_TABLE[alt_key]
                    return RiskAssessment(
                        risk_label=risk_data["risk_label"],
                        confidence_score=risk_data["confidence_score"],
                        severity=risk_data["severity"]
                    )
    
    # Default for unknown combinations
    logger.warning(f"No risk data for {key}, returning Unknown")
    return RiskAssessment(
        risk_label="Unknown",
        confidence_score=0.50,
        severity="unknown"
    )


def get_cpic_action(drug: str, gene: str, phenotype: str) -> str:
    """
    Get CPIC recommended action for a drug-gene-phenotype combination.
    
    Args:
        drug: Drug name
        gene: Gene symbol
        phenotype: Full phenotype string
    
    Returns:
        Action recommendation string
    """
    normalized_drug = normalize_drug_name(drug)
    key = (normalized_drug, gene, phenotype)
    
    if key in RISK_TABLE:
        return RISK_TABLE[key].get("cpic_action", "Consult clinical guidelines.")
    
    return (
        f"No curated pharmacogenomic rule found for {gene} + {normalized_drug} + {phenotype}. "
        "Classify as Unknown and consult CPIC/PharmGKB or a pharmacogenomics specialist."
    )


def get_alternative_drugs(drug: str, gene: str, phenotype: str) -> List[str]:
    """
    Get alternative drug recommendations.
    
    Args:
        drug: Drug name
        gene: Gene symbol
        phenotype: Full phenotype string
    
    Returns:
        List of alternative drug names
    """
    normalized_drug = normalize_drug_name(drug)
    key = (normalized_drug, gene, phenotype)
    
    if key in RISK_TABLE:
        return RISK_TABLE[key].get("alternatives", [])
    
    return []


def build_clinical_recommendation(
    drug: str,
    gene: str,
    phenotype: str
) -> ClinicalRecommendation:
    """
    Build complete clinical recommendation object.
    
    Args:
        drug: Drug name
        gene: Gene symbol
        phenotype: Full phenotype string
    
    Returns:
        ClinicalRecommendation object
    """
    normalized_drug = normalize_drug_name(drug)
    
    # Get PharmGKB annotation for additional data
    annotation = lookup_annotation(gene, normalized_drug)
    
    # Get CPIC reference
    ref_key = f"{gene}_{normalized_drug}"
    cpic_ref = CPIC_REFERENCES.get(ref_key, {})
    
    # Build guideline/reference with curated CPIC priority for target pairs.
    if cpic_ref:
        guideline_name = cpic_ref.get("guideline", f"CPIC Guideline for {normalized_drug} and {gene}")
        evidence = annotation.evidence_level if annotation else "1A"
        fda_req = annotation.fda_requirement if annotation else "Recommended"
        reference = (
            f"{cpic_ref.get('authors', 'CPIC')} "
            f"({cpic_ref.get('year', 'n.d.')}). PMID: {cpic_ref.get('pmid', 'N/A')}"
        )
    elif annotation:
        guideline_name = annotation.cpic_guideline
        evidence = annotation.evidence_level
        fda_req = annotation.fda_requirement
        if annotation.year and str(annotation.pmid).isdigit() and len(str(annotation.pmid)) >= 6:
            reference = f"{annotation.authors} ({annotation.year}). PMID: {annotation.pmid}"
        else:
            reference = None
    else:
        guideline_name = f"No curated CPIC guideline mapping for {normalized_drug} and {gene}"
        evidence = "4"
        fda_req = "None"
        reference = None
    
    # Get action and alternatives
    action = get_cpic_action(drug, gene, phenotype)
    alternatives = get_alternative_drugs(drug, gene, phenotype)
    
    # Build monitoring guidance
    monitoring = build_monitoring_guidance(normalized_drug, gene, phenotype)
    
    return ClinicalRecommendation(
        cpic_guideline=guideline_name,
        action=action,
        alternative_drugs=alternatives,
        monitoring=monitoring,
        evidence_level=evidence,
        fda_requirement=fda_req,
        reference=reference
    )


def build_monitoring_guidance(drug: str, gene: str, phenotype: str) -> str:
    """
    Build monitoring guidance based on risk level.
    """
    # Assess risk to determine monitoring
    risk = assess_risk(drug, gene, phenotype)
    
    if risk.severity == "critical":
        return "Do NOT initiate therapy. Consult clinical pharmacist or pharmacogenomics specialist."
    elif risk.severity == "high":
        return "Intensive monitoring required. Check labs frequently. Watch for adverse events."
    elif risk.severity == "moderate":
        return "Monitor patient response. Adjust dose as needed based on clinical outcome."
    elif risk.severity == "unknown":
        return (
            "Insufficient curated evidence for this combination. "
            "Use standard monitoring and seek specialist pharmacogenomic review."
        )
    else:
        return "Standard monitoring per drug label."


def calculate_risk_score(
    risk_assessment: RiskAssessment,
    annotation_completeness: float,
    vcf_quality: float
) -> float:
    """
    Calculate overall risk confidence score considering data quality.
    
    Args:
        risk_assessment: Base risk assessment
        annotation_completeness: Fraction of variants annotated (0-1)
        vcf_quality: VCF quality score (0-100)
    
    Returns:
        Adjusted confidence score
    """
    base_confidence = risk_assessment.confidence_score
    
    # Quality adjustments
    quality_factor = min(1.0, vcf_quality / 100)
    annotation_factor = annotation_completeness
    
    # Weight: 70% base, 15% quality, 15% annotation
    adjusted = (
        base_confidence * 0.70 +
        quality_factor * 0.15 +
        annotation_factor * 0.15
    )
    
    return round(adjusted, 2)


def get_severity_rank(severity: str) -> int:
    """
    Get numeric rank for severity level.
    Higher = more severe.
    """
    ranks = {
        "none": 0,
        "low": 1,
        "moderate": 2,
        "high": 3,
        "critical": 4,
        "unknown": -1
    }
    return ranks.get(severity, -1)


def aggregate_risk_assessments(assessments: List[RiskAssessment]) -> Dict[str, Any]:
    """
    Aggregate multiple risk assessments into summary.
    
    Args:
        assessments: List of RiskAssessment objects
    
    Returns:
        Summary dict with highest risk, average confidence, etc.
    """
    if not assessments:
        return {
            "highest_risk": "Unknown",
            "highest_severity": "unknown",
            "average_confidence": 0.0,
            "count": 0
        }
    
    # Find highest severity
    max_severity = max(assessments, key=lambda x: get_severity_rank(x.severity))
    
    # Average confidence
    avg_confidence = sum(a.confidence_score for a in assessments) / len(assessments)
    
    return {
        "highest_risk": max_severity.risk_label,
        "highest_severity": max_severity.severity,
        "average_confidence": round(avg_confidence, 2),
        "count": len(assessments)
    }
