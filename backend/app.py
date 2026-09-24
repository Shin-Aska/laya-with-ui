#!/usr/bin/env python3
"""Loopback-only JSON API for the Laya workbench."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from poc.validation import MAX_BODY, InvalidRequest, parse_json

ROOT = Path(__file__).resolve().parent
class Handler(BaseHTTPRequestHandler):
    server_version = "LayaAPI/2.0"

    def log_message(self, fmt, *args):
        # Do not log request payloads or user content.
        pass

    def _send(self, status, body, kind="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _trusted(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            hosts |= {"127.0.0.1", "localhost"}
        if self.headers.get("Host") not in hosts:
            self._send(403, {"error": "Use the localhost URL printed by the launcher."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + h for h in hosts}:
            self._send(403, {"error": "Cross-origin requests are disabled."})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._send(403, {"error": "Cross-site requests are disabled."})
            return False
        return True

    def do_GET(self):
        if not self._trusted():
            return
        route = urlsplit(self.path).path
        if route == "/api/health":
            self._send(200, self.server.engine.health())
        elif route == "/api/presets":
            self._send(200, json.loads((ROOT / "examples" / "presets.json").read_text(encoding="utf-8")))
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        if not self._trusted():
            return
        from poc.engine import BusyError
        route = urlsplit(self.path).path
        if route not in ("/api/predict", "/api/unload"):
            self._send(404, {"error": "Not found"})
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise InvalidRequest("Chunked requests are not supported.")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                # Drain a near-limit body before replying so Windows clients can
                # receive the 413 instead of a reset from unread request bytes.
                if MAX_BODY < size <= MAX_BODY + 65_536:
                    self.connection.settimeout(15)
                    self.rfile.read(size)
                self._send(413, {"error": f"Request must contain 1–{MAX_BODY} bytes."})
                return
            self.connection.settimeout(15)
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise InvalidRequest("Incomplete request body.")
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self._send(415, {"error": "Use Content-Type: application/json"})
                return
            payload = parse_json(raw)
            self.connection.settimeout(None)
            if route == "/api/unload":
                self.server.engine.unload()
                self._send(200, {"ok": True})
            else:
                self._send(200, self.server.engine.predict(payload))
        except BusyError as exc:
            self._send(409, {"error": str(exc)})
        except (InvalidRequest, ValueError, TimeoutError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            # Error details stay in the terminal; URLs/tokens are not reflected into the UI.
            print(f"Model error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            self._send(503, {"error": "Model operation failed. Check the backend terminal for details, then retry."})


def make_server(engine, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.engine = engine
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use cached model files only")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"], default="cpu")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.threads <= 32:
        parser.error("Port must be 1–65535 and threads 1–32.")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from poc.engine import Engine
    engine = Engine(device=args.device, threads=args.threads)
    try:
        server = make_server(engine, args.port)
    except OSError as exc:
        parser.exit(1, f"Cannot start server: {exc}. Try --port 8766.\n")
    print(f"\nLaya API ready: http://127.0.0.1:{args.port}/api/health", flush=True)
    print("Open the UI at http://localhost:5173. First run downloads and loads the selected checkpoint.", flush=True)
    print("Press Ctrl+C to stop.\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
