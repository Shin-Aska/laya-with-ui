# Laya UI

This is the browser workbench. The Python API lives separately in `../backend`.

## Start

From the repository root, start `.\backend\run.ps1` in one terminal. In a second terminal:

```powershell
cd ui
corepack pnpm install
corepack pnpm dev
```

Open [http://localhost:5173](http://localhost:5173). There is no URL or token form. The UI forwards its local `/api/laya/*` requests to the Python API at `http://127.0.0.1:8765`.

For a non-default backend port on the same machine, set `LAYA_BACKEND_URL` for the UI server before starting it. Do not expose the Python API directly to the network; it is a local service.

## Checks

```powershell
corepack pnpm exec tsc --noEmit
corepack pnpm lint
corepack pnpm build
```
