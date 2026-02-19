"""
Constants and hardcoded risk mappings for PharmaGuard AI.
Based on CPIC guidelines and PharmGKB clinical annotations.
"""

from typing import Dict, List, Tuple

# Target genes for pharmacogenomic analysis
TARGET_GENES = ["CYP2D6", "CYP2C19", "CYP2C9", "SLCO1B1", "TPMT", "DPYD"]

# Supported drugs with their primary metabolizing genes
SUPPORTED_DRUGS = {
    "CODEINE": "CYP2D6",
    "CLOPIDOGREL": "CYP2C19",
    "WARFARIN": "CYP2C9",
    "SIMVASTATIN": "SLCO1B1",
    "AZATHIOPRINE": "TPMT",
    "FLUOROURACIL": "DPYD",
    "5-FLUOROURACIL": "DPYD",
    "5-FU": "DPYD",
}

# Drug name aliases for normalization
DRUG_ALIASES = {
    # Codeine aliases
    "TYLENOL 3": "CODEINE",
    "TYLENOL-3": "CODEINE",
    "TYLENOL WITH CODEINE": "CODEINE",
    "CODEINE PHOSPHATE": "CODEINE",
    "CODEINE SULFATE": "CODEINE",
    # Clopidogrel aliases
    "PLAVIX": "CLOPIDOGREL",
    # Warfarin aliases
    "COUMADIN": "WARFARIN",
    "JANTOVEN": "WARFARIN",
    # Simvastatin aliases
    "ZOCOR": "SIMVASTATIN",
    # Azathioprine aliases
    "IMURAN": "AZATHIOPRINE",
    "AZASAN": "AZATHIOPRINE",
    # Fluorouracil aliases
    "5-FU": "FLUOROURACIL",
    "5-FLUOROURACIL": "FLUOROURACIL",
    "ADRUCIL": "FLUOROURACIL",
    "EFUDEX": "FLUOROURACIL",
    "CARAC": "FLUOROURACIL",
}

# rsID to Star Allele mappings (from PharmVar)
RSID_TO_STAR_ALLELE = {
    # CYP2D6
    "rs3892097": {"gene": "CYP2D6", "star": "*4", "function": "No function"},
    "rs35742686": {"gene": "CYP2D6", "star": "*3", "function": "No function"},
    "rs5030655": {"gene": "CYP2D6", "star": "*6", "function": "No function"},
    "rs16947": {"gene": "CYP2D6", "star": "*2", "function": "Normal function"},
    "rs1065852": {"gene": "CYP2D6", "star": "*10", "function": "Decreased function"},
    # CYP2C19
    "rs4244285": {"gene": "CYP2C19", "star": "*2", "function": "No function"},
    "rs4986893": {"gene": "CYP2C19", "star": "*3", "function": "No function"},
    "rs12248560": {"gene": "CYP2C19", "star": "*17", "function": "Increased function"},
    "rs28399504": {"gene": "CYP2C19", "star": "*4", "function": "No function"},
    # CYP2C9
    "rs1799853": {"gene": "CYP2C9", "star": "*2", "function": "Decreased function"},
    "rs1057910": {"gene": "CYP2C9", "star": "*3", "function": "Decreased function"},
    "rs28371686": {"gene": "CYP2C9", "star": "*5", "function": "Decreased function"},
    "rs9332131": {"gene": "CYP2C9", "star": "*6", "function": "No function"},
    # SLCO1B1
    "rs4149056": {"gene": "SLCO1B1", "star": "*5", "function": "Decreased function"},
    "rs2306283": {"gene": "SLCO1B1", "star": "*1B", "function": "Normal function"},
    # TPMT
    "rs1800462": {"gene": "TPMT", "star": "*2", "function": "No function"},
    "rs1800460": {"gene": "TPMT", "star": "*3B", "function": "No function"},
    "rs1142345": {"gene": "TPMT", "star": "*3C", "function": "No function"},
    # DPYD
    "rs3918290": {"gene": "DPYD", "star": "*2A", "function": "No function"},
    "rs55886062": {"gene": "DPYD", "star": "*13", "function": "No function"},
    "rs67376798": {"gene": "DPYD", "star": "HapB3", "function": "Decreased function"},
    "rs75017182": {"gene": "DPYD", "star": "c.1129-5923C>G", "function": "Decreased function"},
}

