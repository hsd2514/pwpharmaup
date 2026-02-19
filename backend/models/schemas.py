"""
Pydantic models for PharmaGuard AI - Stage 7 Schema Validation.
These schemas enforce exact JSON output format required for evaluation.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal, List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLabel(str, Enum):
    """Allowed risk label values."""
    SAFE = "Safe"
    ADJUST_DOSAGE = "Adjust Dosage"
    TOXIC = "Toxic"
    INEFFECTIVE = "Ineffective"
    UNKNOWN = "Unknown"


class Severity(str, Enum):
    """Allowed severity values."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class PhenotypeLabel(str, Enum):
    """Allowed phenotype abbreviations."""
    PM = "PM"     # Poor Metabolizer
    IM = "IM"     # Intermediate Metabolizer
    NM = "NM"     # Normal Metabolizer
    RM = "RM"     # Rapid Metabolizer
    URM = "URM"   # Ultrarapid Metabolizer
    UNKNOWN = "Unknown"


# =============================================================================
# Stage 1 - VCF Parser Models
# =============================================================================

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VariantRecord(StrictModel):
    """Represents a single variant from VCF file."""
    chrom: str = Field(..., description="Chromosome")
    pos: int = Field(..., description="Position")
    rsid: str = Field(..., description="rsID identifier")
    ref: str = Field(..., description="Reference allele")
    alt: str = Field(..., description="Alternate allele")
    qual: float = Field(..., description="Quality score")
    gene: str = Field(..., description="Gene symbol from INFO")
    star_allele: str = Field(..., description="Star allele from INFO")
    genotype: str = Field(default="0/1", description="Genotype (0/0, 0/1, 1/1)")
    function: Optional[str] = Field(default=None, description="Functional annotation")


# =============================================================================
# Stage 5 - Risk Assessment Models
# =============================================================================

class RiskAssessment(StrictModel):
    """Risk assessment output from Stage 5."""
    risk_label: Literal["Safe", "Adjust Dosage", "Toxic", "Ineffective", "Unknown"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    severity: Literal["none", "low", "moderate", "high", "critical", "unknown"]
    
    @field_validator('confidence_score')
    @classmethod
    def round_confidence(cls, v):
        return round(v, 2)


# =============================================================================
# Stage 4 - PharmGKB Annotation Models
# =============================================================================

class DetectedVariant(StrictModel):
    """Individual variant detection details."""
    rsid: str
    gene: str
    star_allele: str
    zygosity: Literal["homozygous", "heterozygous"]
    function: Optional[str] = None
    clinical_significance: Optional[str] = None


class PharmacoGenomicProfile(StrictModel):
    """Pharmacogenomic profile for a patient-drug analysis."""
    primary_gene: str
    diplotype: str
    phenotype: Literal["PM", "IM", "NM", "RM", "URM", "Unknown"]
    activity_score: Optional[float] = None
    detected_variants: List[DetectedVariant]


# =============================================================================
# Clinical Recommendation Models
# =============================================================================

class ClinicalRecommendation(StrictModel):
    """Clinical recommendation output."""
    cpic_guideline: str
    action: str
    alternative_drugs: List[str] = Field(default_factory=list)
    monitoring: Optional[str] = None
    evidence_level: str = Field(default="1A")
    fda_requirement: Literal["Required", "Recommended", "Informative", "None"] = "Recommended"
    reference: Optional[str] = None


# =============================================================================
# Stage 6 - LLM Explanation Models
# =============================================================================

class LLMGeneratedExplanation(StrictModel):
    """LLM-generated clinical explanation."""
    summary: str = Field(..., description="2-3 sentence clinical summary")
    mechanism: str = Field(..., description="Biological mechanism explanation")
    variant_impact: str = Field(..., description="Impact of specific variants/diplotype")
    clinical_context: str = Field(..., description="What clinician should do")
    patient_summary: str = Field(..., description="Simple explanation for patient")


# =============================================================================
# Quality Metrics Models
# =============================================================================

class QualityMetrics(StrictModel):
    """Quality metrics for the analysis."""
    vcf_parsing_success: bool = True
    vcf_quality_score: float = Field(..., ge=0.0, le=100.0)
    variants_analyzed: int
    annotation_completeness: float = Field(..., ge=0.0, le=1.0)
    confidence_level: Literal["high", "medium", "low"]
    analysis_version: str = Field(default="1.0.0")


# =============================================================================
# Main Analysis Result Model
# =============================================================================

class AnalysisResult(StrictModel):
    """Complete analysis result - the main output schema."""
    patient_id: str
    drug: str
    timestamp: str
    risk_assessment: RiskAssessment
    pharmacogenomic_profile: PharmacoGenomicProfile
    clinical_recommendation: ClinicalRecommendation
    llm_generated_explanation: LLMGeneratedExplanation
    quality_metrics: QualityMetrics
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        # Accept ISO format timestamps
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            # If parsing fails, generate a valid timestamp
            v = datetime.utcnow().isoformat() + "Z"
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "patient_001",
                "drug": "CODEINE",
                "timestamp": "2026-02-19T12:00:00Z",
                "risk_assessment": {
                    "risk_label": "Toxic",
                    "confidence_score": 0.95,
                    "severity": "critical"
                },
                "pharmacogenomic_profile": {
                    "primary_gene": "CYP2D6",
                    "diplotype": "*4/*4",
                    "phenotype": "PM",
                    "detected_variants": []
                },
                "clinical_recommendation": {
                    "cpic_guideline": "CPIC Guideline for Codeine and CYP2D6",
                    "action": "Avoid codeine",
                    "alternative_drugs": ["morphine"],
                    "evidence_level": "1A",
                    "fda_requirement": "Required"
                },
                "llm_generated_explanation": {
                    "summary": "Patient is a CYP2D6 poor metabolizer.",
                    "mechanism": "CYP2D6 converts codeine to morphine.",
                    "variant_impact": "*4/*4 results in no enzyme activity.",
                    "clinical_context": "Avoid codeine, use alternatives.",
                    "patient_summary": "Your body cannot process this medication safely."
                },
                "quality_metrics": {
                    "vcf_quality_score": 95.0,
                    "variants_analyzed": 5,
                    "annotation_completeness": 1.0,
                    "confidence_level": "high",
                    "analysis_version": "1.0.0"
                }
            }
        }


# =============================================================================
# API Request/Response Models
# =============================================================================

class AnalyzeRequest(StrictModel):
    """Request model for /analyze endpoint when using JSON body."""
    patient_id: Optional[str] = Field(default=None)
    drugs: List[str] = Field(..., min_length=1)
    vcf_content: Optional[str] = Field(default=None, description="VCF file content as string")


class AnalyzeResponse(StrictModel):
    """Response model wrapping multiple analysis results."""
    success: bool
    results: List[AnalysisResult]
    errors: List[str] = Field(default_factory=list)


class HealthResponse(StrictModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: str


class SupportedDrugsResponse(StrictModel):
    """Supported drugs list response."""
    drugs: List[str]
    count: int


class DrugNormalizationResponse(StrictModel):
    """Drug name normalization response."""
    original: str
    normalized: str
    confidence: float
    is_supported: bool
