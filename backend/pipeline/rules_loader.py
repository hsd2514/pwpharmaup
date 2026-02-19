"""
Clinical rules loader.
Loads versioned, externalized clinical rules from JSON.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LoadedRules:
    rules_version: str
    target_genes: List[str]
    default_diplotype: str
    default_phenotype: str
    supported_drugs: Dict[str, str]
    drug_aliases: Dict[str, str]
    rsid_to_star_allele: Dict[str, Dict[str, Any]]
    phenotype_abbreviations: Dict[str, str]
    cyp2d6_activity_scores: Dict[str, float]
    diplotype_phenotypes: Dict[str, Dict[Tuple[str, str], str]]
    risk_table: Dict[Tuple[str, str, str], Dict[str, Any]]
    evidence_confidence: Dict[str, Tuple[float, float]]
    confidence_model: Dict[str, Any]
    cpic_references: Dict[str, Dict[str, Any]]


_RULES: Optional[LoadedRules] = None


def _rules_path() -> Path:
    configured = os.getenv("CLINICAL_RULES_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "data" / "clinical_rules" / "rules.v1.json"


def _normalize_diplotype_map(raw: Dict[str, Dict[str, str]]) -> Dict[str, Dict[Tuple[str, str], str]]:
    out: Dict[str, Dict[Tuple[str, str], str]] = {}
    for gene, mapping in raw.items():
        out[gene] = {}
        for k, v in mapping.items():
            parts = k.split("|")
            if len(parts) != 2:
                continue
            out[gene][(parts[0], parts[1])] = v
    return out


def _normalize_risk_table(raw: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    table: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in raw:
        key = (row["drug"], row["gene"], row["phenotype"])
        table[key] = {
            "risk_label": row["risk_label"],
            "severity": row["severity"],
            "confidence_score": row["confidence_score"],
            "cpic_action": row.get("cpic_action", ""),
            "alternatives": row.get("alternatives", []),
        }
    return table


def _normalize_evidence(raw: Dict[str, List[float]]) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for k, v in raw.items():
        if isinstance(v, list) and len(v) == 2:
            out[k] = (float(v[0]), float(v[1]))
    return out


def _validate_required(data: Dict[str, Any]) -> None:
    required = [
        "rules_version",
        "target_genes",
        "default_diplotype",
        "default_phenotype",
        "supported_drugs",
        "drug_aliases",
        "rsid_to_star_allele",
        "phenotype_abbreviations",
        "cyp2d6_activity_scores",
        "diplotype_phenotypes",
        "risk_table",
        "evidence_confidence",
        "confidence_model",
        "cpic_references",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Clinical rules file missing keys: {missing}")


def load_rules(force_reload: bool = False) -> LoadedRules:
    global _RULES
    if _RULES is not None and not force_reload:
        return _RULES

    path = _rules_path()
    if not path.exists():
        raise FileNotFoundError(f"Clinical rules file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    _validate_required(data)

    _RULES = LoadedRules(
        rules_version=str(data["rules_version"]),
        target_genes=list(data["target_genes"]),
        default_diplotype=str(data["default_diplotype"]),
        default_phenotype=str(data["default_phenotype"]),
        supported_drugs=dict(data["supported_drugs"]),
        drug_aliases=dict(data["drug_aliases"]),
        rsid_to_star_allele=dict(data["rsid_to_star_allele"]),
        phenotype_abbreviations=dict(data["phenotype_abbreviations"]),
        cyp2d6_activity_scores={k: float(v) for k, v in data["cyp2d6_activity_scores"].items()},
        diplotype_phenotypes=_normalize_diplotype_map(dict(data["diplotype_phenotypes"])),
        risk_table=_normalize_risk_table(list(data["risk_table"])),
        evidence_confidence=_normalize_evidence(dict(data["evidence_confidence"])),
        confidence_model=dict(data["confidence_model"]),
        cpic_references=dict(data["cpic_references"]),
    )
    logger.info(f"Loaded clinical rules version {_RULES.rules_version} from {path}")
    return _RULES


def get_rules() -> LoadedRules:
    return load_rules()
