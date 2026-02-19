"""
Stage 4: PharmGKB Evidence Lookup
Provides gene-drug evidence annotations and clinical significance.

Data is loaded from the real PharmGKB TSV files in backend/data/:
  clinical/clinical_annotations.tsv  — evidence levels & categories
  variants/var_drug_ann.tsv           — variant-drug annotations & sentences

Falls back to hardcoded table if files are not present.
"""

import csv
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from models.constants import (
    CPIC_REFERENCES,
    DRUG_ALIASES,
    EVIDENCE_CONFIDENCE,
    SUPPORTED_DRUGS,
)

logger = logging.getLogger(__name__)

# Resolve data directory relative to this file: backend/data/
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class PharmGKBAnnotation:
    """Annotation data from PharmGKB."""
    gene: str
    drug: str
    evidence_level: str
    clinical_significance: str
    fda_requirement: str
    cpic_guideline: str
    pmid: str
    year: int
    authors: str
    # Extra fields populated from real TSV data
    annotation_sentences: List[str] = field(default_factory=list)
    phenotype_categories: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hardcoded fallback (used when TSV files are absent)
# ---------------------------------------------------------------------------
_FALLBACK_ANNOTATIONS: Dict[Tuple[str, str], PharmGKBAnnotation] = {
    ("CYP2D6", "CODEINE"): PharmGKBAnnotation(
        gene="CYP2D6", drug="CODEINE", evidence_level="1A",
        clinical_significance="Toxicity/ADR and Efficacy", fda_requirement="Required",
        cpic_guideline="CPIC Guideline for Codeine and CYP2D6",
        pmid="24458010", year=2014, authors="Crews et al.",
    ),
    ("CYP2C19", "CLOPIDOGREL"): PharmGKBAnnotation(
        gene="CYP2C19", drug="CLOPIDOGREL", evidence_level="1A",
        clinical_significance="Efficacy", fda_requirement="Required",
        cpic_guideline="CPIC Guideline for Clopidogrel and CYP2C19",
        pmid="23698643", year=2013, authors="Scott et al.",
    ),
    ("CYP2C9", "WARFARIN"): PharmGKBAnnotation(
        gene="CYP2C9", drug="WARFARIN", evidence_level="1A",
        clinical_significance="Toxicity/ADR and Dosage", fda_requirement="Required",
        cpic_guideline="CPIC Guideline for Warfarin and CYP2C9",
        pmid="21900891", year=2011, authors="Johnson et al.",
    ),
    ("SLCO1B1", "SIMVASTATIN"): PharmGKBAnnotation(
        gene="SLCO1B1", drug="SIMVASTATIN", evidence_level="1A",
        clinical_significance="Toxicity/ADR", fda_requirement="Recommended",
        cpic_guideline="CPIC Guideline for Simvastatin and SLCO1B1",
        pmid="24918167", year=2014, authors="Ramsey et al.",
    ),
    ("TPMT", "AZATHIOPRINE"): PharmGKBAnnotation(
        gene="TPMT", drug="AZATHIOPRINE", evidence_level="1A",
        clinical_significance="Toxicity/ADR", fda_requirement="Required",
        cpic_guideline="CPIC Guideline for Azathioprine and TPMT",
        pmid="21270794", year=2011, authors="Relling et al.",
    ),
    ("DPYD", "FLUOROURACIL"): PharmGKBAnnotation(
        gene="DPYD", drug="FLUOROURACIL", evidence_level="1A",
        clinical_significance="Toxicity/ADR", fda_requirement="Recommended",
        cpic_guideline="CPIC Guideline for Fluorouracil and DPYD",
        pmid="23988873", year=2013, authors="Caudle et al.",
    ),
}


# ---------------------------------------------------------------------------
# TSV loaders
# ---------------------------------------------------------------------------

