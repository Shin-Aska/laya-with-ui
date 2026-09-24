# Laya Playground

A local workbench for running the real [Laya](https://github.com/NandhaKishorM/laya) decision model. The UI and backend are separate projects:

- `ui/` is the browser app. It owns the JSON editors and response view.
- `backend/` is the Python JSON API. It owns examples, validation, model loading, and inference.

The browser talks to the Python API through local UI routes. There is **no service URL or API token to enter**.

## Run on Windows

Install Python 3.11 and Node.js 22 or newer. Open PowerShell in this folder.

First-time backend setup:

```powershell
cd backend
.\setup.ps1
cd ..
```

Start the backend in one terminal:

```powershell
.\backend\run.ps1
```

Start the UI in another terminal:

```powershell
cd ui
corepack pnpm install
corepack pnpm dev
```

For VS Code, open this repository folder and select **Laya: Backend + UI** in Run and Debug. Run the first-time backend setup and `corepack pnpm install` before pressing F5. Stop any copies already using ports 8765 or 5173 before starting the compound configuration.

Open [http://localhost:5173](http://localhost:5173). The UI detects the backend automatically. The first model request downloads and loads the selected checkpoint; it can take a few minutes. Keep the backend terminal open to see progress.

If PowerShell blocks scripts, run `py -3.11 scripts/install.py` once, then `.venv\Scripts\python.exe app.py`, both from inside `backend`. The UI needs no environment file for the default local ports.

## Use the NVIDIA GPU on Windows

This workspace's VS Code **Laya: Backend** and **Laya: Backend + UI** launch configurations now start the API with `--device cuda`. The installed PyTorch wheel is `2.6.0+cu124`, and the local RTX 4060 passes `torch.cuda.is_available()`.

After recreating `backend/.venv`, run the normal setup first, stop the backend, then replace its CPU PyTorch wheel with the [official CUDA 12.4 build](https://docs.pytorch.org/get-started/previous-versions/):

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps "torch==2.6.0" --index-url https://download.pytorch.org/whl/cu124
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

See [backend/README.md](backend/README.md) for the request format and model setup. The backend serves JSON only; the UI is at port 5173.
