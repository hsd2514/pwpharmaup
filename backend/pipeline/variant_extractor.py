"""
Stage 2: Variant Extractor
Converts flat list of variants into diplotype representation.
"""

import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

from models.schemas import VariantRecord, DetectedVariant
from pipeline.rules_loader import get_rules

logger = logging.getLogger(__name__)
_RULES = get_rules()


def determine_zygosity(genotype: str) -> str:
    """
    Determine zygosity from genotype string.
    0/0 = reference homozygous
    0/1 or 1/0 = heterozygous
    1/1 = alternate homozygous
    """
    if genotype in ["1/1", "1|1", "0/0", "0|0"]:
        return "homozygous"
    elif genotype in ["0/1", "1/0", "0|1", "1|0"]:
        return "heterozygous"
    else:
        return "heterozygous"  # Default


def is_reference_genotype(genotype: str) -> bool:
    """
    True when genotype indicates homozygous reference.
    """
    return genotype in ["0/0", "0|0"]


def extract_diplotypes(variants: List[VariantRecord]) -> Dict[str, str]:
    """
    Convert variant list to diplotype representation.
    
    Args:
        variants: List of VariantRecord from Stage 1
    
    Returns:
        Dict mapping gene -> diplotype (e.g., {'CYP2D6': '*4/*4'})
    """
    # Group variants by gene
    gene_variants: Dict[str, List[VariantRecord]] = defaultdict(list)
    
    for variant in variants:
        if variant.gene and variant.gene in _RULES.target_genes:
            gene_variants[variant.gene].append(variant)
    
    # Build diplotypes for each gene
    diplotypes: Dict[str, str] = {}
    
    for gene in _RULES.target_genes:
        if gene not in gene_variants or not gene_variants[gene]:
            # No variants detected - assume wild type
            diplotypes[gene] = _RULES.default_diplotype
            continue
        
        gene_vars = gene_variants[gene]
        star_alleles = []
        
        for var in gene_vars:
            if var.star_allele:
                # Reference calls and *1 do not contribute to variant diplotypes.
                if is_reference_genotype(var.genotype):
                    continue
                if var.star_allele == "*1":
                    continue
                zygosity = determine_zygosity(var.genotype)
                
                if zygosity == "homozygous":
                    # Homozygous for variant - both alleles
                    star_alleles.extend([var.star_allele, var.star_allele])
                else:
                    # Heterozygous - one variant allele
                    star_alleles.append(var.star_allele)
        
        # Build diplotype string
        if len(star_alleles) == 0:
            diplotypes[gene] = _RULES.default_diplotype
        elif len(star_alleles) == 1:
            # Single heterozygous variant - pair with *1
            diplotypes[gene] = f"*1/{star_alleles[0]}"
        elif len(star_alleles) >= 2:
            # Sort for consistent representation
            sorted_alleles = sorted(star_alleles[:2], key=lambda x: (x.replace("*", "").replace("x", "99"), x))
            diplotypes[gene] = f"{sorted_alleles[0]}/{sorted_alleles[1]}"
    
    logger.info(f"Extracted diplotypes: {diplotypes}")
    return diplotypes


def extract_detected_variants(variants: List[VariantRecord], gene: str) -> List[DetectedVariant]:
    """
    Extract detailed variant information for a specific gene.
    
    Args:
        variants: All parsed variants
        gene: Target gene to filter
    
    Returns:
        List of DetectedVariant objects
    """
    detected = []
    
    for var in variants:
        if var.gene == gene and var.star_allele:
            # Show only actionable/non-reference calls in detected variants.
            if is_reference_genotype(var.genotype):
                continue
            if var.star_allele == "*1":
                continue
            detected_var = DetectedVariant(
                rsid=var.rsid,
                gene=var.gene,
                star_allele=var.star_allele,
                zygosity=determine_zygosity(var.genotype),
                function=var.function,
                clinical_significance=get_clinical_significance(var.rsid, var.star_allele)
            )
            detected.append(detected_var)
    
    return detected


def get_clinical_significance(rsid: str, star_allele: str) -> Optional[str]:
    """
    Get clinical significance annotation for a variant.
    """
    # Look up in our rsID table
    if rsid in _RULES.rsid_to_star_allele:
        function = _RULES.rsid_to_star_allele[rsid].get("function", "")
        if "No function" in function:
            return "Loss-of-function variant"
        elif "Decreased" in function:
            return "Reduced function variant"
        elif "Increased" in function:
            return "Gain-of-function variant"
        else:
            return "Normal function variant"
    
    # Infer from star allele
    if star_allele in ["*1", "*1B"]:
        return "Wild-type allele"
    elif star_allele in ["*2A", "*3", "*4", "*5", "*6", "*13"]:
        return "Loss-of-function variant"
    elif star_allele == "*17":
        return "Gain-of-function variant"
    
    return "Variant of uncertain significance"


def calculate_annotation_completeness(variants: List[VariantRecord]) -> float:
    """
    Calculate how many variants have complete annotation.
    
    Returns:
        Float between 0.0 and 1.0
    """
    if not variants:
        return 1.0  # No variants = nothing to annotate
    
    annotated = sum(1 for v in variants if v.gene and v.star_allele)
    return round(annotated / len(variants), 2)


def get_primary_gene_for_drug(drug: str) -> Optional[str]:
    """
    Get the primary metabolizing gene for a drug.
    """
    drug_upper = drug.upper()
    return _RULES.supported_drugs.get(drug_upper)


def parse_diplotype(diplotype: str) -> Tuple[str, str]:
    """
    Parse diplotype string into two alleles.
    
    Args:
        diplotype: String like "*1/*4" or "*4/*4"
    
    Returns:
        Tuple of (allele1, allele2)
    """
    if "/" not in diplotype:
        return ("*1", "*1")
    
    parts = diplotype.split("/")
    if len(parts) != 2:
        return ("*1", "*1")
    
    allele1 = parts[0].strip()
    allele2 = parts[1].strip()
    
    # Ensure * prefix
    if not allele1.startswith("*"):
        allele1 = f"*{allele1}"
    if not allele2.startswith("*"):
        allele2 = f"*{allele2}"
    
    return (allele1, allele2)