def _load_clinical_annotations(path: Path) -> Dict[Tuple[str, str], PharmGKBAnnotation]:
    """
    Parse clinical_annotations.tsv downloaded from PharmGKB.

    Relevant columns:
        Gene | Drug(s) | Level of Evidence | Phenotype Category | PMID Count | URL
    """
    annotations: Dict[Tuple[str, str], PharmGKBAnnotation] = {}

    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            gene = row.get("Gene", "").strip()
            drugs_raw = row.get("Drug(s)", "").strip()
            level = row.get("Level of Evidence", "").strip()
            category = row.get("Phenotype Category", "").strip()
            pmid_count = row.get("PMID Count", "0").strip()
            url = row.get("URL", "").strip()

            if not gene or not drugs_raw or not level:
                continue

            # Drug(s) cell can be semicolon-separated, e.g. "codeine;morphine"
            for raw_drug in drugs_raw.split(";"):
                drug = raw_drug.strip().upper()
                if not drug:
                    continue
                key = (gene, drug)
                # Keep the annotation with the highest evidence level (lowest number)
                existing = annotations.get(key)
                if existing and _evidence_rank(existing.evidence_level) <= _evidence_rank(level):
                    # Merge phenotype categories
                    existing.phenotype_categories = list(
                        set(existing.phenotype_categories + [c.strip() for c in category.split(",")])
                    )
                    continue

                cpic = CPIC_REFERENCES.get(gene, f"CPIC Guideline for {gene}")
                annotations[key] = PharmGKBAnnotation(
                    gene=gene,
                    drug=drug,
                    evidence_level=level,
                    clinical_significance=category,
                    fda_requirement=_infer_fda_requirement(level),
                    cpic_guideline=cpic,
                    pmid=pmid_count,
                    year=0,
                    authors="PharmGKB",
                    phenotype_categories=[c.strip() for c in category.split(",") if c.strip()],
                )

    logger.info(f"Loaded {len(annotations)} gene-drug pairs from {path.name}")
    return annotations


def _load_variant_drug_annotations(path: Path, annotations: Dict[Tuple[str, str], PharmGKBAnnotation]) -> None:
    """
    Enrich existing annotations with human-readable sentences from var_drug_ann.tsv.

    Relevant columns:
        Gene | Drug(s) | Sentence | Significance | Metabolizer types
    """
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            gene = row.get("Gene", "").strip()
            drugs_raw = row.get("Drug(s)", "").strip()
            sentence = row.get("Sentence", "").strip()
            significance = row.get("Significance", "").strip()

            if not gene or not drugs_raw or not sentence:
                continue

            for raw_drug in drugs_raw.split(";"):
                drug = raw_drug.strip().upper()
                key = (gene, drug)
                ann = annotations.get(key)
                if ann and sentence not in ann.annotation_sentences:
                    ann.annotation_sentences.append(sentence)


def _evidence_rank(level: str) -> int:
    """Lower number = better evidence. Used to keep highest-confidence entry."""
    order = {"1A": 1, "1B": 2, "2A": 3, "2B": 4, "3": 5, "4": 6}
    return order.get(level.upper(), 99)


def _infer_fda_requirement(level: str) -> str:
    level = level.upper()
    if level == "1A":
        return "Required"
    if level == "1B":
        return "Recommended"
    return "None"


# ---------------------------------------------------------------------------
# Build the module-level lookup table on import
# ---------------------------------------------------------------------------

def _build_annotation_table() -> Dict[Tuple[str, str], PharmGKBAnnotation]:
    clinical_tsv = _DATA_DIR / "clinical" / "clinical_annotations.tsv"
    variant_tsv  = _DATA_DIR / "variants"  / "var_drug_ann.tsv"

    if not clinical_tsv.exists():
        logger.warning(
            f"PharmGKB TSV not found at {clinical_tsv}. Using hardcoded fallback table. "
            "Download data from https://www.pharmgkb.org/downloads and extract to backend/data/"
        )
        return dict(_FALLBACK_ANNOTATIONS)

    try:
        table = _load_clinical_annotations(clinical_tsv)
        if variant_tsv.exists():
            _load_variant_drug_annotations(variant_tsv, table)
        else:
            logger.warning(f"var_drug_ann.tsv not found at {variant_tsv} — skipping sentence enrichment")
        # Merge fallback entries that are not already present (keeps hardcoded CPIC detail)
        for k, v in _FALLBACK_ANNOTATIONS.items():
            table.setdefault(k, v)
        return table
    except Exception as exc:
        logger.error(f"Failed to load PharmGKB TSVs: {exc}. Falling back to hardcoded data.")
        return dict(_FALLBACK_ANNOTATIONS)


