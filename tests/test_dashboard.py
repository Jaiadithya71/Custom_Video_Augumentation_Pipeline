"""Unit tests for Dashboard REST API and routes."""

import unittest
import json
from src.dashboard.app import app


class TestDashboardAPI(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_route(self):
        """Verify the dashboard homepage loads with HTML."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Content Agent Dashboard", response.data)

    def test_get_jobs_api(self):
        """Verify /api/jobs returns a valid JSON array."""
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_post_job_validation(self):
        """Verify POST /api/jobs requires a URL."""
        response = self.client.post("/api/jobs", json={})
        self.assertEqual(response.status_code, 400)

        response2 = self.client.post("/api/jobs", json={"url": ""})
        self.assertEqual(response2.status_code, 400)


if __name__ == "__main__":
    unittest.main()
