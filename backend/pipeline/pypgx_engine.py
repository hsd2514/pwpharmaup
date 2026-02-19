"""
Stage 3: PyPGx Phenotype Engine
Handles diplotype-to-phenotype translation.

Note: Since PyPGx library has complex dependencies, we implement
equivalent logic using CPIC-aligned lookup tables.
"""

import logging
from typing import Dict, Optional, Tuple

from pipeline.rules_loader import get_rules

logger = logging.getLogger(__name__)
_RULES = get_rules()


def call_phenotype(gene: str, diplotype: str) -> str:
    """
    Determine phenotype from gene and diplotype.
    Mimics pypgx.call_phenotype() functionality.
    
    Args:
        gene: Gene symbol (e.g., 'CYP2D6')
        diplotype: Diplotype string (e.g., '*4/*4')
    
    Returns:
        Phenotype string (e.g., 'Poor Metabolizer')
    """
    if gene not in _RULES.target_genes:
        logger.warning(f"Gene {gene} not in target genes")
        return "Unknown"
    
    # Parse diplotype into alleles
    allele1, allele2 = parse_diplotype_string(diplotype)
    
    # Check direct lookup first
    if gene in _RULES.diplotype_phenotypes:
        gene_phenotypes = _RULES.diplotype_phenotypes[gene]
        
        # Try both orderings
        key1 = (allele1, allele2)
        key2 = (allele2, allele1)
        
        if key1 in gene_phenotypes:
            return gene_phenotypes[key1]
        if key2 in gene_phenotypes:
            return gene_phenotypes[key2]
    
    # For CYP2D6, use activity score-based phenotype calling
    if gene == "CYP2D6":
        return call_cyp2d6_phenotype_by_activity(allele1, allele2)
    
    # For other genes, infer from allele function
    return infer_phenotype_from_alleles(gene, allele1, allele2)


def parse_diplotype_string(diplotype: str) -> Tuple[str, str]:
    """
    Parse diplotype string into two alleles.
    """
    if "/" not in diplotype:
        return ("*1", "*1")
    
    parts = diplotype.split("/")
    if len(parts) != 2:
        return ("*1", "*1")
    
    allele1 = parts[0].strip()
    allele2 = parts[1].strip()
    
    # Ensure * prefix
    if allele1 and not allele1.startswith("*"):
        allele1 = f"*{allele1}"
    if allele2 and not allele2.startswith("*"):
        allele2 = f"*{allele2}"
    
    return (allele1 or "*1", allele2 or "*1")


def call_cyp2d6_phenotype_by_activity(allele1: str, allele2: str) -> str:
    """
    Call CYP2D6 phenotype using activity scores (CPIC method).
    
    Activity Score Ranges:
    - 0: Poor Metabolizer
    - 0.25-1.0: Intermediate Metabolizer
    - 1.25-2.25: Normal Metabolizer
    - >2.25: Ultrarapid Metabolizer
    """
    score1 = _RULES.cyp2d6_activity_scores.get(allele1, 1.0)  # Default to functional
    score2 = _RULES.cyp2d6_activity_scores.get(allele2, 1.0)
    
    total_score = score1 + score2
    
    if total_score == 0:
        return "Poor Metabolizer"
    elif total_score <= 1.0:
        return "Intermediate Metabolizer"
    elif total_score <= 2.25:
        return "Normal Metabolizer"
    else:
        return "Ultrarapid Metabolizer"


def infer_phenotype_from_alleles(gene: str, allele1: str, allele2: str) -> str:
    """
    Infer phenotype for non-CYP2D6 genes based on allele patterns.
    """
    # Define non-functional alleles for each gene
    non_functional = {
        "CYP2C19": ["*2", "*3", "*4", "*5", "*6", "*7", "*8"],
        "CYP2C9": ["*3", "*5", "*6", "*11", "*13"],
        "SLCO1B1": ["*5"],
        "TPMT": ["*2", "*3A", "*3B", "*3C"],
        "DPYD": ["*2A", "*13"],
    }
    
    decreased_function = {
        "CYP2C19": [],
        "CYP2C9": ["*2", "*8"],
        "SLCO1B1": [],
        "TPMT": [],
        "DPYD": ["HapB3", "c.1129-5923C>G"],
    }
    
    increased_function = {
        "CYP2C19": ["*17"],
    }
    
    gene_nonfunc = non_functional.get(gene, [])
    gene_decreased = decreased_function.get(gene, [])
    gene_increased = increased_function.get(gene, [])
    
    # Count functional status
    is_allele1_nonfunc = allele1 in gene_nonfunc
    is_allele2_nonfunc = allele2 in gene_nonfunc
    is_allele1_decreased = allele1 in gene_decreased
    is_allele2_decreased = allele2 in gene_decreased
    is_allele1_increased = allele1 in gene_increased
    is_allele2_increased = allele2 in gene_increased
    
    # Both non-functional = Poor Metabolizer
    if is_allele1_nonfunc and is_allele2_nonfunc:
        if gene == "SLCO1B1":
            return "Poor Function"
        return "Poor Metabolizer"
    
    # One non-functional = Intermediate
    if is_allele1_nonfunc or is_allele2_nonfunc:
        if gene == "SLCO1B1":
            return "Decreased Function"
        return "Intermediate Metabolizer"
    
    # Both decreased = Poor
    if is_allele1_decreased and is_allele2_decreased:
        if gene == "SLCO1B1":
            return "Poor Function"
        return "Poor Metabolizer"
    
    # One decreased = Intermediate
    if is_allele1_decreased or is_allele2_decreased:
        if gene == "SLCO1B1":
            return "Decreased Function"
        return "Intermediate Metabolizer"
    
    # Both increased = Ultrarapid
    if is_allele1_increased and is_allele2_increased:
        return "Ultrarapid Metabolizer"
    
    # One increased = Rapid
    if is_allele1_increased or is_allele2_increased:
        return "Rapid Metabolizer"
    
    # Default
    if gene == "SLCO1B1":
        return "Normal Function"
    return "Normal Metabolizer"


def get_activity_score(gene: str, diplotype: str) -> Optional[float]:
    """
    Get activity score for a diplotype (CYP2D6 only currently).
    """
    if gene != "CYP2D6":
        return None
    
    allele1, allele2 = parse_diplotype_string(diplotype)
    score1 = _RULES.cyp2d6_activity_scores.get(allele1, 1.0)
    score2 = _RULES.cyp2d6_activity_scores.get(allele2, 1.0)
    
    return round(score1 + score2, 2)


def phenotype_to_abbreviation(phenotype: str) -> str:
    """
    Convert full phenotype name to abbreviation.
    
    Args:
        phenotype: Full name like 'Poor Metabolizer'
    
    Returns:
        Abbreviation like 'PM'
    """
    return _RULES.phenotype_abbreviations.get(phenotype, "Unknown")


def get_all_phenotypes(diplotypes: Dict[str, str]) -> Dict[str, str]:
    """
    Get phenotypes for all genes in diplotype dict.
    
    Args:
        diplotypes: Dict of gene -> diplotype
    
    Returns:
        Dict of gene -> phenotype
    """
    phenotypes = {}
    for gene, diplotype in diplotypes.items():
        phenotypes[gene] = call_phenotype(gene, diplotype)
    return phenotypes
