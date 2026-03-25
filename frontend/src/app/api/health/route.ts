import { proxyGet } from "@/app/api/_lib/backend";

export async function GET() {
  return proxyGet("/api/health");
}
