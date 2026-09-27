"""Controlled, no-network failure-mode coverage for API and fusion behavior."""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

import main
from ensemble_module import fusion_engine


def _redirect(state: str = "completed") -> dict:
    return {
        "original_url": "https://example.test/",
        "final_url": "https://example.test/",
        "redirect_chain": [],
        "num_redirects": 0,
        "loop_detected": state == "loop",
        "suspicious_redirects": state == "loop",
        "has_meta_refresh": False,
        "resolution_state": state,
        "errors": [] if state == "completed" else [f"chaos:{state}"],
    }


def _domain_result(redirect_state: str = "completed", ti_status: str = "available") -> dict:
    return {
        "status": "available",
        "domain_score": 0.1,
        "domain_risk_level": "safe",
        "domain_signals": [],
        "metadata": {"age_days": None, "ssl_valid": True},
        "ti_status": {"status": ti_status, "reason": "TI unavailable in chaos test" if ti_status != "available" else None},
        "ti_details": {"status": ti_status, "ti_hits": 0, "ti_sources": []},
        "redirect_analysis": _redirect(redirect_state),
    }


class ChaosFailureModeTests(unittest.IsolatedAsyncioTestCase):
    async def _calculate(self, unavailable: str | None = None, *, redirect_state: str = "completed", ti_status: str = "available") -> dict:
        ready = {
            "ML_READY": unavailable != "url_ml",
            "NLP_READY": unavailable != "nlp",
            "VISION_READY": unavailable != "vision",
            "DOMAIN_READY": unavailable != "domain_intelligence",
        }
        with patch.multiple(fusion_engine, **ready), \
             patch("detector.hitl_service.check_hitl_override", new=AsyncMock(return_value=None)), \
             patch.object(fusion_engine, "predict_url", return_value={"ml_score": 0.1}), \
             patch.object(fusion_engine, "analyze_text_with_nlp", return_value={"nlp_score": 0.1}), \
             patch.object(fusion_engine, "analyze_image_with_vision", return_value={"vision_score": 0.1}), \
             patch.object(fusion_engine, "analyze_domain", return_value=_domain_result(redirect_state, ti_status)), \
             patch.object(fusion_engine, "get_meta_learner", return_value=None):
            return await fusion_engine.calculate_ensemble_score(
                "https://example.test/", text="submitted text", image_bytes=b"image",
            )

    async def test_each_unavailable_scoring_engine_is_explicit_and_partial(self):
        for unavailable in ("url_ml", "nlp", "vision", "domain_intelligence"):
            with self.subTest(unavailable=unavailable):
                result = await self._calculate(unavailable)
                signal = next(item for item in result["xai"]["engine_signals"] if item["source"] == unavailable)
                self.assertEqual(result["analysis_status"], "partial")
                self.assertEqual(result["engine_status"][unavailable]["status"], "unavailable")
                self.assertEqual(signal["status"], "unavailable")
                self.assertNotIn(unavailable.split("_")[0], result["individual_scores_percent"])
                self.assertIsNotNone(result["ensemble_score_percent"])

    async def test_no_available_scoring_engine_returns_no_fabricated_final_score(self):
        with patch.multiple(fusion_engine, ML_READY=False, NLP_READY=False, VISION_READY=False, DOMAIN_READY=False), \
             patch("detector.hitl_service.check_hitl_override", new=AsyncMock(return_value=None)):
            result = await fusion_engine.calculate_ensemble_score(
                "https://example.test/", text="submitted text", image_bytes=b"image",
            )

        self.assertEqual(result["analysis_status"], "failed")
        self.assertEqual(result["fusion_method"], "unavailable")
        self.assertIsNone(result["ensemble_score_percent"])
        self.assertEqual(result["ensemble_risk_level"], "unavailable")
        self.assertEqual(result["individual_scores_percent"], {})

    async def test_ti_failure_is_explicit_without_changing_available_engine_scores(self):
        result = await self._calculate(ti_status="unavailable")
        signal = next(item for item in result["xai"]["engine_signals"] if item["source"] == "threat_intelligence")
        self.assertEqual(result["analysis_status"], "partial")
        self.assertEqual(result["engine_status"]["threat_intelligence"]["status"], "unavailable")
        self.assertEqual(signal["status"], "unavailable")
        self.assertEqual(result["individual_scores_percent"], {"ml": 10.0, "nlp": 10.0, "vision": 10.0, "domain": 10.0})

    def test_ti_original_scope_is_preserved_when_resolution_cannot_reach_a_final_url(self):
        signals = fusion_engine._build_engine_signals(
            {},
            {"ti_details": {"ti_hits": 0, "ti_sources": []}},
            engine_status={"threat_intelligence": {"status": "available", "url_scope": "original_url"}},
        )
        ti_signal = next(signal for signal in signals if signal["source"] == "threat_intelligence")
        self.assertEqual(ti_signal["url_scope"], "original_url")

    def test_unsubmitted_and_restricted_inputs_do_not_claim_collected_evidence(self):
        signals = fusion_engine._build_engine_signals(
            {},
            {"status": "restricted", "ti_details": {"ti_hits": 0, "ti_sources": []}},
            engine_status={
                "url_ml": {"status": "available", "applicable": True},
                "nlp": {"status": "unavailable", "applicable": False},
                "vision": {"status": "unavailable", "applicable": False},
                "domain_intelligence": {"status": "restricted", "applicable": True},
                "threat_intelligence": {"status": "unavailable", "url_scope": "original_url"},
            },
        )
        by_source = {signal["source"]: signal for signal in signals}
        self.assertEqual(by_source["nlp"]["url_scope"], "not_submitted")
        self.assertEqual(by_source["vision"]["url_scope"], "not_submitted")
        self.assertEqual(by_source["domain_intelligence"]["url_scope"], "not_collected")

    async def test_captured_screenshot_provenance_is_distinct_from_a_submitted_image(self):
        with patch.multiple(fusion_engine, ML_READY=False, NLP_READY=False, VISION_READY=True, DOMAIN_READY=False), \
             patch("detector.hitl_service.check_hitl_override", new=AsyncMock(return_value=None)), \
             patch.object(fusion_engine, "analyze_image_with_vision", return_value={"vision_score": 0.2}):
            result = await fusion_engine.calculate_ensemble_score(
                "https://example.test/",
                image_bytes=b"screenshot",
                vision_status={"status": "available", "applicable": True, "input_scope": "captured_screenshot"},
            )
        signal = next(item for item in result["xai"]["engine_signals"] if item["source"] == "vision")
        self.assertEqual(signal["url_scope"], "captured_screenshot")

    async def test_redirect_failures_are_explicit_without_fabricating_redirect_evidence(self):
        for state in ("failed", "loop", "limit_exceeded"):
            with self.subTest(state=state):
                result = await self._calculate(redirect_state=state)
                self.assertEqual(result["analysis_status"], "partial")
                self.assertEqual(result["redirect_analysis"]["resolution_state"], state)
                self.assertNotEqual(result["engine_status"]["redirect"]["status"], "available")
                self.assertFalse(any(item["source"] == "redirect" for item in result["xai"]["engine_signals"]))

    async def test_xai_unavailable_returns_503_without_starting_analysis(self):
        with patch.object(main, "ENSEMBLE_READY", False):
            with self.assertRaises(HTTPException) as raised:
                await main.analyze_ensemble(url="https://example.test/")
        self.assertEqual(raised.exception.status_code, 503)

    async def test_engine_exceptions_are_not_disclosed_to_api_clients(self):
        with patch.object(main, "NLP_READY", True), \
             patch.object(main, "analyze_text_with_nlp", side_effect=RuntimeError("internal host secret")):
            with self.assertRaises(HTTPException) as raised:
                await main.analyze_text(main.TextRequest(text="test"))
        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail, "Internal server error.")

    def test_invalid_and_unsupported_urls_return_client_errors(self):
        for url in ("", "ftp://example.test/", "javascript:alert(1)", "https://example.test:" + "9" * 32):
            with self.subTest(url=url):
                with self.assertRaises(HTTPException) as raised:
                    main._validate_url_syntax(url)
                self.assertEqual(raised.exception.status_code, 400)
