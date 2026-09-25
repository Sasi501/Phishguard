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


if __name__ == "__main__":
    unittest.main()
