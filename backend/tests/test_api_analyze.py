import unittest
from pathlib import Path
import json

from fastapi.testclient import TestClient

import main as app_module
from models.schemas import LLMGeneratedExplanation


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_VCF_DIR = ROOT / "sample_vcf"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


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

    def _post_analyze(self, sample_filename: str, drugs: str, concurrent_medications: str = ""):
        file_path = SAMPLE_VCF_DIR / sample_filename
        with open(file_path, "rb") as fh:
            files = {"vcf_file": (sample_filename, fh, "text/plain")}
            data = {"drugs": drugs}
            if concurrent_medications:
                data["concurrent_medications"] = concurrent_medications
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

    def test_golden_dpyd_pm(self):
        payload = self._post_analyze("patient_pm_dpyd.vcf", "FLUOROURACIL")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "FLUOROURACIL")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "DPYD")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*2A/*2A")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Toxic")

    def test_golden_slco1b1_im(self):
        payload = self._post_analyze("patient_im_slco1b1.vcf", "SIMVASTATIN")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "SIMVASTATIN")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "SLCO1B1")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*1/*5")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Adjust Dosage")

    def test_golden_cyp2c19_rm(self):
        payload = self._post_analyze("patient_rm_cyp2c19.vcf", "CLOPIDOGREL")
        result = payload["results"][0]
        self.assertEqual(result["drug"], "CLOPIDOGREL")
        self.assertEqual(result["pharmacogenomic_profile"]["primary_gene"], "CYP2C19")
        self.assertEqual(result["pharmacogenomic_profile"]["diplotype"], "*1/*17")
        self.assertEqual(result["risk_assessment"]["risk_label"], "Adjust Dosage")

    def test_alias_drugs_are_normalized_and_deduplicated(self):
        payload = self._post_analyze(
            "patient_normal_all.vcf",
            "FLUOROURACIL,5-FU,5-FLUOROURACIL",
        )
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["drug"], "FLUOROURACIL")

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

    def test_evidence_trace_contract(self):
        response = self.client.post(
            "/evidence-trace",
            data={
                "drug": "CODEINE",
                "gene": "CYP2D6",
                "phenotype": "Poor Metabolizer",
                "vcf_quality": "96",
                "annotation_completeness": "1",
                "diplotype": "*4/*4",
                "risk_label": "Toxic",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn("rules_version", body)
        self.assertIn("rule_key", body)
        self.assertIn("rule_match", body)
        self.assertIn("risk_rule", body)
        self.assertIn("pharmgkb_annotation", body)
        self.assertIn("confidence_components", body)
        self.assertIn("confidence_score_v2", body)
        self.assertIn("decision_chain", body)
        self.assertGreaterEqual(body.get("total_steps", 0), 6)
        self.assertTrue(body.get("all_sources_cited"))

    def test_analyze_strict_snapshot_codeine_pm(self):
        response = self._post_analyze_strict("patient_pm_cyp2d6.vcf", "CODEINE")
        self.assertEqual(response.status_code, 200, response.text)
        actual = response.json()
        self.assertEqual(len(actual), 1)

        # Stabilize volatile fields for strict fixture conformance.
        self.assertRegex(
            actual[0]["timestamp"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z$",
        )
        actual[0]["timestamp"] = "__ISO8601__"
        actual[0]["patient_id"] = "fixture_patient"

        expected = json.loads((FIXTURE_DIR / "analyze_strict_codeine_pm.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_explanation_quality_endpoint(self):
        response = self.client.post(
            "/explanation-quality",
            data={
                "drug": "CODEINE",
                "gene": "CYP2D6",
                "summary": "Patient carries rs3892097 and *4/*4 for CYP2D6 with toxic CODEINE risk.",
                "mechanism": "CYP2D6 drives codeine activation.",
                "variant_impact": "No function diplotype.",
                "clinical_context": "Avoid codeine and monitor alternatives.",
                "patient_summary": "This drug is unsafe for you. Use alternatives.",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn("explanation_quality_score", body)
        self.assertIn("quality_fail_reasons", body)

    def test_phenoconversion_changes_effective_risk(self):
        payload = self._post_analyze(
            "patient_normal_all.vcf",
            "CODEINE",
            concurrent_medications="fluoxetine",
        )
        result = payload["results"][0]
        self.assertEqual(result["risk_assessment"]["risk_label"], "Adjust Dosage")
        self.assertIn(
            "Phenoconversion override",
            result["clinical_recommendation"]["action"],
        )

    def test_phenoconversion_check_endpoint(self):
        response = self.client.post(
            "/phenoconversion-check",
            data={
                "gene": "CYP2D6",
                "genetic_phenotype": "NM",
                "concurrent_medications": "fluoxetine",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["phenoconversion_risk"])
        self.assertEqual(body["genetic_phenotype"], "NM")
        self.assertEqual(body["functional_phenotype"], "IM")

    def test_cohort_summary_endpoint(self):
        first = self._post_analyze("patient_pm_cyp2d6.vcf", "CODEINE")["results"][0]
        second = self._post_analyze("patient_normal_all.vcf", "CODEINE")["results"][0]
        response = self.client.post("/cohort-summary", json=[first, second])
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["cohort_size"], 2)
        self.assertIn("CODEINE", body["risk_matrix"])
        self.assertIn("high_risk_count", body)


if __name__ == "__main__":
    unittest.main()
