# Laya Playground

A local workbench for running the real [Laya](https://github.com/NandhaKishorM/laya) decision model. The UI and backend are separate projects:

- `ui/` is the browser app. It owns the JSON editors and response view.
- `backend/` is the Python JSON API. It owns examples, validation, model loading, and inference.

The browser talks to the Python API through local UI routes. There is **no service URL or API token to enter**.

## Run on Windows

Install Python 3.14 and Node.js 22.13 or newer. Open PowerShell in this folder.

One-time setup (Python 3.14, CPU mode, no GPU required; creates `backend/.venv`, provisions `ui/.openai/hosting.json`, installs UI packages, and builds the UI):

```powershell
.\setup.ps1
```

If PowerShell blocks local scripts, run setup and launch with `-ExecutionPolicy Bypass`:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Start both the backend and UI together (defaults to ports `8765` and `5173`; pass `-UiPort 5174` or `-BackendPort 8766` if either port is in use):

```powershell
.\run.ps1
```

Or run them in separate terminals (`.\backend\run.ps1` and `cd ui; npm run dev`). On Windows, `npm run dev` (`ui/scripts/run-framework.mjs dev`) automatically builds and serves via local Wrangler because `vinext dev`'s `workerd` runner can fail on `/`; set `LAYA_USE_VINEXT_DEV=1` to opt into `vinext dev`.

For VS Code, open this repository folder and select **Laya: Backend + UI** in Run and Debug. Run `.\setup.ps1` once before pressing F5. Stop any copies already using ports 8765 or 5173 before starting the compound configuration.

For JetBrains IDEs, open this repository folder and select **Laya: Backend + UI** from the run configuration menu. The shared `.run/` entries also let you run or debug **Laya: Backend** and **Laya: UI** separately. Run `.\setup.ps1` once first; the backend configuration uses `backend/.venv/Scripts/python.exe` rather than the project's default interpreter. Stop any copies already using ports 8765 or 5173 before launching both. Use a JetBrains IDE with Python and Node.js run/debug support.

Open [http://localhost:5173](http://localhost:5173) (or the `-UiPort` you passed). The UI detects the backend automatically. The first model request downloads and loads the selected checkpoint; it can take a few minutes. Keep the backend terminal open to see progress.

If PowerShell blocks scripts for manual steps, run `py -3.14 scripts/install.py` once, then `.venv\Scripts\python.exe app.py`, both from inside `backend`. The UI needs no environment file for the default local ports.

## Use the NVIDIA GPU on Windows

This workspace's VS Code and JetBrains **Laya: Backend** and **Laya: Backend + UI** launch configurations default to `--device cpu`. If you have an NVIDIA GPU, pass `--device cuda` instead and replace the CPU PyTorch wheel with the [official CUDA build](https://pytorch.org/get-started/locally/) matching your Python version (for example `cu128` for Python 3.14, or `cu124` for Python 3.10–3.12):

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps torch --index-url https://download.pytorch.org/whl/cu128
.\backend\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"
.\backend\run.ps1 --device cuda
```

The check should print `True`. After one prediction, `/api/health` reports `actual_device: "cuda"`. The UI connects to the same backend automatically.

## Run on Linux or macOS

From this folder, run `bash backend/setup.sh` once. Then use two terminals: `bash backend/run.sh` and `cd ui && corepack pnpm install && corepack pnpm dev`.

## Use the playground

The first example is the supplied sky-color JSON with structured instructions and criteria. Edit **State** and **Questions**, choose a checkpoint, and press **Run request**. Other examples cover support triage, document routing, and feedback. The response is produced by the real model, so its values may differ from the JEV screenshot.

Laya supports `choice`, `score`, and `noul` (yes/no probability) questions. State can be text or JSON. Choice descriptions and instructions can be JSON objects. The Python API validates all requests and limits them to eight questions.

## API

The backend listens only on `127.0.0.1:8765`. Its routes are `GET /api/health`, `GET /api/presets`, `POST /api/predict`, and `POST /api/unload`. For a direct test:

```powershell
curl.exe http://127.0.0.1:8765/api/health
```

See [backend/README.md](backend/README.md) for the request format and model setup. The backend serves JSON only; the UI defaults to port 5173 (or whichever `--port` you pass, such as 5174).
