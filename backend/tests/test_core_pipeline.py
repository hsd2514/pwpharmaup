import unittest

from models.schemas import QualityMetrics
from pipeline.pypgx_engine import call_phenotype
from pipeline.risk_engine import assess_risk, get_cpic_action
from pipeline.variant_extractor import extract_detected_variants, extract_diplotypes
from pipeline.vcf_parser import parse_vcf_content


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
        self.assertEqual(risk.severity, "unknown")
        action = get_cpic_action("WARFARIN", "CYP2C9", "Ultrarapid Metabolizer")
        self.assertIn("No curated pharmacogenomic rule found", action)


if __name__ == "__main__":
    unittest.main()