PHARMGKB_ANNOTATIONS: Dict[Tuple[str, str], PharmGKBAnnotation] = _build_annotation_table()


def normalize_drug_name(drug_name: str) -> str:
    """
    Normalize drug name to standard form.
    Handles brand names and common variations.
    
    Args:
        drug_name: Raw drug name input
    
    Returns:
        Normalized drug name (uppercase)
    """
    drug_upper = drug_name.strip().upper()
    
    # Check aliases first
    if drug_upper in DRUG_ALIASES:
        return DRUG_ALIASES[drug_upper]
    
    # Check if already a supported drug
    if drug_upper in SUPPORTED_DRUGS:
        return drug_upper
    
    # Try partial matching
    for alias, standard in DRUG_ALIASES.items():
        if alias in drug_upper or drug_upper in alias:
            return standard
    
    # Return as-is if no match
    return drug_upper


def get_primary_gene(drug: str) -> Optional[str]:
    """
    Get the primary metabolizing gene for a drug.
    
    Args:
        drug: Normalized drug name
    
    Returns:
        Gene symbol or None if not supported
    """
    normalized = normalize_drug_name(drug)
    return SUPPORTED_DRUGS.get(normalized)


def lookup_annotation(gene: str, drug: str) -> Optional[PharmGKBAnnotation]:
    """
    Look up PharmGKB annotation for a gene-drug pair.
    
    Args:
        gene: Gene symbol (e.g., 'CYP2D6')
        drug: Drug name (e.g., 'CODEINE')
    
    Returns:
        PharmGKBAnnotation or None if not found
    """
    normalized_drug = normalize_drug_name(drug)
    key = (gene, normalized_drug)
    
    return PHARMGKB_ANNOTATIONS.get(key)


def get_evidence_confidence_range(evidence_level: str) -> Tuple[float, float]:
    """
    Get confidence score range for an evidence level.
    
    Args:
        evidence_level: PharmGKB evidence level (1A, 1B, 2A, etc.)
    
    Returns:
        Tuple of (min_confidence, max_confidence)
    """
    return EVIDENCE_CONFIDENCE.get(evidence_level, (0.50, 0.60))


def is_drug_supported(drug: str) -> bool:
    """
    Check if a drug is supported by the system.
    
    Args:
        drug: Drug name
    
    Returns:
        True if supported
    """
    normalized = normalize_drug_name(drug)
    return normalized in SUPPORTED_DRUGS


def get_all_supported_drugs() -> list:
    """
    Get list of all supported drug names.
    
    Returns:
        List of supported drug names
    """
    return list(SUPPORTED_DRUGS.keys())


def get_fda_requirement(gene: str, drug: str) -> str:
    """
    Get FDA testing requirement for gene-drug pair.
    
    Args:
        gene: Gene symbol
        drug: Drug name
    
    Returns:
        FDA requirement status
    """
    annotation = lookup_annotation(gene, drug)
    if annotation:
        return annotation.fda_requirement
    return "None"


def build_cpic_reference(gene: str, drug: str) -> Optional[str]:
    """
    Build CPIC reference citation string.
    
    Args:
        gene: Gene symbol
        drug: Drug name
    
    Returns:
        Reference string or None
    """
    annotation = lookup_annotation(gene, drug)
    if annotation:
        return f"{annotation.authors} ({annotation.year}). {annotation.cpic_guideline}. PMID: {annotation.pmid}"
    return None