# Phenotype labels mapping (PyPGx output -> Our schema)
PHENOTYPE_ABBREVIATIONS = {
    "Poor Metabolizer": "PM",
    "Intermediate Metabolizer": "IM",
    "Normal Metabolizer": "NM",
    "Rapid Metabolizer": "RM",
    "Ultrarapid Metabolizer": "URM",
    "Poor Function": "PM",
    "Decreased Function": "IM",
    "Normal Function": "NM",
    "Increased Function": "RM",
    "Unknown": "Unknown",
}

# Activity scores for diplotypes (CYP2D6)
CYP2D6_ACTIVITY_SCORES = {
    "*1": 1.0,
    "*2": 1.0,
    "*3": 0.0,
    "*4": 0.0,
    "*5": 0.0,
    "*6": 0.0,
    "*9": 0.5,
    "*10": 0.25,
    "*17": 0.5,
    "*29": 0.5,
    "*41": 0.5,
    "*1xN": 2.0,  # Gene duplication
    "*2xN": 2.0,
}

# Diplotype to phenotype mappings
DIPLOTYPE_PHENOTYPES = {
    "CYP2D6": {
        ("*1", "*1"): "Normal Metabolizer",
        ("*1", "*2"): "Normal Metabolizer",
        ("*2", "*2"): "Normal Metabolizer",
        ("*1", "*4"): "Intermediate Metabolizer",
        ("*2", "*4"): "Intermediate Metabolizer",
        ("*1", "*10"): "Intermediate Metabolizer",
        ("*4", "*4"): "Poor Metabolizer",
        ("*4", "*5"): "Poor Metabolizer",
        ("*5", "*5"): "Poor Metabolizer",
        ("*3", "*4"): "Poor Metabolizer",
        ("*1", "*1xN"): "Ultrarapid Metabolizer",
        ("*2", "*2xN"): "Ultrarapid Metabolizer",
    },
    "CYP2C19": {
        ("*1", "*1"): "Normal Metabolizer",
        ("*1", "*2"): "Intermediate Metabolizer",
        ("*1", "*3"): "Intermediate Metabolizer",
        ("*2", "*2"): "Poor Metabolizer",
        ("*2", "*3"): "Poor Metabolizer",
        ("*3", "*3"): "Poor Metabolizer",
        ("*1", "*17"): "Rapid Metabolizer",
        ("*17", "*17"): "Ultrarapid Metabolizer",
    },
    "CYP2C9": {
        ("*1", "*1"): "Normal Metabolizer",
        ("*1", "*2"): "Intermediate Metabolizer",
        ("*1", "*3"): "Intermediate Metabolizer",
        ("*2", "*2"): "Poor Metabolizer",
        ("*2", "*3"): "Poor Metabolizer",
        ("*3", "*3"): "Poor Metabolizer",
    },
    "SLCO1B1": {
        ("*1", "*1"): "Normal Function",
        ("*1", "*5"): "Decreased Function",
        ("*5", "*5"): "Poor Function",
        ("*1", "*1B"): "Normal Function",
        ("*1B", "*5"): "Decreased Function",
    },
    "TPMT": {
        ("*1", "*1"): "Normal Metabolizer",
        ("*1", "*2"): "Intermediate Metabolizer",
        ("*1", "*3A"): "Intermediate Metabolizer",
        ("*1", "*3B"): "Intermediate Metabolizer",
        ("*1", "*3C"): "Intermediate Metabolizer",
        ("*3A", "*3A"): "Poor Metabolizer",
        ("*3B", "*3C"): "Poor Metabolizer",
        ("*2", "*3A"): "Poor Metabolizer",
    },
    "DPYD": {
        ("*1", "*1"): "Normal Metabolizer",
        ("*1", "*2A"): "Intermediate Metabolizer",
        ("*1", "*13"): "Intermediate Metabolizer",
        ("*1", "HapB3"): "Intermediate Metabolizer",
        ("*2A", "*2A"): "Poor Metabolizer",
        ("*2A", "*13"): "Poor Metabolizer",
        ("*13", "*13"): "Poor Metabolizer",
    },
}

