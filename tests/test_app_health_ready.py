"""Tests for Flask /health/ready readiness endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app_flask import app


class TestHealthReady(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    @patch("app_flask.database_connection_ok", return_value=(True, None))
    def test_ready_200_when_db_connects(self, _mock: MagicMock) -> None:
        resp = self.client.get("/health/ready")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(data.get("status"), "ready")
        self.assertTrue((data.get("database") or {}).get("ok"))

    @patch(
        "app_flask.database_connection_ok",
        return_value=(False, "connection refused"),
    )
    def test_ready_503_when_db_fails(self, _mock: MagicMock) -> None:
        resp = self.client.get("/health/ready")
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(data.get("status"), "not_ready")
        self.assertFalse((data.get("database") or {}).get("ok"))


if __name__ == "__main__":
    unittest.main()
