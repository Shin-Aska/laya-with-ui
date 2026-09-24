import { forwardLocalBackend } from "@/lib/local-backend";

export async function GET(): Promise<Response> {
  return forwardLocalBackend("/api/health");
}