# Complete Risk Mapping Table - Core of Stage 5
# (Drug, Gene, Phenotype) -> (risk_label, severity, confidence)
RISK_TABLE: Dict[Tuple[str, str, str], Dict] = {
    # CODEINE - CYP2D6
    ("CODEINE", "CYP2D6", "Poor Metabolizer"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.95,
        "cpic_action": "Avoid codeine. Use morphine or non-opioid alternative. CPIC Level 1A.",
        "alternatives": ["morphine", "non-opioid analgesics", "tramadol"],
    },
    ("CODEINE", "CYP2D6", "Ultrarapid Metabolizer"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "cpic_action": "Avoid codeine due to risk of respiratory depression. Use non-opioid alternative.",
        "alternatives": ["non-opioid analgesics", "morphine with reduced dose"],
    },
    ("CODEINE", "CYP2D6", "Intermediate Metabolizer"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.85,
        "cpic_action": "Use codeine with caution. Consider reduced dose or alternative.",
        "alternatives": ["morphine", "acetaminophen"],
    },
    ("CODEINE", "CYP2D6", "Normal Metabolizer"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.95,
        "cpic_action": "Use codeine per standard dosing guidelines.",
        "alternatives": [],
    },
    # CLOPIDOGREL - CYP2C19
    ("CLOPIDOGREL", "CYP2C19", "Poor Metabolizer"): {
        "risk_label": "Ineffective",
        "severity": "high",
        "confidence_score": 0.92,
        "cpic_action": "Avoid clopidogrel. Use prasugrel or ticagrelor instead. CPIC Level 1A.",
        "alternatives": ["prasugrel", "ticagrelor"],
    },
    ("CLOPIDOGREL", "CYP2C19", "Intermediate Metabolizer"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.85,
        "cpic_action": "Consider alternative antiplatelet or higher clopidogrel dose with monitoring.",
        "alternatives": ["prasugrel", "ticagrelor"],
    },
    ("CLOPIDOGREL", "CYP2C19", "Rapid Metabolizer"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.80,
        "cpic_action": "Standard dosing expected to be effective. No change needed.",
        "alternatives": [],
    },
    ("CLOPIDOGREL", "CYP2C19", "Ultrarapid Metabolizer"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.90,
        "cpic_action": "Standard dosing. Enhanced antiplatelet effect expected.",
        "alternatives": [],
    },
    ("CLOPIDOGREL", "CYP2C19", "Normal Metabolizer"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.95,
        "cpic_action": "Use clopidogrel per standard dosing guidelines.",
        "alternatives": [],
    },
    # WARFARIN - CYP2C9
    ("WARFARIN", "CYP2C9", "Poor Metabolizer"): {
        "risk_label": "Toxic",
        "severity": "high",
        "confidence_score": 0.93,
        "cpic_action": "Reduce warfarin dose by 50-80%. Use lower initial dose. Monitor INR closely.",
        "alternatives": ["direct oral anticoagulants (DOACs)", "apixaban", "rivaroxaban"],
    },
    ("WARFARIN", "CYP2C9", "Intermediate Metabolizer"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.88,
        "cpic_action": "Reduce initial warfarin dose by 25-50%. Monitor INR frequently.",
        "alternatives": [],
    },
    ("WARFARIN", "CYP2C9", "Normal Metabolizer"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.95,
        "cpic_action": "Use warfarin per standard dosing algorithm.",
        "alternatives": [],
    },
    # SIMVASTATIN - SLCO1B1
    ("SIMVASTATIN", "SLCO1B1", "Poor Function"): {
        "risk_label": "Toxic",
        "severity": "high",
        "confidence_score": 0.90,
        "cpic_action": "Avoid simvastatin or use ≤20mg dose. Consider alternative statin.",
        "alternatives": ["pravastatin", "rosuvastatin", "atorvastatin (lower dose)"],
    },
    ("SIMVASTATIN", "SLCO1B1", "Decreased Function"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.85,
        "cpic_action": "Use simvastatin ≤20mg daily. Monitor for myopathy symptoms.",
        "alternatives": ["pravastatin", "rosuvastatin"],
    },
    ("SIMVASTATIN", "SLCO1B1", "Normal Function"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.95,
        "cpic_action": "Use simvastatin per standard dosing guidelines.",
        "alternatives": [],
    },
    # AZATHIOPRINE - TPMT
    ("AZATHIOPRINE", "TPMT", "Poor Metabolizer"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.97,
        "cpic_action": "Drastically reduce dose (10% of standard) or use alternative agent. Risk of fatal myelosuppression.",
        "alternatives": ["mycophenolate mofetil", "alternative immunosuppressant"],
    },
    ("AZATHIOPRINE", "TPMT", "Intermediate Metabolizer"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.90,
        "cpic_action": "Reduce azathioprine dose by 30-70%. Monitor CBC weekly initially.",
        "alternatives": [],
    },
    ("AZATHIOPRINE", "TPMT", "Normal Metabolizer"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.95,
        "cpic_action": "Use azathioprine per standard dosing guidelines.",
        "alternatives": [],
    },
    # FLUOROURACIL - DPYD
    ("FLUOROURACIL", "DPYD", "Poor Metabolizer"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.96,
        "cpic_action": "Avoid fluorouracil. Risk of fatal toxicity. Use alternative therapy.",
        "alternatives": ["alternative chemotherapy regimen per oncologist"],
    },
    ("FLUOROURACIL", "DPYD", "Intermediate Metabolizer"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "confidence_score": 0.91,
        "cpic_action": "Reduce fluorouracil dose by 25-50%. Monitor closely for toxicity.",
        "alternatives": [],
    },
    ("FLUOROURACIL", "DPYD", "Normal Metabolizer"): {
        "risk_label": "Safe",
        "severity": "none",
        "confidence_score": 0.95,
        "cpic_action": "Use fluorouracil per standard dosing guidelines.",
        "alternatives": [],
    },
}

