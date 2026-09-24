"""Application and HTTP tests. These do not substitute for model integration tests."""
import http.client
import json
from pathlib import Path
import threading
import unittest

from app import make_server
from poc.engine import BusyError, Engine
from poc.validation import InvalidRequest, parse_json, validate

ROOT = Path(__file__).resolve().parents[1]
REQUEST = json.loads((ROOT / "examples/triage-request.json").read_text())


class ValidationTests(unittest.TestCase):
    def test_all_supplied_samples_validate(self):
        presets = json.loads((ROOT / "examples/presets.json").read_text())
        for preset in presets:
            for sample in preset["samples"]:
                with self.subTest(preset=preset["id"], sample=sample["name"]):
                    validate({"state": sample["state"], "questions": preset["questions"],
                              "checkpoint": sample.get("checkpoint", preset["checkpoint"])})

    def test_invalid_states(self):
        for state in (None, True, 12, "  ", {}, [], "x" * 24001):
            with self.subTest(state_type=type(state).__name__):
                with self.assertRaises(InvalidRequest):
                    validate(dict(REQUEST, state=state))

    def test_invalid_question_shapes(self):
        cases = [{}, {"x": {"type": "extract", "instructions": "Extract amount"}},
                 {"x": {"type": "choice", "instructions": "Select", "criteria": ["a", "b"]}},
                 {"x": {"type": "score", "instructions": "Rate", "criteria": ["low"]}},
                 {"x": {"type": "noul", "instructions": "True?", "criteria": {"yes": "yes"}}},
                 {"x": {"type": "noul", "instructions": " "}},
                 {"x": {"type": "noul", "instructions": "True?", "unexpected": 1}}]
        for questions in cases:
            with self.subTest(questions=questions), self.assertRaises(InvalidRequest):
                validate(dict(REQUEST, questions=questions))

    def test_unknown_checkpoint_and_top_level_fields(self):
        for payload in (dict(REQUEST, checkpoint="arbitrary/repo"), dict(REQUEST, device="cuda")):
            with self.assertRaises(InvalidRequest):
                validate(payload)

    def test_duplicate_keys_and_nonfinite_numbers(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{broken'):
            with self.assertRaises(InvalidRequest):
                parse_json(raw)


class FakeAgent:
    device = "cpu"

    def predict(self, state, questions):
        return Engine._preview(questions)


class EngineTests(unittest.TestCase):
    def make_engine(self):
        self.loads = []
        def loader(checkpoint, device, threads):
            self.loads.append(checkpoint)
            return FakeAgent()
        return Engine(loader=loader, reporter=lambda *args: {"truncated_questions": []})

    def test_preview_is_explicit_and_input_independent(self):
        engine = Engine(demo=True, loader=lambda *args: self.fail("preview must not load ML"))
        first = engine.predict(REQUEST)
        second = engine.predict(dict(REQUEST, state="completely different input"))
        self.assertEqual(first["mode"], "preview")
        self.assertEqual(first["result"], second["result"])
        self.assertIn("synthetic", first["warnings"][0])
        self.assertEqual(first["runtime"]["device"], "none")

    def test_model_reuse_switch_and_unload(self):
        engine = self.make_engine()
        self.assertTrue(engine.predict(REQUEST)["runtime"]["cold_load"])
        self.assertFalse(engine.predict(REQUEST)["runtime"]["cold_load"])
        engine.predict(dict(REQUEST, checkpoint="multilingual"))
        self.assertEqual(self.loads, ["typed-decisions", "multilingual"])
        engine.unload()
        self.assertIsNone(engine.health()["checkpoint"])
        self.assertIsNone(engine._agent)

    def test_busy_requests_are_rejected(self):
        engine = self.make_engine()
        engine._lock.acquire()
        try:
            with self.assertRaises(BusyError): engine.predict(REQUEST)
            with self.assertRaises(BusyError): engine.unload()
        finally:
            engine._lock.release()

    def test_load_failure_never_falls_back_to_preview(self):
        def fail(*args): raise RuntimeError("test download failure")
        engine = Engine(loader=fail)
        with self.assertRaisesRegex(RuntimeError, "download failure"):
            engine.predict(REQUEST)
        self.assertEqual(engine.health()["mode"], "laya")
        self.assertFalse(engine._lock.locked())
        engine.loader = lambda *args: FakeAgent()
        engine.reporter = lambda *args: {"truncated_questions": []}
        self.assertEqual(engine.predict(REQUEST)["mode"], "laya")

    def test_truncation_is_exposed(self):
        engine = self.make_engine()
        engine.reporter = lambda *args: {"truncated_questions": ["department"]}
        response = engine.predict(REQUEST)
        self.assertTrue(any("truncated" in warning for warning in response["warnings"]))


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(Engine(demo=True), port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def post(self, payload=REQUEST, headers=None):
        return self.request("POST", "/api/predict", json.dumps(payload), headers or {"Content-Type": "application/json"})

    def test_api_only_routes_and_runtime(self):
        for path in ("/api/presets", "/api/health"):
            with self.subTest(path=path):
                status, headers, body = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertGreater(len(body), 10)
                self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ("/", "/style.css", "/app.js"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)

    def test_all_question_types_over_http(self):
        status, _, body = self.post()
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["mode"], "preview")
        self.assertEqual({x["type"] for x in result["result"]["answers"].values()}, {"choice", "score", "noul"})

    def test_http_validation_and_media_type(self):
        self.assertEqual(self.post(dict(REQUEST, state=""))[0], 400)
        self.assertEqual(self.post(headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/predict", "x" * 131073, {"Content-Type": "application/json"})[0], 413)

    def test_path_traversal_and_unknown_routes(self):
        for path in ("/../model_sources.json", "/%2e%2e/app.py", "/app.py", "/api/missing"):
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_cross_origin_and_dns_rebinding_requests(self):
        self.assertEqual(self.post(headers={"Content-Type": "application/json", "Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request("GET", "/api/health", headers={"Host": "evil.example"})[0], 403)

    def test_unload(self):
        status, _, body = self.request("POST", "/api/unload", "{}", {"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])


if __name__ == "__main__":
    unittest.main()
