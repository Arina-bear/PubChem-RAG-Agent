function backendUrl(path: string) {
  const base = process.env.BACKEND_BASE_URL ?? "http://127.0.0.1:8000";
  return new URL(path, base).toString();
}

export async function proxyRequest(request: Request, path: string) {
  const init: RequestInit = {
    method: request.method,
    headers: {
      "Content-Type": request.headers.get("content-type") ?? "application/json",
    },
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  const response = await fetch(backendUrl(path), init);
  const contentType = response.headers.get("content-type") ?? "application/json";
  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}

export async function proxyGet(path: string) {
  const response = await fetch(backendUrl(path), { cache: "no-store" });
  const contentType = response.headers.get("content-type") ?? "application/json";
  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}
