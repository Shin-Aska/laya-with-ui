import { forwardLocalBackend } from "@/lib/local-backend";

export async function POST(): Promise<Response> {
  return forwardLocalBackend("/api/unload", "{}");
}
