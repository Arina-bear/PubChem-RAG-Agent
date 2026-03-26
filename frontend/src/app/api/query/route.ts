import { proxyRequest } from "@/app/api/_lib/backend";

export async function POST(request: Request) {
  return proxyRequest(request, "/api/query");
}
