import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main as app_module
from models.schemas import LLMGeneratedExplanation


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_VCF_DIR = ROOT / "sample_vcf"


async def _stub_generate_explanation(**kwargs):
    return LLMGeneratedExplanation(
        summary="Stub summary with variant context.",
        mechanism="Stub mechanism.",
        variant_impact="Stub variant impact.",
        clinical_context=kwargs.get("cpic_action", "Stub context."),
        patient_summary="Stub patient summary.",
    )


GOLDEN_CASES = [
    {
        "vcf": "patient_pm_cyp2d6.vcf",
        "drug": "CODEINE",
        "expected": {
            "risk_assessment.risk_label": "Toxic",
            "risk_assessment.severity": "critical",
            "pharmacogenomic_profile.phenotype": "PM",
            "pharmacogenomic_profile.primary_gene": "CYP2D6",
        },
    },
    {
        "vcf": "patient_pm_cyp2c19.vcf",
        "drug": "CLOPIDOGREL",
        "expected": {
            "risk_assessment.risk_label": "Ineffective",
            "risk_assessment.severity": "high",
            "pharmacogenomic_profile.phenotype": "PM",
        },
    },
    {
        "vcf": "patient_normal_all.vcf",
        "drug": "WARFARIN",
        "expected": {
            "risk_assessment.risk_label": "Safe",
            "risk_assessment.severity": "none",
            "pharmacogenomic_profile.phenotype": "NM",
        },
    },
]


class SnapshotConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.generate_explanation = _stub_generate_explanation
        cls.client = TestClient(app_module.app)

    def _get_nested(self, obj, path: str):
        cur = obj
        for key in path.split("."):
            cur = cur[key]
        return cur

    def _run_case(self, vcf_name: str, drug: str):
        with open(SAMPLE_VCF_DIR / vcf_name, "rb") as fh:
            response = self.client.post(
                "/analyze-strict",
                files={"vcf_file": (vcf_name, fh, "text/plain")},
                data={"drugs": drug},
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 1)
        return payload[0]

    def test_golden_cases_exact_field_match(self):
        for case in GOLDEN_CASES:
            with self.subTest(vcf=case["vcf"], drug=case["drug"]):
                result = self._run_case(case["vcf"], case["drug"])
                for field_path, expected_value in case["expected"].items():
                    actual = self._get_nested(result, field_path)
                    self.assertEqual(
                        actual,
                        expected_value,
                        f"Field {field_path}: expected '{expected_value}', got '{actual}'",
                    )


if __name__ == "__main__":
    unittest.main()

