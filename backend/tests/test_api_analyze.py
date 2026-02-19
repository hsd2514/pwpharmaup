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


class AnalyzeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Avoid external LLM calls in test suite.
        app_module.generate_explanation = _stub_generate_explanation
        cls.client = TestClient(app_module.app)

    def _post_analyze(self, sample_filename: str, drugs: str):
        file_path = SAMPLE_VCF_DIR / sample_filename
        with open(file_path, "rb") as fh:
            files = {"vcf_file": (sample_filename, fh, "text/plain")}
            data = {"drugs": drugs}
            response = self.client.post("/analyze", files=files, data=data)
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload.get("success"), payload)
        self.assertIn("results", payload)
        self.assertGreaterEqual(len(payload["results"]), 1)
        return payload

    def _post_analyze_strict(self, sample_filename: str, drugs: str):
        file_path = SAMPLE_VCF_DIR / sample_filename
        with open(file_path, "rb") as fh:
            files = {"vcf_file": (sample_filename, fh, "text/plain")}
            data = {"drugs": drugs}
            response = self.client.post("/analyze-strict", files=files, data=data)
        return response

    def test_analyze_contract_shape(self):
        payload = self._post_analyze("patient_pm_cyp2d6.vcf", "CODEINE")
        result = payload["results"][0]

        self.assertIn("patient_id", result)
        self.assertIn("drug", result)
        self.assertIn("timestamp", result)
        self.assertIn("risk_assessment", result)
        self.assertIn("pharmacogenomic_profile", result)
        self.assertIn("clinical_recommendation", result)
        self.assertIn("llm_generated_explanation", result)
        self.assertIn("quality_metrics", result)

        self.assertIn("risk_label", result["risk_assessment"])
        self.assertIn("confidence_score", result["risk_assessment"])
        self.assertIn("severity", result["risk_assessment"])

        pgx = result["pharmacogenomic_profile"]
        self.assertIn("primary_gene", pgx)
        self.assertIn("diplotype", pgx)
        self.assertIn("phenotype", pgx)
        self.assertIn("detected_variants", pgx)

        quality = result["quality_metrics"]
        self.assertIn("vcf_parsing_success", quality)
        self.assertTrue(quality["vcf_parsing_success"])

    def test_golden_codeine_pm(self):
        payload = self._post_analyze("patient_pm_cyp2d6.vcf", "CODEINE")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "CODEINE")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "CYP2D6")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*4/*4")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Toxic")

    def test_golden_clopidogrel_pm(self):
        payload = self._post_analyze("patient_pm_cyp2c19.vcf", "CLOPIDOGREL")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "CLOPIDOGREL")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "CYP2C19")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*2/*2")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Ineffective")

    def test_golden_warfarin_im(self):
        payload = self._post_analyze("patient_im_cyp2c9.vcf", "WARFARIN")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "WARFARIN")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "CYP2C9")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*1/*3")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Adjust Dosage")

    def test_golden_dpyd_im(self):
        payload = self._post_analyze("patient_dpyd_im.vcf", "FLUOROURACIL")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "FLUOROURACIL")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "DPYD")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*1/*2A")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Adjust Dosage")

    def test_analyze_strict_returns_plain_result_list(self):
        response = self._post_analyze_strict("patient_pm_cyp2d6.vcf", "CODEINE")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["drug"], "CODEINE")

    def test_analyze_strict_fails_if_any_drug_errors(self):
        response = self._post_analyze_strict("patient_pm_cyp2d6.vcf", "CODEINE,NOTADRUG")
        self.assertEqual(response.status_code, 422, response.text)
        body = response.json()
        self.assertIn("detail", body)


if __name__ == "__main__":
    unittest.main()
