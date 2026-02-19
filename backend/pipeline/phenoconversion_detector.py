"""
Phenoconversion detector (rule-based).

Detects likely phenotype shifts when strong/moderate/weak inhibitors are present
in concurrent medications.
"""

from __future__ import annotations

from typing import Dict, List, Any


CYP_INHIBITORS: Dict[str, Dict[str, List[str]]] = {
    "CYP2D6": {
        "strong": ["fluoxetine", "paroxetine", "bupropion", "quinidine"],
        "moderate": ["duloxetine", "terbinafine", "cinacalcet"],
        "weak": ["amiodarone", "cimetidine"],
    },
    "CYP2C19": {
        "strong": ["omeprazole", "esomeprazole", "fluvoxamine"],
        "moderate": ["fluconazole", "moclobemide"],
        "weak": ["cimetidine", "etravirine"],
    },
    "CYP2C9": {
        "strong": ["fluconazole", "amiodarone"],
        "moderate": ["miconazole", "metronidazole"],
        "weak": ["ibuprofen"],
    },
}


PHENOTYPE_DOWNGRADE: Dict[str, Dict[str, str]] = {
    "strong": {
        "URM": "NM",
        "RM": "IM",
        "NM": "IM",
        "IM": "PM",
        "PM": "PM",
    },
    "moderate": {
        "URM": "RM",
        "RM": "NM",
        "NM": "NM",
        "IM": "IM",
        "PM": "PM",
    },
    "weak": {
        "URM": "URM",
        "RM": "RM",
        "NM": "NM",
        "IM": "IM",
        "PM": "PM",
    },
}


PHENOTYPE_FULL = {
    "PM": "Poor Metabolizer",
    "IM": "Intermediate Metabolizer",
    "NM": "Normal Metabolizer",
    "RM": "Rapid Metabolizer",
    "URM": "Ultrarapid Metabolizer",
    "Unknown": "Unknown",
}


_STRENGTH_ORDER = {"weak": 0, "moderate": 1, "strong": 2}
_PENALTY = {"weak": 0.02, "moderate": 0.05, "strong": 0.10}


def _normalize_med_name(name: str) -> str:
    return str(name).strip().lower()


def detect_phenoconversion(
    *,
    gene: str,
    genetic_phenotype_abbrev: str,
    concurrent_medications: List[str],
) -> Dict[str, Any]:
    gene_key = (gene or "").upper()
    meds = [_normalize_med_name(m) for m in concurrent_medications if str(m).strip()]

    gene_inhibitors = CYP_INHIBITORS.get(gene_key, {})
    detected_inhibitors: List[Dict[str, str]] = []
    highest_strength = None

    for strength, inhibitors in gene_inhibitors.items():
        inhibitor_set = {i.lower() for i in inhibitors}
        for med in meds:
            if med in inhibitor_set:
                detected_inhibitors.append({"drug": med, "strength": strength})
                if highest_strength is None or _STRENGTH_ORDER[strength] > _STRENGTH_ORDER[highest_strength]:
                    highest_strength = strength

    if not detected_inhibitors:
        return {
            "phenoconversion_risk": False,
            "genetic_phenotype": genetic_phenotype_abbrev,
            "functional_phenotype": genetic_phenotype_abbrev,
            "functional_phenotype_full": PHENOTYPE_FULL.get(genetic_phenotype_abbrev, "Unknown"),
            "caused_by": [],
            "confidence_penalty": 0.0,
            "clinical_note": "No known inhibitor-based phenoconversion signal detected.",
        }

    functional = PHENOTYPE_DOWNGRADE.get(highest_strength, {}).get(
        genetic_phenotype_abbrev,
        genetic_phenotype_abbrev,
    )
    drugs_str = ", ".join(sorted({d["drug"] for d in detected_inhibitors}))
    return {
        "phenoconversion_risk": True,
        "genetic_phenotype": genetic_phenotype_abbrev,
        "functional_phenotype": functional,
        "functional_phenotype_full": PHENOTYPE_FULL.get(functional, "Unknown"),
        "caused_by": detected_inhibitors,
        "confidence_penalty": _PENALTY.get(highest_strength, 0.0),
        "clinical_note": (
            f"Genetic phenotype {genetic_phenotype_abbrev} may functionally shift to {functional} "
            f"due to inhibitor exposure ({drugs_str}). Source: inhibitor rule table."
        ),
    }

