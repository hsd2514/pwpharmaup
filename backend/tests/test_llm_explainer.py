import unittest

from models.schemas import RiskAssessment
import pipeline.llm_explainer as llm


class LLMExplainerTests(unittest.IsolatedAsyncioTestCase):
    async def test_placeholder_fields_are_replaced_by_template_text(self):
        original_predict = llm.predict_endpoint
        try:
            calls = {"count": 0}

            def fake_predict(project, endpoint_id, instances, location, dedicated_domain=""):
                calls["count"] += 1
                if calls["count"] == 1:
                    # Stage A narrative
                    return [{"content": "Narrative from model about rs3892097 and codeine."}]
                # Stage B JSON with placeholders
                return [{
                    "content": (
                        '{"summary":"...","mechanism":"...","variant_impact":"...",'
                        '"clinical_context":"...","patient_summary":"..."}'
                    )
                }]

            llm.predict_endpoint = fake_predict
            explainer = llm.LLMExplainer()
            risk = RiskAssessment(risk_label="Toxic", confidence_score=0.95, severity="critical")
            out = await explainer.generate_explanation(
                drug="CODEINE",
                gene="CYP2D6",
                diplotype="*4/*4",
                phenotype="Poor Metabolizer",
                risk_assessment=risk,
                detected_variants=[],
                cpic_action="Avoid codeine.",
            )

            self.assertNotEqual(out.summary.strip(), "...")
            self.assertNotEqual(out.mechanism.strip(), "...")
            self.assertNotEqual(out.patient_summary.strip(), "...")
            self.assertTrue(len(out.summary.strip()) > 0)
            self.assertTrue(len(out.mechanism.strip()) > 0)
            self.assertTrue(len(out.patient_summary.strip()) > 0)
        finally:
            llm.predict_endpoint = original_predict


if __name__ == "__main__":
    unittest.main()
