import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from detector.hitl_service import (
    submit_url,
    get_pending_urls,
    resolve_url,
    set_case_status,
    get_audit_logs,
    check_hitl_override,
)

class MockAsyncCursor:
    def __init__(self, docs):
        self.docs = docs
        self.index = 0

    def sort(self, field, direction):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index < len(self.docs):
            doc = self.docs[self.index]
            self.index += 1
            return doc
        else:
            raise StopAsyncIteration

class HITLTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_and_pending_flow(self):
        mock_db = MagicMock()
        mock_queue = MagicMock()
        mock_db.hitl_queue = mock_queue

        # Mock find_one returning None (not existing)
        mock_queue.find_one = AsyncMock(return_value=None)
        
        # Mock insert_one returning inserted_id
        mock_insert_res = MagicMock()
        mock_insert_res.inserted_id = "mock_id_123"
        mock_queue.insert_one = AsyncMock(return_value=mock_insert_res)

        # Mock find returning cursor
        pending_doc = {"_id": "mock_id_123", "url": "http://malicious-test-phish.net/login.html", "user_label": "phishing", "status": "pending"}
        mock_queue.find.return_value = MockAsyncCursor([pending_doc])

        with patch('detector.hitl_service.get_db', return_value=mock_db):
            url = "http://malicious-test-phish.net/login.html"
            item = await submit_url(url, "phishing")
            
            self.assertEqual(item["url"], url)
            self.assertEqual(item["user_label"], "phishing")
            self.assertEqual(item["status"], "pending")

            pending = await get_pending_urls()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["url"], url)

    async def test_resolve_and_override_flow(self):
        mock_db = MagicMock()
        mock_queue = MagicMock()
        mock_audit = MagicMock()
        mock_db.hitl_queue = mock_queue
        mock_db.hitl_audit = mock_audit

        url = "http://safe-verified-site.org/index.html"
        resolved_doc = {
            "_id": "mock_id_456",
            "url": url,
            "user_label": "safe",
            "final_label": "safe",
            "status": "resolved",
            "reviewer": "admin-tester"
        }

        mock_queue.find_one_and_update = AsyncMock(return_value=resolved_doc)
        mock_audit.insert_one = AsyncMock()
        mock_queue.find.return_value = MockAsyncCursor([])
        mock_queue.find_one = AsyncMock(return_value=resolved_doc)
        mock_audit.find.return_value = MockAsyncCursor([{"_id": "audit_1", "url": url, "action": "Classified as safe", "reviewer": "admin-tester", "timestamp": 12345}])

        with patch('detector.hitl_service.get_db', return_value=mock_db):
            res = await resolve_url(url, "safe", "admin-tester")
            self.assertIsNotNone(res)

            pending = await get_pending_urls()
            self.assertEqual(len(pending), 0)

            override = await check_hitl_override(url)
            self.assertIsNotNone(override)
            self.assertEqual(override["ensemble_risk_level"], "safe")
            self.assertEqual(override["ensemble_score_percent"], 0.0)
            self.assertTrue(override["hitl_override"])

            logs = await get_audit_logs()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["url"], url)
            self.assertEqual(logs[0]["reviewer"], "admin-tester")

    async def test_resolution_comment_and_normalized_case_fields(self):
        mock_db = MagicMock()
        mock_queue = MagicMock()
        mock_audit = MagicMock()
        mock_db.hitl_queue = mock_queue
        mock_db.hitl_audit = mock_audit
        resolved_doc = {
            "_id": "case_789",
            "url": "http://review.example/",
            "user_label": "suspicious",
            "final_label": "phishing",
            "status": "resolved",
            "reviewer": "analyst-1",
        }
        mock_queue.find_one_and_update = AsyncMock(return_value=resolved_doc)
        mock_audit.insert_one = AsyncMock()

        with patch("detector.hitl_service.get_db", return_value=mock_db):
            case = await resolve_url(
                resolved_doc["url"],
                "phishing",
                "analyst-1",
                "Credential harvesting confirmed.",
            )

        self.assertEqual(case["case_id"], "case_789")
        self.assertEqual(case["analyst_verdict"], "phishing")
        self.assertEqual(case["analyst_comment"], "Credential harvesting confirmed.")
        self.assertEqual(case["case_status"], "resolved")
        audit_record = mock_audit.insert_one.await_args.args[0]
        self.assertEqual(audit_record["comment"], "Credential harvesting confirmed.")

    async def test_under_review_and_needs_investigation_do_not_override(self):
        mock_db = MagicMock()
        mock_queue = MagicMock()
        mock_audit = MagicMock()
        mock_db.hitl_queue = mock_queue
        mock_db.hitl_audit = mock_audit
        case = {
            "_id": "case_101",
            "url": "http://investigate.example/",
            "status": "under_review",
            "case_status": "under_review",
            "final_label": "unknown",
        }
        mock_queue.find_one_and_update = AsyncMock(return_value=case)
        mock_queue.find_one = AsyncMock(return_value={
            **case,
            "status": "needs_investigation",
            "case_status": "needs_investigation",
            "final_label": "needs_investigation",
        })
        mock_audit.insert_one = AsyncMock()

        with patch("detector.hitl_service.get_db", return_value=mock_db):
            claimed = await set_case_status(case["url"], "under_review", "analyst-1")
            investigated = await resolve_url(
                case["url"],
                "needs_investigation",
                "analyst-1",
                "Insufficient evidence.",
            )
            override = await check_hitl_override(case["url"])

        self.assertEqual(claimed["case_status"], "under_review")
        self.assertEqual(investigated["case_status"], "needs_investigation")
        self.assertIsNone(override)

    async def test_submission_stores_optional_evidence_snapshot(self):
        mock_db = MagicMock()
        mock_queue = MagicMock()
        mock_audit = MagicMock()
        mock_db.hitl_queue = mock_queue
        mock_db.hitl_audit = mock_audit
        mock_queue.find_one = AsyncMock(return_value=None)
        inserted = MagicMock()
        inserted.inserted_id = "case-snapshot"
        mock_queue.insert_one = AsyncMock(return_value=inserted)
        snapshot = {
            "captured_at": 123.0,
            "source": "ensemble_analysis",
            "original_url": "https://submitted.example/",
            "final_url": "https://landing.example/",
            "ensemble_score": 82.0,
            "ensemble_risk_level": "phishing",
            "engine_signals": [{"engine": "URL ML", "score": 90}],
            "xai": {"summary": "Observed risk factors."},
            "redirect_analysis": {
                "original_url": "https://submitted.example/",
                "final_url": "https://landing.example/",
                "redirect_chain": [],
                "num_redirects": 0,
                "resolution_state": "completed",
                "errors": [],
            },
        }

        with patch("detector.hitl_service.get_db", return_value=mock_db):
            case = await submit_url("https://submitted.example/", "phishing", snapshot)

        stored = mock_queue.insert_one.await_args.args[0]
        self.assertEqual(stored["evidence_snapshot"], snapshot)
        self.assertEqual(case["evidence_snapshot"]["xai"]["summary"], "Observed risk factors.")

    async def test_snapshot_is_not_changed_by_claim_or_resolution(self):
        mock_db = MagicMock()
        mock_queue = MagicMock()
        mock_audit = MagicMock()
        mock_db.hitl_queue = mock_queue
        mock_db.hitl_audit = mock_audit
        snapshot = {"source": "ensemble_analysis", "ensemble_score": 10.0}
        stored_case = {
            "_id": "case-integrity",
            "url": "https://integrity.example/",
            "status": "pending",
            "final_label": "unknown",
            "evidence_snapshot": snapshot,
        }
        mock_queue.find_one_and_update = AsyncMock(return_value=stored_case)
        mock_audit.insert_one = AsyncMock()

        with patch("detector.hitl_service.get_db", return_value=mock_db):
            await set_case_status(stored_case["url"], "under_review", "analyst")
            await resolve_url(stored_case["url"], "safe", "analyst", "Reviewed.")

        for call in mock_queue.find_one_and_update.await_args_list:
            update = call.args[1]
            self.assertNotIn("evidence_snapshot", update.get("$set", {}))
            self.assertNotIn("evidence_snapshot", update.get("$setOnInsert", {}))
        self.assertEqual(stored_case["evidence_snapshot"], snapshot)

if __name__ == '__main__':
    unittest.main()
