"""The only module that knows about Laya. ML imports are deliberately lazy."""
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import threading
import time

from .validation import validate

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT / "model_sources.json").read_text())


class BusyError(RuntimeError):
    pass


def installed_version():
    try:
        return importlib.metadata.version("laya")
    except importlib.metadata.PackageNotFoundError:
        return None


def load_agent(checkpoint, device, threads):
    # Plain HTTPS downloads avoid a second native transfer runtime on older machines.
    # Keep generous first-download timeouts; callers can override all three settings.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
    try:
        import torch
        import laya
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError("Laya dependencies are missing. Run setup.sh (Linux/macOS) or setup.ps1 (Windows), then restart.") from exc
    torch.set_num_threads(threads)
    prefix = SOURCES["checkpoints"][checkpoint]
    prefix = prefix + "/" if prefix else ""
    root = snapshot_download(
        repo_id=SOURCES["repository"], revision=SOURCES["revision"],
        allow_patterns=[prefix + name for name in
                        ("rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")],
        max_workers=2,
    )
    return laya.load(str(Path(root) / prefix), device=device)


def token_report(agent, state, questions):
    """Report document truncation using the pinned SDK's actual sequence builder."""
    from laya.common import build_sequence, serialize_state
    text = serialize_state(state).replace(agent.tok.mask_token, " ")
    count = len(agent.tok(text, add_special_tokens=False)["input_ids"])
    maximum = agent.cfg.get("max_len", 512)
    head = agent.cfg.get("head_max_len", 192)
    budgets = {}
    for key, definition in questions.items():
        seq, _ = build_sequence(agent.tok, "", agent._to_internal(definition), maximum, head)
        budgets[key] = max(0, maximum - len(seq))
    return {"state_tokens": count, "context_tokens": maximum, "state_budget_by_question": budgets,
            "truncated_questions": [key for key, budget in budgets.items() if count > budget]}


class Engine:
    def __init__(self, demo=False, device="cpu", threads=2, loader=None, reporter=None):
        self.demo, self.device, self.threads = demo, device, threads
        self.loader = loader or load_agent
        self.reporter = reporter or token_report
        self._lock = threading.Lock()
        self._agent = None
        self._checkpoint = None
        self.status = "preview" if demo else "not loaded"

    def health(self):
        return {"mode": "preview" if self.demo else "laya", "status": self.status,
                "checkpoint": self._checkpoint, "requested_device": self.device,
                "actual_device": str(self._agent.device) if self._agent else None,
                "laya_version": installed_version(), "busy": self._lock.locked(),
                "threads": self.threads, "model_source": SOURCES,
                "offline": os.environ.get("HF_HUB_OFFLINE") == "1"}

    def unload(self):
        if not self._lock.acquire(blocking=False):
            raise BusyError("A model operation is running. Wait for it to finish.")
        try:
            self._release()
        finally:
            self._lock.release()

    def _release(self):
        self._agent = None
        self._checkpoint = None
        gc.collect()
        # Only import torch if it was already needed. CPU is the supported default.
        import sys
        torch = sys.modules.get("torch")
        if torch and torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.status = "preview" if self.demo else "not loaded"

    def predict(self, payload):
        request = validate(payload)
        if not self._lock.acquire(blocking=False):
            raise BusyError("Another decision is running. Wait for it to finish.")
        started = time.perf_counter()
        try:
            load_ms, cold = 0.0, False
            if self.demo:
                result = self._preview(request["questions"])
                context = None
                inference_ms = 0.0
                warnings = ["PREVIEW: synthetic display fixtures. Input text is not evaluated. These are not Laya predictions."]
                actual_device = "none"
            else:
                if self._checkpoint != request["checkpoint"] or self._agent is None:
                    self._release()
                    self.status = "downloading / loading"
                    load_start = time.perf_counter()
                    self._agent = self.loader(request["checkpoint"], self.device, self.threads)
                    self._checkpoint = request["checkpoint"]
                    load_ms = (time.perf_counter() - load_start) * 1000
                    cold = True
                self.status = "evaluating"
                context = self.reporter(self._agent, request["state"], request["questions"])
                inference_start = time.perf_counter()
                result = self._agent.predict(request["state"], request["questions"])
                inference_ms = (time.perf_counter() - inference_start) * 1000
                actual_device = str(self._agent.device)
                warnings = ["Model probabilities are not validated for your domain. Review decisions before using them."]
                if context["truncated_questions"]:
                    warnings.append("Input was truncated for: " + ", ".join(context["truncated_questions"]) + ". Shorten the state and rerun.")
                if any(len(q.get("criteria", {})) > 8 for q in request["questions"].values()):
                    warnings.append("Many options share a small question token budget. Prefer a shorter shortlist when possible.")
            self.status = "preview" if self.demo else "ready"
            return {"mode": "preview" if self.demo else "laya", "request": request,
                    "result": result, "context": context, "warnings": warnings,
                    "runtime": {"checkpoint": request["checkpoint"], "device": actual_device,
                                "laya_version": installed_version(), "cold_load": cold,
                                "model_load_ms": round(load_ms, 2), "inference_ms": round(inference_ms, 2),
                                "total_ms": round((time.perf_counter() - started) * 1000, 2),
                                "source": SOURCES}}
        except Exception:
            self.status = "error — retry or unload"
            raise
        finally:
            self._lock.release()

    @staticmethod
    def _preview(questions):
        answers = {}
        for key, q in questions.items():
            if q["type"] == "choice":
                labels = list(q["criteria"])
                probabilities = {label: round(0.28 / (len(labels) - 1), 4) for label in labels}
                probabilities[labels[0]] = 0.72
                answer = {"type": "choice", "choice": labels[0], "probabilities": probabilities, "confidence": 0.6}
            elif q["type"] == "score":
                size = len(q["criteria"])
                answer = {"type": "score", "score": (size - 1) / 2, "confidence": 0.0,
                          "legend": {str(i): label for i, label in enumerate(q["criteria"])},
                          "probabilities": {str(i): round(1 / size, 4) for i in range(size)}}
            else:
                answer = {"type": "noul", "noul": 0.64, "confidence": 0.64}
            answers[key] = answer
        return {"model": "synthetic-preview-fixture", "answers": answers,
                "usage": {"input_tokens": 0, "output_tokens": 0}}
