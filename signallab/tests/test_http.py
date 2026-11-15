from httpcase import BoundaryCase


class HTTPTests(BoundaryCase):
    def test_static_and_health(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"SignalLab", body)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("GET", "/api/health")[2]["project"], "SignalLab")

    def test_real_replay_and_unlabeled_import(self):
        status, _, result = self.request("POST", "/api/analyze", {})
        self.assertEqual(status, 200)
        self.assertEqual(len(result["comparison"]), 3)
        status, _, result = self.request("POST", "/api/analyze", {"csv": "minute,service,total,bad\n0,api,1000,0\n"})
        self.assertEqual(status, 200)
        self.assertIsNone(result["comparison"][0]["recall"])

    def test_malformed_csv_is_rejected(self):
        for text in ["bad csv", "minute,service,total,bad\n0,api,1000,0,extra\n", "minute,service,total,bad\n1,api,10,0\n"]:
            with self.subTest(text=text):
                self.assertEqual(self.request("POST", "/api/analyze", {"csv":text})[0], 400)

    def test_invalid_json_and_nonfinite_numbers(self):
        for raw in ['{"slo":NaN}', '[]', '{broken']:
            self.assertEqual(self.request("POST", "/api/analyze", raw=raw, headers={"Content-Type":"application/json"})[0], 400)

    def test_foreign_origin_and_wrong_content_type(self):
        self.assertEqual(self.request("POST", "/api/analyze", {}, {"Origin":"https://example.com"})[0], 403)
        self.assertEqual(self.request("POST", "/api/analyze", raw="{}")[0], 415)

    def test_static_traversal_and_duplicate_query_rejected(self):
        self.assertEqual(self.request("GET", "/../core.py")[0], 404)
        self.assertEqual(self.request("GET", "/api/health?x=1&x=2")[0], 400)
