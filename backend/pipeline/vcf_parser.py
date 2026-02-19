"""
Stage 1: VCF File Parser
Parses VCF (Variant Call Format) files and extracts variant information.
"""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

from models.schemas import VariantRecord
from models.constants import RSID_TO_STAR_ALLELE, TARGET_GENES

logger = logging.getLogger(__name__)


class VCFParseError(Exception):
    """Raised when VCF parsing fails."""
    pass


def parse_info_field(info: str) -> dict:
    """
    Parse INFO column from VCF.
    Format: KEY1=VAL1;KEY2=VAL2;...
    """
    result = {}
    if info == "." or not info:
        return result
    
    for item in info.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
        else:
            # Flag field (no value)
            result[item.strip()] = True
    
    return result


def parse_format_genotype(format_str: str, sample_str: str) -> str:
    """
    Extract genotype from FORMAT and sample columns.
    FORMAT: GT:DP:GQ:...
    SAMPLE: 0/1:30:99:...
    """
    if not format_str or not sample_str:
        return "0/1"  # Default heterozygous
    
    format_fields = format_str.split(":")
    sample_values = sample_str.split(":")
    
    try:
        gt_idx = format_fields.index("GT")
        genotype = sample_values[gt_idx]
        # Normalize phased (|) to unphased (/)
        genotype = genotype.replace("|", "/")
        return genotype
    except (ValueError, IndexError):
        return "0/1"


def infer_star_allele_from_rsid(rsid: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Infer gene and star allele from rsID using lookup table.
    Returns: (gene, star_allele, function)
    """
    if rsid in RSID_TO_STAR_ALLELE:
        info = RSID_TO_STAR_ALLELE[rsid]
        return info["gene"], info["star"], info.get("function")
    return None, None, None


def parse_vcf_content(vcf_content: str, min_qual: float = 20.0) -> List[VariantRecord]:
    """
    Parse VCF file content and return list of VariantRecord objects.
    
    Args:
        vcf_content: Raw VCF file content as string
        min_qual: Minimum quality score to accept variant (default 20)
    
    Returns:
        List of VariantRecord objects
    """
    variants = []
    lines = vcf_content.strip().split("\n")
    
    header_cols = None
    line_number = 0
    
    for line in lines:
        line_number += 1
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Skip metadata headers (##)
        if line.startswith("##"):
            continue
            
        # Parse column header line (#CHROM)
        if line.startswith("#CHROM"):
            header_cols = line[1:].split("\t")  # Remove # and split
            continue
        
        # Skip if we haven't seen header yet
        if header_cols is None:
            continue
            
        # Parse data line
        try:
            fields = line.split("\t")
            
            if len(fields) < 8:
                logger.warning(f"Line {line_number}: Insufficient columns, skipping")
                continue
            
            # Extract core fields
            chrom = fields[0]
            pos = int(fields[1])
            rsid = fields[2] if fields[2] != "." else ""
            ref = fields[3]
            alt = fields[4]
            
            # Parse quality score
            try:
                qual = float(fields[5]) if fields[5] != "." else 0.0
            except ValueError:
                qual = 0.0
            
            # Quality filter: skip low-quality and unknown-quality variants
            if qual < min_qual:
                logger.debug(f"Line {line_number}: Quality {qual} below threshold {min_qual}, skipping")
                continue
            
            # Parse INFO field
            info = parse_info_field(fields[7])
            
            # Extract gene and star allele from INFO
            gene = info.get("GENE", "")
            star_allele = info.get("STAR", "")
            rs_from_info = info.get("RS", rsid)
            
            # If rsID not in ID column, try from INFO
            if not rsid and rs_from_info:
                rsid = rs_from_info
            
            # Try to infer gene/star from rsID if not in INFO
            if rsid and (not gene or not star_allele):
                inferred_gene, inferred_star, inferred_func = infer_star_allele_from_rsid(rsid)
                if inferred_gene and not gene:
                    gene = inferred_gene
                if inferred_star and not star_allele:
                    star_allele = inferred_star
            
            # Only include variants for target genes
            if gene and gene not in TARGET_GENES:
                continue
            
            # Parse genotype from FORMAT/SAMPLE columns
            genotype = "0/1"  # Default
            if len(fields) >= 10:
                genotype = parse_format_genotype(fields[8], fields[9])
            
            # Create VariantRecord
            variant = VariantRecord(
                chrom=chrom,
                pos=pos,
                rsid=rsid if rsid else f"chr{chrom}:{pos}",
                ref=ref,
                alt=alt,
                qual=qual,
                gene=gene,
                star_allele=star_allele,
                genotype=genotype,
                function=RSID_TO_STAR_ALLELE.get(rsid, {}).get("function")
            )
            
            variants.append(variant)
            
        except Exception as e:
            logger.warning(f"Line {line_number}: Parse error - {str(e)}, skipping")
            continue
    
    logger.info(f"Parsed {len(variants)} variants from VCF")
    return variants


def parse_vcf_file(file_path: str, min_qual: float = 20.0) -> List[VariantRecord]:
    """
    Parse VCF file from disk.
    
    Args:
        file_path: Path to VCF file
        min_qual: Minimum quality score
    
    Returns:
        List of VariantRecord objects
    """
    with open(file_path, 'r') as f:
        content = f.read()
    return parse_vcf_content(content, min_qual)


def validate_vcf_content(vcf_content: str) -> Tuple[bool, str]:
    """
    Validate VCF content format.
    
    Returns:
        (is_valid, error_message)
    """
    lines = vcf_content.strip().split("\n")
    
    # Check for file format header
    has_format = any(line.startswith("##fileformat=VCF") for line in lines[:10])
    
    # Check for column header
    has_header = any(line.startswith("#CHROM") for line in lines)
    
    # Check for at least one data line
    data_lines = [l for l in lines if l and not l.startswith("#")]
    has_data = len(data_lines) > 0
    
    if not has_header:
        return False, "Missing #CHROM header line"
    
    if not has_data:
        return False, "No variant data found"
    
    return True, "Valid VCF format"


def calculate_vcf_quality_score(variants: List[VariantRecord]) -> float:
    """
    Calculate overall VCF quality score (0-100).
    """
    if not variants:
        return 0.0
    
    # Average quality of variants
    avg_qual = sum(v.qual for v in variants) / len(variants)
    
    # Normalize to 0-100 (assuming QUAL typically 0-100+)
    normalized = min(100.0, avg_qual)
    
    # Bonus for having gene annotations
    annotated = sum(1 for v in variants if v.gene and v.star_allele)
    annotation_rate = annotated / len(variants) if variants else 0
    
    # Weighted score
    score = (normalized * 0.7) + (annotation_rate * 30)
    
    return round(score, 1)
