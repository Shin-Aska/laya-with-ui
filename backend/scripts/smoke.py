#!/usr/bin/env python3
"""Run actual model inference and verify response invariants, not semantic accuracy."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check_result(response):
    if response["mode"] != "laya":
        raise AssertionError("Smoke test requires actual inference, not preview fixtures.")
    questions = response["request"]["questions"]
    answers = response["result"]["answers"]
    assert set(answers) == set(questions)
    for key, question in questions.items():
        answer = answers[key]
        assert answer["type"] == question["type"]
        assert math.isfinite(answer["confidence"]) and 0 <= answer["confidence"] <= 1
        if answer["type"] == "choice":
            assert answer["choice"] in question["criteria"]
            assert set(answer["probabilities"]) == set(question["criteria"])
        elif answer["type"] == "score":
            assert math.isfinite(answer["score"]) and 0 <= answer["score"] <= len(question["criteria"]) - 1
        else:
            assert math.isfinite(answer["noul"]) and 0 <= answer["noul"] <= 1
        if "probabilities" in answer:
            assert all(math.isfinite(p) and 0 <= p <= 1 for p in answer["probabilities"].values())
            assert abs(sum(answer["probabilities"].values()) - 1) < 0.005
    assert response["result"]["usage"]["input_tokens"] > 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", choices=["english", "typed-decisions", "multilingual"], default="typed-decisions")
    parser.add_argument("--preset", choices=["triage", "documents", "feedback"], default="triage")
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 20:
        parser.error("repeat must be 1–20")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from poc.engine import Engine
    engine = Engine(threads=2)
    presets = json.loads((ROOT / "examples/presets.json").read_text(encoding="utf-8"))
    preset = next(p for p in presets if p["id"] == args.preset)
    if not 0 <= args.sample < len(preset["samples"]):
        parser.error("sample index is out of range")
    payload = {"state": preset["samples"][args.sample]["state"], "questions": preset["questions"], "checkpoint": args.checkpoint}
    results = []
    for i in range(args.repeat):
        print(f"Real inference {i + 1}/{args.repeat}: {args.checkpoint}", flush=True)
        result = engine.predict(payload)
        check_result(result)
        results.append(result)
        print(json.dumps({"inference_ms": result["runtime"]["inference_ms"],
                          "load_ms": result["runtime"]["model_load_ms"],
                          "answers": result["result"]["answers"]}, ensure_ascii=False), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"platform": platform.platform(), "python": platform.python_version(),
                                           "purpose": "Integration smoke test; not an accuracy benchmark", "runs": results},
                                          indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: real model output contracts validated.", flush=True)


if __name__ == "__main__":
    main()
