const localBackend = "http://127.0.0.1:8765";

type BackendPath = "/api/health" | "/api/presets" | "/api/predict" | "/api/unload";

export async function forwardLocalBackend(path: BackendPath, body?: string): Promise<Response> {
  const base = process.env.LAYA_BACKEND_URL ?? localBackend;

  try {
    const response = await fetch(base.replace(/\/$/, "") + path, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(body === undefined ? 5000 : 1_200_000),
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { error: "Laya backend is offline. In a second terminal, run .\backend\run.ps1." },
      { status: 503 },
    );
  }
}
