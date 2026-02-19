import unittest

from models.schemas import QualityMetrics
from pipeline.pypgx_engine import call_phenotype
from pipeline.risk_engine import (
    assess_risk,
    get_cpic_action,
    calculate_confidence_components,
    calculate_confidence_score_v2,
)
from pipeline.variant_extractor import extract_detected_variants, extract_diplotypes
from pipeline.vcf_parser import parse_vcf_content
from pipeline.explanation_quality import score_explanation_quality
from models.schemas import LLMGeneratedExplanation, DetectedVariant
from pipeline.confidence_calibrator import IsotonicCalibrator


class CorePipelineTests(unittest.TestCase):
    def test_vcf_parser_skips_low_and_unknown_quality(self):
        vcf = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE
22\t42522613\trs3892097\tG\tA\t.\tPASS\tGENE=CYP2D6;STAR=*4;RS=rs3892097\tGT:DP:GQ\t1/1:40:99
22\t42522614\trs3892097\tG\tA\t10\tPASS\tGENE=CYP2D6;STAR=*4;RS=rs3892097\tGT:DP:GQ\t1/1:40:99
22\t42522615\trs3892097\tG\tA\t99\tPASS\tGENE=CYP2D6;STAR=*4;RS=rs3892097\tGT:DP:GQ\t1/1:40:99
"""
        variants = parse_vcf_content(vcf)
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].qual, 99.0)

    def test_reference_calls_do_not_create_actionable_variants(self):
        vcf = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE
22\t42522613\trs16947\tC\tT\t95\tPASS\tGENE=CYP2D6;STAR=*1;RS=rs16947\tGT:DP:GQ\t0/0:40:90
"""
        variants = parse_vcf_content(vcf)
        diplotypes = extract_diplotypes(variants)
        detected = extract_detected_variants(variants, "CYP2D6")
        self.assertEqual(diplotypes["CYP2D6"], "*1/*1")
        self.assertEqual(detected, [])

    def test_pm_codeine_pathway_maps_to_toxic(self):
        vcf = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE
22\t42522613\trs3892097\tG\tA\t100\tPASS\tGENE=CYP2D6;STAR=*4;RS=rs3892097\tGT:DP:GQ\t1/1:45:99
"""
        variants = parse_vcf_content(vcf)
        diplotypes = extract_diplotypes(variants)
        self.assertEqual(diplotypes["CYP2D6"], "*4/*4")

        phenotype = call_phenotype("CYP2D6", diplotypes["CYP2D6"])
        self.assertEqual(phenotype, "Poor Metabolizer")

        risk = assess_risk("CODEINE", "CYP2D6", phenotype)
        self.assertEqual(risk.risk_label, "Toxic")
        self.assertEqual(risk.severity, "critical")

    def test_quality_metrics_schema_has_parsing_success(self):
        qm = QualityMetrics(
            vcf_quality_score=98.0,
            variants_analyzed=1,
            annotation_completeness=1.0,
            confidence_level="high",
            analysis_version="1.0.0",
        )
        self.assertTrue(qm.vcf_parsing_success)

    def test_unknown_combination_has_explicit_unknown_action(self):
        risk = assess_risk("WARFARIN", "CYP2C9", "Ultrarapid Metabolizer")
        self.assertEqual(risk.risk_label, "Unknown")
        self.assertEqual(risk.severity, "low")
        action = get_cpic_action("WARFARIN", "CYP2C9", "Ultrarapid Metabolizer")
        self.assertIn("No curated pharmacogenomic rule found", action)

    def test_confidence_components_are_bounded(self):
        comp = calculate_confidence_components(
            evidence_level="1A",
            vcf_quality=96.0,
            annotation_completeness=1.0,
            phenotype="Poor Metabolizer",
            diplotype="*4/*4",
            risk_label="Toxic",
        )
        self.assertEqual(set(comp.keys()), {"evidence", "genotype", "phenotype", "rule_coverage"})
        for value in comp.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_unknown_confidence_is_capped(self):
        score = calculate_confidence_score_v2(
            evidence_level="1A",
            vcf_quality=100.0,
            annotation_completeness=1.0,
            phenotype="Unknown",
            diplotype="*1/*1",
            risk_label="Unknown",
        )
        self.assertLessEqual(score, 0.69)

    def test_explanation_quality_scoring(self):
        explanation = LLMGeneratedExplanation(
            summary="Patient has CYP2D6 *4/*4 with rs3892097 and high toxicity risk for CODEINE.",
            mechanism="CYP2D6 converts codeine to morphine; loss of function alters exposure.",
            variant_impact="*4/*4 indicates no function activity.",
            clinical_context="Avoid codeine and use alternatives; monitor clinically.",
            patient_summary="Your genes show this medicine is unsafe. Ask for an alternative.",
        )
        variants = [
            DetectedVariant(
                rsid="rs3892097",
                gene="CYP2D6",
                star_allele="*4",
                zygosity="homozygous",
                function="No function",
                clinical_significance="Loss-of-function variant",
            )
        ]
        out = score_explanation_quality(
            explanation=explanation,
            gene="CYP2D6",
            drug="CODEINE",
            detected_variants=variants,
            cpic_action="Avoid codeine.",
        )
        self.assertGreaterEqual(out["explanation_quality_score"], 0.8)
        self.assertTrue(out["passed"])

    def test_confidence_calibrator_maps_bins(self):
        calibrator = IsotonicCalibrator()
        self.assertEqual(calibrator.calibrate(0.95), 0.95)
        self.assertEqual(calibrator.calibrate(0.85), 0.87)
        self.assertEqual(calibrator.calibrate(0.35), 0.3)


if __name__ == "__main__":
    unittest.main()
