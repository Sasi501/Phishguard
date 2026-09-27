import unittest
from unittest.mock import patch

import main


class MainRedirectResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_analyze_ensemble_exposes_namespaced_redirect_analysis(self):
        redirect_analysis = {
            "original_url": "https://short.example/a",
            "final_url": "https://landing.example/",
            "redirect_chain": [],
            "num_redirects": 0,
            "loop_detected": False,
            "suspicious_redirects": False,
            "has_meta_refresh": False,
            "resolution_state": "completed",
            "errors": [],
        }
        scan_result = {
            "ensemble_score_percent": 12.0,
            "confidence": 12.0,
            "ensemble_risk_level": "safe",
            "xai_summary": "safe",
            "xai": {},
            "reasons": [],
            "individual_scores_percent": {"ml": 10.0, "domain": 20.0},
            "redirect_analysis": redirect_analysis,
        }

        with patch.object(main, "_validate_url"), \
             patch.object(main, "calculate_ensemble_score", return_value=scan_result), \
             patch.object(main, "get_db", return_value=None), \
             patch(
                 "vision_module.screenshot_pipeline.capture_screenshot",
                 return_value={"thumb": None, "is_real_screenshot": False},
             ):
            result = await main.analyze_ensemble(
                url="https://short.example/a",
                text=None,
                image=None,
            )

        self.assertEqual(result["redirect_analysis"], redirect_analysis)
        self.assertIn("ensemble_score_percent", result)

    async def test_loopback_scan_reaches_ensemble_instead_of_failing_url_validation(self):
        url = "http://127.0.0.1:8000/api/scan/"
        result_payload = {
            "ensemble_score_percent": 42.0,
            "ensemble_risk_level": "suspicious",
            "analysis_status": "partial",
            "engine_status": {"domain_intelligence": {"status": "restricted"}},
            "individual_scores_percent": {"ml": 42.0},
            "xai": {},
            "xai_summary": "Network evidence was restricted.",
            "reasons": [],
        }
        with patch.object(main, "calculate_ensemble_score", return_value=result_payload) as mock_analyze, \
             patch.object(main, "get_db", return_value=None), \
             patch("vision_module.screenshot_pipeline.SCREENSHOT_ENABLED", False), \
             patch(
                 "vision_module.screenshot_pipeline.capture_screenshot",
                 return_value={"thumb": None, "is_real_screenshot": False},
             ):
            result = await main.analyze_ensemble(url=url, text=None, image=None)

        self.assertEqual(result["analysis_status"], "partial")
        mock_analyze.assert_awaited_once()
        self.assertEqual(mock_analyze.await_args.args[0], url)
        self.assertEqual(
            mock_analyze.await_args.kwargs["vision_status"]["applicable"],
            False,
        )

    async def test_unwrap_endpoint_returns_blocked_state_without_domain_fetch(self):
        url = "http://127.0.0.1:8000/api/scan/"
        blocked_reason = "Unsafe destination resolved to blocked address: 127.0.0.1"
        with patch("domain_module.shortener_expander.is_likely_shortener", return_value=False), \
             patch("domain_module.redirect_unwrapper.unwrap_url", return_value={
                 "original_url": url,
                 "final_url": url,
                 "redirect_chain": [{"url": url, "status_code": None, "note": "unsafe_url"}],
                 "num_redirects": 0,
                 "loop_detected": False,
                 "suspicious_redirects": False,
                 "resolution_state": "blocked",
                 "blocked_reason": blocked_reason,
                 "errors": [f"unsafe_url:{blocked_reason}"],
             }), \
             patch("domain_module.domain_intelligence.get_domain_metadata") as mock_metadata, \
             patch.object(main, "get_db", return_value=None):
            result = await main.unwrap_redirect_endpoint(main.DomainRequest(url=url))

        mock_metadata.assert_not_called()
        self.assertEqual(result["resolution_state"], "blocked")
        self.assertEqual(result["status"], "restricted")
        self.assertIsNone(result["domain_risk"]["domain_score"])

    async def test_private_target_skips_automatic_screenshot_and_marks_vision_restricted(self):
        url = "http://127.0.0.1:8000/api/scan/"
        payload = {
            "ensemble_score_percent": 30.0,
            "ensemble_risk_level": "safe",
            "analysis_status": "partial",
            "engine_status": {"vision": {"status": "restricted"}},
            "individual_scores_percent": {"ml": 30.0},
            "xai": {},
            "xai_summary": "Network evidence was restricted.",
            "reasons": [],
        }
        with patch.object(main, "calculate_ensemble_score", return_value=payload) as mock_analyze, \
             patch.object(main, "get_db", return_value=None), \
             patch("vision_module.screenshot_pipeline.SCREENSHOT_ENABLED", True), \
             patch(
                 "domain_module.redirect_unwrapper.validate_url_for_fetch",
                 side_effect=ValueError("Unsafe destination resolved to blocked address: 127.0.0.1"),
             ), \
             patch("vision_module.screenshot_pipeline.capture_screenshot") as mock_capture:
            result = await main.analyze_ensemble(url=url, text=None, image=None)

        mock_capture.assert_not_called()
        self.assertEqual(result["analysis_status"], "partial")
        vision_status = mock_analyze.await_args.kwargs["vision_status"]
        self.assertEqual(vision_status["status"], "restricted")
        self.assertTrue(vision_status["applicable"])


if __name__ == "__main__":
    unittest.main()
