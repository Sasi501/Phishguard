import unittest
from unittest.mock import AsyncMock, Mock, patch

import main


class HealthStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_exposes_engine_readiness_and_xai_without_changing_legacy_fields(self):
        database = Mock()
        database.command = AsyncMock(return_value={"ok": 1})
        with patch.object(main, "ML_READY", True), \
             patch.object(main, "NLP_READY", True), \
             patch.object(main, "VISION_READY", True), \
             patch.object(main, "DOMAIN_READY", True), \
             patch.object(main, "ENSEMBLE_READY", True), \
             patch.object(main, "get_db", return_value=database):
            result = await main.health_check()

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["engines"]["xai"]["ready"])
        self.assertTrue(result["engines"]["url_ml"]["ready"])
        self.assertTrue(result["engines"]["nlp"]["ready"])
        self.assertTrue(result["engines"]["vision"]["ready"])
        self.assertTrue(result["engines"]["domain"]["ready"])
        self.assertTrue(result["engines"]["hitl"]["ready"])
        self.assertTrue(result["engines"]["database"]["ready"])
        self.assertTrue(result["engines"]["ml_ready"])
        self.assertTrue(result["engines"]["ensemble_ready"])
        database.command.assert_awaited_once_with("ping")

    async def test_health_reports_mongodb_dependency_for_hitl_and_database(self):
        with patch.object(main, "get_db", return_value=None):
            result = await main.health_check()

        self.assertEqual(result["engines"]["hitl"], {
            "ready": False,
            "reason": "MongoDB unavailable",
        })
        self.assertEqual(result["engines"]["database"], {
            "ready": False,
            "reason": "MongoDB unavailable",
        })

    async def test_health_reports_failed_mongodb_ping_as_unavailable(self):
        database = Mock()
        database.command = AsyncMock(side_effect=ConnectionError("connection refused"))
        with patch.object(main, "get_db", return_value=database):
            result = await main.health_check()

        self.assertEqual(result["engines"]["database"]["ready"], False)
        self.assertEqual(result["engines"]["database"]["reason"], "MongoDB unavailable")
        self.assertEqual(result["engines"]["hitl"]["ready"], False)

    async def test_xai_readiness_tracks_backend_analysis_implementation(self):
        with patch.object(main, "ENSEMBLE_READY", False), \
             patch.object(main, "get_db", return_value=None):
            result = await main.health_check()

        self.assertEqual(result["engines"]["xai"], {
            "ready": False,
            "reason": "XAI analysis implementation is unavailable",
        })

    async def test_health_probe_does_not_run_scan_or_scoring(self):
        with patch.object(main, "calculate_ensemble_score") as score_scan, \
             patch.object(main, "get_db", return_value=None):
            await main.health_check()

        score_scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
