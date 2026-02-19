"""
PharmaGuard AI - FastAPI Backend
Pharmacogenomics Risk Analysis Platform

Main application entry point with all API routes.
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, UTC
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from backend/.env regardless of launch directory
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import pipeline modules
from pipeline.vcf_parser import (
    parse_vcf_content,
    validate_vcf_content,
    calculate_vcf_quality_score,
)
from pipeline.variant_extractor import (
    extract_diplotypes,
    extract_detected_variants,
    calculate_annotation_completeness,
)
from pipeline.pypgx_engine import (
    call_phenotype,
    phenotype_to_abbreviation,
)
from pipeline.pharmgkb_lookup import (
    normalize_drug_name,
    get_primary_gene,
    is_drug_supported,
    get_all_supported_drugs,
    lookup_annotation,
)
from pipeline.risk_engine import (
    assess_risk,
    build_clinical_recommendation,
    build_evidence_trace,
    calculate_confidence_score_v2,
    has_rule_match,
)
from pipeline.llm_explainer import (
    generate_explanation,
    get_explainer,
)
from pipeline.explanation_quality import score_explanation_quality
from pipeline.phenoconversion_detector import detect_phenoconversion
from pipeline.confidence_calibrator import IsotonicCalibrator
from pipeline.rules_loader import get_rules

# Import schemas
from models.schemas import (
    AnalysisResult,
    AnalyzeResponse,
    HealthResponse,
    SupportedDrugsResponse,
    DrugNormalizationResponse,
    RiskAssessment,
    PharmacoGenomicProfile,
    ClinicalRecommendation,
    LLMGeneratedExplanation,
    QualityMetrics,
    DetectedVariant,
)

_RULES = get_rules()
_CALIBRATOR = IsotonicCalibrator()


# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("PharmaGuard AI starting up...")
    yield
    # Cleanup
    explainer = get_explainer()
    await explainer.close()
    logger.info("PharmaGuard AI shutting down...")


# Create FastAPI application
app = FastAPI(
    title="PharmaGuard AI",
    description="Pharmacogenomics Risk Analysis Platform - Analyzes patient genetic variants to predict drug response and risk",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint for deployment monitoring.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )


# =============================================================================
# Supported Drugs Endpoint
# =============================================================================

@app.get("/supported-drugs", response_model=SupportedDrugsResponse, tags=["Reference"])
async def get_supported_drugs():
    """
    Get list of all supported drugs for analysis.
    """
    drugs = get_all_supported_drugs()
    return SupportedDrugsResponse(
        drugs=drugs,
        count=len(drugs)
    )


# =============================================================================
# Drug Normalization Endpoint
# =============================================================================

@app.post("/normalize-drug", response_model=DrugNormalizationResponse, tags=["Reference"])
async def normalize_drug(drug_name: str = Form(...)):
    """
    Normalize a drug name (handles brand names and variations).
    
    - **drug_name**: Input drug name (e.g., "Plavix", "tylenol 3")
    
    Returns normalized drug name and whether it's supported.
    """
    normalized = normalize_drug_name(drug_name)
    supported = is_drug_supported(normalized)
    
    # Simple confidence based on exact match
    confidence = 1.0 if drug_name.upper() == normalized else 0.85
    
    return DrugNormalizationResponse(
        original=drug_name,
        normalized=normalized,
        confidence=confidence,
        is_supported=supported
    )


@app.post("/evidence-trace", tags=["Reference"])
async def evidence_trace(
    drug: str = Form(..., description="Drug name"),
    gene: str = Form(..., description="Gene symbol, e.g. CYP2D6"),
    phenotype: str = Form(..., description="Full phenotype, e.g. Poor Metabolizer"),
    vcf_quality: Optional[float] = Form(default=None),
    annotation_completeness: Optional[float] = Form(default=None),
    diplotype: Optional[str] = Form(default=None),
    risk_label: Optional[str] = Form(default=None),
    detected_variant_count: Optional[int] = Form(default=None),
    gene_support_score: Optional[float] = Form(default=None),
    calibrated_confidence: Optional[float] = Form(default=None),
    rsid: Optional[str] = Form(default=None),
):
    """
    Deterministic provenance endpoint for clinical review and judging.
    Returns which rule/evidence rows were used for the decision path.
    """
    return build_evidence_trace(
        drug=drug,
        gene=gene,
        phenotype=phenotype,
        vcf_quality=vcf_quality,
        annotation_completeness=annotation_completeness,
        diplotype=diplotype,
        risk_label=risk_label,
        detected_variant_count=detected_variant_count,
        gene_support_score=gene_support_score,
        calibrated_confidence=calibrated_confidence,
        rsid=rsid,
    )


@app.post("/explanation-quality", tags=["Reference"])
async def explanation_quality(
    drug: str = Form(...),
    gene: str = Form(...),
    summary: str = Form(...),
    mechanism: str = Form(...),
    variant_impact: str = Form(...),
    clinical_context: str = Form(...),
    patient_summary: str = Form(...),
):
    """
    Deterministic explanation quality scoring endpoint.
    """
    explanation = LLMGeneratedExplanation(
        summary=summary,
        mechanism=mechanism,
        variant_impact=variant_impact,
        clinical_context=clinical_context,
        patient_summary=patient_summary,
    )
    return score_explanation_quality(
        explanation=explanation,
        gene=gene,
        drug=drug,
        detected_variants=[],
        cpic_action=clinical_context,
    )


@app.post("/phenoconversion-check", tags=["Reference"])
async def phenoconversion_check(
    gene: str = Form(...),
    genetic_phenotype: str = Form(..., description="PM|IM|NM|RM|URM|Unknown"),
    concurrent_medications: str = Form(default=""),
):
    meds = [m.strip() for m in (concurrent_medications or "").split(",") if m.strip()]
    return detect_phenoconversion(
        gene=gene,
        genetic_phenotype_abbrev=genetic_phenotype,
        concurrent_medications=meds,
    )


# =============================================================================
# Sample VCF Download Endpoint
# =============================================================================

@app.get("/sample-vcf/{phenotype_type}", tags=["Reference"])
async def get_sample_vcf(phenotype_type: str):
    """
    Download a sample VCF file for testing.
    
    - **phenotype_type**: One of: pm_cyp2d6, pm_cyp2c19, im_cyp2c9, dpyd_im, normal_all
    """
    valid_types = ["pm_cyp2d6", "pm_cyp2c19", "im_cyp2c9", "dpyd_im", "normal_all"]
    
    if phenotype_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phenotype type. Must be one of: {valid_types}"
        )
    
    # Return sample VCF content
    sample_vcfs = {
        "pm_cyp2d6": generate_sample_vcf_cyp2d6_pm(),
        "pm_cyp2c19": generate_sample_vcf_cyp2c19_pm(),
        "im_cyp2c9": generate_sample_vcf_cyp2c9_im(),
        "dpyd_im": generate_sample_vcf_dpyd_im(),
        "normal_all": generate_sample_vcf_normal(),
    }
    
    return JSONResponse(
        content={"vcf_content": sample_vcfs[phenotype_type]},
        media_type="application/json"
    )


# =============================================================================
# Main Analysis Endpoint
# =============================================================================

@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_vcf(
    vcf_file: UploadFile = File(..., description="VCF file containing genetic variants"),
    drugs: str = Form(..., description="Comma-separated list of drug names to analyze"),
    patient_id: Optional[str] = Form(default=None, description="Optional patient identifier"),
    concurrent_medications: Optional[str] = Form(
        default=None, description="Optional comma-separated concurrent medications"
    ),
):
    """
    Analyze a VCF file for pharmacogenomic drug risks.
    
    This is the main endpoint that orchestrates the complete 7-stage pipeline:
    1. VCF Parsing
    2. Variant Extraction
    3. Phenotype Calling
    4. PharmGKB Lookup
    5. Risk Assessment
    6. LLM Explanation
    7. Schema Validation
    
    - **vcf_file**: VCF file upload (max 5MB)
    - **drugs**: Comma-separated drug names (e.g., "codeine,warfarin")
    - **patient_id**: Optional patient identifier
    
    Returns analysis results for each drug.
    """
    response = await _run_analysis(vcf_file, drugs, patient_id, concurrent_medications)
    return response


@app.post("/analyze-strict", response_model=List[AnalysisResult], tags=["Analysis"])
async def analyze_vcf_strict(
    vcf_file: UploadFile = File(..., description="VCF file containing genetic variants"),
    drugs: str = Form(..., description="Comma-separated list of drug names to analyze"),
    patient_id: Optional[str] = Form(default=None, description="Optional patient identifier"),
    concurrent_medications: Optional[str] = Form(
        default=None, description="Optional comma-separated concurrent medications"
    ),
):
    """
    Strict evaluator-friendly endpoint.
    Returns only AnalysisResult[] and fails if any per-drug analysis error occurs.
    """
    response = await _run_analysis(vcf_file, drugs, patient_id, concurrent_medications)
    if response.errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Strict analysis failed for one or more drugs", "errors": response.errors},
        )
    return response.results


async def _run_analysis(
    vcf_file: UploadFile,
    drugs: str,
    patient_id: Optional[str],
    concurrent_medications: Optional[str],
) -> AnalyzeResponse:
    errors = []
    results = []

    if not patient_id:
        patient_id = f"patient_{uuid.uuid4().hex[:8]}"

    raw_drugs = [d.strip() for d in drugs.split(",") if d.strip()]
    seen = set()
    drug_list = []
    for raw in raw_drugs:
        canonical = normalize_drug_name(raw)
        if canonical in seen:
            continue
        seen.add(canonical)
        drug_list.append(canonical)
    concurrent_meds = [m.strip() for m in (concurrent_medications or "").split(",") if m.strip()]
    if not drug_list:
        raise HTTPException(status_code=400, detail="No drugs specified")

    max_file_size = 5 * 1024 * 1024
    content = await vcf_file.read()
    if len(content) > max_file_size:
        raise HTTPException(status_code=400, detail="VCF file exceeds 5MB limit")

    try:
        vcf_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid VCF file encoding")

    is_valid, validation_msg = validate_vcf_content(vcf_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid VCF: {validation_msg}")

    try:
        variants = parse_vcf_content(vcf_content)
    except Exception as e:
        logger.error(f"VCF parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"VCF parsing error: {str(e)}")

    if not variants:
        logger.warning("No variants found in VCF, using default *1/*1 for all genes")

    vcf_quality = calculate_vcf_quality_score(variants)
    annotation_completeness = calculate_annotation_completeness(variants)
    diplotypes = extract_diplotypes(variants)

    for drug in drug_list:
        try:
            result = await analyze_single_drug(
                drug=drug,
                patient_id=patient_id,
                variants=variants,
                diplotypes=diplotypes,
                vcf_quality=vcf_quality,
                annotation_completeness=annotation_completeness,
                concurrent_medications=concurrent_meds,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error analyzing {drug}: {e}")
            errors.append(f"Error analyzing {drug}: {str(e)}")

    return AnalyzeResponse(success=len(results) > 0 and not errors, results=results, errors=errors)


async def analyze_single_drug(
    drug: str,
    patient_id: str,
    variants: list,
    diplotypes: dict,
    vcf_quality: float,
    annotation_completeness: float,
    concurrent_medications: list[str],
) -> AnalysisResult:
    """
    Analyze a single drug against patient variants.
    """
    # Normalize drug name
    normalized_drug = normalize_drug_name(drug)
    
    # Get primary gene for this drug
    primary_gene = get_primary_gene(normalized_drug)
    
    if not primary_gene:
        raise ValueError(f"Drug '{drug}' is not supported")
    
    # Get diplotype for this gene
    diplotype = diplotypes.get(primary_gene, "*1/*1")
    
    # Stage 3: Call phenotype
    phenotype_full = call_phenotype(primary_gene, diplotype)
    phenotype_abbrev = phenotype_to_abbreviation(phenotype_full)
    
    # Stage 2b: Extract detected variants for this gene
    detected_variants = extract_detected_variants(variants, primary_gene)
    gene_support_score = 1.0 if len(detected_variants) > 0 else 0.7
    
    # Stage 4: PharmGKB lookup
    annotation = lookup_annotation(primary_gene, normalized_drug)
    
    phenoconversion = detect_phenoconversion(
        gene=primary_gene,
        genetic_phenotype_abbrev=phenotype_abbrev,
        concurrent_medications=concurrent_medications,
    )
    if phenoconversion.get("phenoconversion_risk"):
        effective_phenotype_full = phenoconversion.get("functional_phenotype_full", phenotype_full)
    else:
        effective_phenotype_full = phenotype_full

    # Stage 5: Risk assessment (uses functional phenotype if phenoconversion is detected)
    risk_assessment = assess_risk(normalized_drug, primary_gene, effective_phenotype_full)
    
    # Build clinical recommendation (phenoconversion-aware override text included when applicable)
    clinical_rec = build_clinical_recommendation(
        normalized_drug,
        primary_gene,
        effective_phenotype_full,
        phenoconversion=phenoconversion,
        genetic_phenotype=phenotype_abbrev,
    )
    cpic_action = clinical_rec.action

    # Calibrated deterministic confidence scoring (component-based).
    evidence_level = annotation.evidence_level if annotation else "4"
    raw_confidence = calculate_confidence_score_v2(
        evidence_level=evidence_level,
        vcf_quality=vcf_quality,
        annotation_completeness=annotation_completeness,
        phenotype=effective_phenotype_full,
        diplotype=diplotype,
        risk_label=risk_assessment.risk_label,
        rule_match=has_rule_match(normalized_drug, primary_gene, effective_phenotype_full),
        detected_variant_count=len(detected_variants),
        gene_support_score=gene_support_score,
    )
    penalty = float(phenoconversion.get("confidence_penalty", 0.0))
    penalized_confidence = max(0.0, raw_confidence - penalty)
    calibrated_confidence = _CALIBRATOR.calibrate(penalized_confidence)
    risk_assessment = RiskAssessment(
        risk_label=risk_assessment.risk_label,
        confidence_score=calibrated_confidence,
        severity=risk_assessment.severity,
    )
    
    # Stage 6: Generate LLM explanation
    explanation = await generate_explanation(
        drug=normalized_drug,
        gene=primary_gene,
        diplotype=diplotype,
        phenotype=effective_phenotype_full,
        risk_assessment=risk_assessment,
        detected_variants=detected_variants,
        cpic_action=cpic_action
    )
    explanation_quality = score_explanation_quality(
        explanation=explanation,
        gene=primary_gene,
        drug=normalized_drug,
        detected_variants=detected_variants,
        cpic_action=cpic_action,
    )
    logger.info(
        "Explanation quality score for %s/%s: %s (fails=%s)",
        normalized_drug,
        primary_gene,
        explanation_quality.get("explanation_quality_score"),
        ",".join(explanation_quality.get("quality_fail_reasons", [])),
    )
    
    # Build pharmacogenomic profile
    pgx_profile = PharmacoGenomicProfile(
        primary_gene=primary_gene,
        diplotype=diplotype,
        phenotype=phenotype_abbrev,
        detected_variants=detected_variants
    )
    
    # Build quality metrics
    confidence_level = "high" if risk_assessment.confidence_score >= 0.85 else (
        "medium" if risk_assessment.confidence_score >= 0.70 else "low"
    )
    
    quality_metrics = QualityMetrics(
        vcf_parsing_success=True,
        vcf_quality_score=vcf_quality,
        variants_analyzed=len(variants),
        annotation_completeness=annotation_completeness,
        confidence_level=confidence_level,
        analysis_version="1.0.0",
        clinical_rules_version=_RULES.rules_version,
    )
    
    # Stage 7: Build and validate final result
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    
    result = AnalysisResult(
        patient_id=patient_id,
        drug=normalized_drug,
        timestamp=timestamp,
        risk_assessment=risk_assessment,
        pharmacogenomic_profile=pgx_profile,
        clinical_recommendation=clinical_rec,
        llm_generated_explanation=explanation,
        quality_metrics=quality_metrics
    )
    
    return result


@app.post("/cohort-summary", tags=["Analysis"])
async def cohort_summary(results: List[AnalysisResult]):
    """
    Aggregate multiple analysis results into cohort-level risk distribution.
    """
    matrix = {}
    high_risk_patients = []
    for item in results:
        drug = item.drug
        risk = item.risk_assessment.risk_label
        if drug not in matrix:
            matrix[drug] = {
                "Safe": 0,
                "Adjust Dosage": 0,
                "Toxic": 0,
                "Ineffective": 0,
                "Unknown": 0,
            }
        matrix[drug][risk] += 1
        if item.risk_assessment.severity in {"critical", "high"}:
            high_risk_patients.append(item.patient_id)

    return {
        "cohort_size": len(results),
        "risk_matrix": matrix,
        "high_risk_patients": sorted(set(high_risk_patients)),
        "high_risk_count": len(set(high_risk_patients)),
        "alert": f"{len(set(high_risk_patients))} patients require immediate clinical review",
    }


# =============================================================================
# Sample VCF Generators
# =============================================================================

def generate_sample_vcf_cyp2d6_pm():
    """Generate sample VCF for CYP2D6 Poor Metabolizer (*4/*4)."""
    return """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
##INFO=<ID=STAR,Number=1,Type=String,Description="Star allele">
##INFO=<ID=RS,Number=1,Type=String,Description="rsID">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth">
##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype quality">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
22	42522613	rs3892097	G	A	100	PASS	GENE=CYP2D6;STAR=*4;RS=rs3892097	GT:DP:GQ	1/1:45:99
"""


def generate_sample_vcf_cyp2c19_pm():
    """Generate sample VCF for CYP2C19 Poor Metabolizer (*2/*2)."""
    return """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
##INFO=<ID=STAR,Number=1,Type=String,Description="Star allele">
##INFO=<ID=RS,Number=1,Type=String,Description="rsID">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
10	96541616	rs4244285	G	A	100	PASS	GENE=CYP2C19;STAR=*2;RS=rs4244285	GT:DP:GQ	1/1:50:99
"""


def generate_sample_vcf_cyp2c9_im():
    """Generate sample VCF for CYP2C9 Intermediate Metabolizer (*1/*3)."""
    return """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
##INFO=<ID=STAR,Number=1,Type=String,Description="Star allele">
##INFO=<ID=RS,Number=1,Type=String,Description="rsID">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
10	96702047	rs1057910	A	C	98	PASS	GENE=CYP2C9;STAR=*3;RS=rs1057910	GT:DP:GQ	0/1:42:95
"""


def generate_sample_vcf_dpyd_im():
    """Generate sample VCF for DPYD Intermediate Metabolizer (*1/*2A)."""
    return """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
##INFO=<ID=STAR,Number=1,Type=String,Description="Star allele">
##INFO=<ID=RS,Number=1,Type=String,Description="rsID">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
1	97915614	rs3918290	C	T	100	PASS	GENE=DPYD;STAR=*2A;RS=rs3918290	GT:DP:GQ	0/1:55:99
"""


def generate_sample_vcf_normal():
    """Generate sample VCF with all normal/wild-type alleles."""
    return """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
##INFO=<ID=STAR,Number=1,Type=String,Description="Star allele">
##INFO=<ID=RS,Number=1,Type=String,Description="rsID">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
22	42522613	rs16947	C	T	95	PASS	GENE=CYP2D6;STAR=*2;RS=rs16947	GT:DP:GQ	0/0:40:90
10	96541616	rs12248560	C	T	92	PASS	GENE=CYP2C19;STAR=*1;RS=rs12248560	GT:DP:GQ	0/0:38:88
"""


# =============================================================================
# Run Application
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "development") == "development"
    )
