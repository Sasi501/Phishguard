import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from detector.hitl_service import submit_url, get_pending_urls, resolve_url, get_audit_logs, check_hitl_override

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

if __name__ == '__main__':
    unittest.main()
