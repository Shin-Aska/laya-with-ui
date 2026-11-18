# Laya Python API

This folder contains the local JSON API and real Laya inference engine. The browser interface is in `../ui`. The backend does not serve a second web page and does not use an API token.

## Setup and run

Python 3.10–3.14 is supported (tested on 3.10, 3.11, and 3.14; 3.13 uses the same `>= 3.13` markers as 3.14; Intel macOS is limited to Python 3.10–3.12). On Windows, Python 3.14 and PowerShell are required:

```powershell
cd backend
.\setup.ps1
.\run.ps1
```

On Linux or macOS:

```bash
cd backend
bash setup.sh
bash run.sh
```

The service binds to `127.0.0.1:8765`. Open the UI separately at `http://localhost:5173`. The first prediction downloads the selected checkpoint from Hugging Face and loads it into memory. Later requests reuse it. The default is CPU with two inference threads. Use `--offline` after the model is cached, or `--port`, `--threads`, and `--device` for advanced local setups.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Model status, checkpoint, device, and version |
| GET | `/api/presets` | Built-in examples, owned by the backend |
| POST | `/api/predict` | Evaluate a state and typed questions |
| POST | `/api/unload` | Release the model from memory; body `{}` |

Example request:

```powershell
curl.exe http://127.0.0.1:8765/api/predict -H "Content-Type: application/json" --data-binary "@examples/sky-color-request.json"
```

The JSON body has `state`, `questions`, and an optional `checkpoint` (`typed-decisions`, `english`, or `multilingual`). State may be a string, object, or array. Each question has `type` (`choice`, `score`, or `noul`) and `instructions`. Instructions and criterion descriptions may be text or structured JSON. A choice needs 2–12 named options, a score needs 2–7 ordered levels, and a request needs 1–8 questions. The serialized state limit is 24,000 characters, though the model's token context is smaller.

`choice` returns a selected label and option probabilities. `score` returns a zero-based expected score and level probabilities. `noul` returns P(true). Model confidence is not measured accuracy. The API returns truncation and review warnings when relevant. Laya performs structured decisions, not OCR, PDF parsing, or arbitrary text extraction.

HTTP 400 means invalid request, 409 means another model operation is running, and 503 means a model operation failed. Check the backend terminal for details. The server accepts only loopback Host and Origin values.

## Verify

```powershell
python -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\smoke.py --offline --repeat 2
```

On Linux or macOS, use `.venv/bin/python`. The installed Laya SDK and model source are pinned in `requirements.txt` and `model_sources.json`.