# Evidence level to confidence score mapping
EVIDENCE_CONFIDENCE = {
    "1A": (0.95, 0.97),
    "1B": (0.88, 0.93),
    "2A": (0.80, 0.87),
    "2B": (0.70, 0.79),
    "3": (0.55, 0.69),
    "4": (0.40, 0.54),
}

# CPIC guideline references
CPIC_REFERENCES = {
    "CYP2D6_CODEINE": {
        "guideline": "CPIC Guideline for Codeine and CYP2D6",
        "pmid": "24458010",
        "year": 2014,
        "authors": "Crews et al.",
    },
    "CYP2C19_CLOPIDOGREL": {
        "guideline": "CPIC Guideline for Clopidogrel and CYP2C19",
        "pmid": "23698643",
        "year": 2013,
        "authors": "Scott et al.",
    },
    "CYP2C9_WARFARIN": {
        "guideline": "CPIC Guideline for Warfarin and CYP2C9",
        "pmid": "21900891",
        "year": 2011,
        "authors": "Johnson et al.",
    },
    "SLCO1B1_SIMVASTATIN": {
        "guideline": "CPIC Guideline for Simvastatin and SLCO1B1",
        "pmid": "24918167",
        "year": 2014,
        "authors": "Ramsey et al.",
    },
    "TPMT_AZATHIOPRINE": {
        "guideline": "CPIC Guideline for Azathioprine and TPMT",
        "pmid": "21270794",
        "year": 2011,
        "authors": "Relling et al.",
    },
    "DPYD_FLUOROURACIL": {
        "guideline": "CPIC Guideline for Fluorouracil and DPYD",
        "pmid": "23988873",
        "year": 2013,
        "authors": "Caudle et al.",
    },
}

# Default phenotype when no variants detected
DEFAULT_PHENOTYPE = "Normal Metabolizer"
DEFAULT_DIPLOTYPE = "*1/*1"
