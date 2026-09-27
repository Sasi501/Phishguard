import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

import main


class HITLEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolution_comment_is_forwarded(self):
        expected = {"case_id": "case-1", "case_status": "resolved"}
        with patch.object(main, "_validate_url"), \
             patch("detector.hitl_service.resolve_url", new=AsyncMock(return_value=expected)) as resolve:
            result = await main.api_hitl_resolve(
                url="https://review.example/",
                final_label="safe",
                reviewer="analyst-1",
                comment="Legitimate authentication provider.",
            )

        self.assertEqual(result, expected)
        resolve.assert_awaited_once_with(
            "https://review.example/",
            "safe",
            "analyst-1",
            "Legitimate authentication provider.",
        )

    async def test_invalid_case_id_returns_not_found(self):
        with patch.object(main, "_validate_url"), \
             patch("detector.hitl_service.resolve_url", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as context:
                await main.api_hitl_resolve(
                    url="https://missing.example/",
                    final_label="phishing",
                    reviewer="analyst-1",
                )

        self.assertEqual(context.exception.status_code, 404)

    def test_admin_auth_rejects_missing_or_wrong_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as missing:
                main.require_admin(None)
        with patch.dict(os.environ, {"ADMIN_API_KEY": "test-only-secret"}, clear=True):
            with self.assertRaises(HTTPException) as wrong:
                main.require_admin("not-the-key")

        self.assertEqual(missing.exception.status_code, 403)
        self.assertEqual(wrong.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
