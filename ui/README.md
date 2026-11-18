# Laya UI

This is the browser workbench. The Python API lives separately in `../backend`.

## Start

On Windows, run `.\setup.ps1` once from the repository root (it installs backend + UI dependencies, provisions `ui/.openai/hosting.json`, and builds the UI), then run `.\run.ps1`.

Or start manually in two terminals:

1. From the repository root, start `.\backend\run.ps1`.
2. In a second terminal:

```powershell
cd ui
npm ci --include=dev --include=optional
npm run dev
```

(`pnpm install` / `pnpm dev` also works if `pnpm` is installed. On Windows, `scripts/run-framework.mjs dev` builds and serves via local Wrangler automatically unless `LAYA_USE_VINEXT_DEV=1` is set.)

Open [http://localhost:5173](http://localhost:5173). There is no URL or token form. The UI forwards its local `/api/laya/*` requests to the Python API at `http://127.0.0.1:8765`.

For a non-default backend port on the same machine, set `LAYA_BACKEND_URL` for the UI server before starting it (or pass `-BackendPort` / `-UiPort` to `..\run.ps1`). Do not expose the Python API directly to the network; it is a local service.

## Checks

```powershell
npx tsc --noEmit
npm run lint
npm run build
```
