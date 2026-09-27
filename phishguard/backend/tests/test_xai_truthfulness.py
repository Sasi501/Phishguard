"""Deterministic XAI truthfulness tests using controlled engine outputs only."""
import unittest
from unittest.mock import AsyncMock, patch

from ensemble_module import fusion_engine


def _redirect(state="completed"):
    return {
        "original_url": "https://submitted.test/",
        "final_url": "https://final.test/",
        "redirect_chain": [],
        "num_redirects": 0,
        "loop_detected": state == "loop",
        "suspicious_redirects": False,
        "has_meta_refresh": False,
        "resolution_state": state,
        "errors": [],
    }


class XaiTruthfulnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_safe_ti_no_match_is_limited_evidence_not_proof_of_safety(self):
        domain = {
            "status": "available", "domain_score": 0.1, "domain_risk_level": "safe",
            "domain_signals": [], "metadata": {"age_days": None, "ssl_valid": True},
            "ti_status": {"status": "available", "url_scope": "final_url"},
            "ti_details": {"status": "available", "ti_hits": 0, "ti_sources": []},
            "redirect_analysis": _redirect(),
        }
        with patch.multiple(fusion_engine, ML_READY=True, NLP_READY=False, VISION_READY=False, DOMAIN_READY=True), \
             patch("detector.hitl_service.check_hitl_override", new=AsyncMock(return_value=None)), \
             patch.object(fusion_engine, "predict_url", return_value={"ml_score": 0.1}), \
             patch.object(fusion_engine, "analyze_domain", return_value=domain), \
             patch.object(fusion_engine, "generate_xai_summary", return_value="invented narrative") as narrative:
            result = await fusion_engine.calculate_ensemble_score("https://submitted.test/")

        narrative.assert_not_called()
        ti_factor = next(item for item in result["xai"]["safety_factors"] if item["source"] == "threat_intelligence")
        self.assertIn("not proof", ti_factor["description"].lower())
        self.assertIn("not proof", result["xai_summary"].lower())
        # B3 correction: only URL ML (0.1) and Domain (0.1) produced measurements;
        # NLP and Vision were never applicable for this URL-only scan.
        #   before: 0.1*0.35 + 0.15*0.0 + 0.20*0.0 + 0.1*0.30 = 0.065 -> 6.5%
        #           (the 0.35 weight mass of NLP+Vision counted as measured "0.0 = safe")
        #   after : (0.1*0.35 + 0.1*0.30) / (0.35 + 0.30)      = 0.100 -> 10.0%
        self.assertEqual(result["individual_scores_percent"], {"ml": 10.0, "domain": 10.0})
        self.assertEqual(result["ensemble_score_percent"], 10.0)

    async def test_partial_scan_xai_only_describes_available_engine_outputs(self):
        restricted = {
            "status": "restricted", "reason": "SSRF protection blocked metadata collection.",
            "domain_score": None, "domain_signals": [],
            "metadata": {"status": "restricted"},
            "ti_status": {"status": "unavailable", "url_scope": "original_url"},
            "ti_details": {"status": "unavailable", "ti_hits": 0, "ti_sources": []},
            "redirect_analysis": _redirect("blocked"),
        }
        with patch.multiple(fusion_engine, ML_READY=True, NLP_READY=False, VISION_READY=False, DOMAIN_READY=True), \
             patch("detector.hitl_service.check_hitl_override", new=AsyncMock(return_value=None)), \
             patch.object(fusion_engine, "predict_url", return_value={"ml_score": 0.8}), \
             patch.object(fusion_engine, "analyze_domain", return_value=restricted):
            result = await fusion_engine.calculate_ensemble_score("http://127.0.0.1/")

        self.assertEqual(result["analysis_status"], "partial")
        self.assertEqual(result["ensemble_score_percent"], 80.0)
        self.assertEqual(result["engine_status"]["domain_intelligence"]["status"], "restricted")
        self.assertEqual(result["engine_status"]["threat_intelligence"]["status"], "unavailable")
        self.assertNotIn("WHOIS", result["xai_summary"])
        self.assertNotIn("SSL certificate", result["xai_summary"])
        self.assertIn("not itself evidence of phishing", result["xai_summary"])

    async def test_raw_url_probability_and_engine_signal_remain_distinct(self):
        with patch.multiple(fusion_engine, ML_READY=True, NLP_READY=False, VISION_READY=False, DOMAIN_READY=False), \
             patch("detector.hitl_service.check_hitl_override", new=AsyncMock(return_value=None)), \
             patch.object(fusion_engine, "predict_url", return_value={"ml_score": 0.72}):
            result = await fusion_engine.calculate_ensemble_score("https://submitted.test/")

        evidence = result["xai"]["url_ml_evidence"]
        signal = next(item for item in result["xai"]["engine_signals"] if item["source"] == "url_ml")
        self.assertEqual(evidence["raw_model_probability_percent"], 72.0)
        self.assertEqual(evidence["engine_signal_percent"], signal["score"])
        factor = next(item for item in result["xai"]["risk_factors"] if item["source"] == "url")
        self.assertIn("Raw URL-model probability", factor["description"])
        self.assertIn("engine signal used in fusion", factor["description"])

    def test_missing_engine_outputs_create_no_invented_factors(self):
        result = fusion_engine._build_xai_structured(
            url="https://submitted.test/", risk_level="unavailable", scores={},
            ml_result=None, nlp_result=None, vision_result=None, domain_result=None,
            threat_result=None, redirect_analysis=None, engine_status={},
        )
        self.assertEqual(result["summary"], "No valid engine score was available to produce a final ensemble assessment.")
        self.assertEqual(result["risk_factors"], [])
        self.assertEqual(result["safety_factors"], [])
