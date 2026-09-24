import { forwardLocalBackend } from "@/lib/local-backend";

export async function POST(request: Request): Promise<Response> {
  if (request.headers.get("Content-Type")?.split(";")[0] !== "application/json") {
    return Response.json({ error: "Use Content-Type: application/json." }, { status: 415 });
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).length > 131072) {
    return Response.json({ error: "Request is too large." }, { status: 413 });
  }
  return forwardLocalBackend("/api/predict", body);
}
