import type {
  ApiRequestResult,
  InterpretRequest,
  InterpretResponseEnvelope,
  ManualQuerySpec,
  QueryResponseEnvelope,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
const CURL_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

async function postJson<T>(path: string, body: unknown): Promise<ApiRequestResult<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const data = (await response.json()) as T;
  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

export function runQuery(spec: ManualQuerySpec): Promise<ApiRequestResult<QueryResponseEnvelope>> {
  return postJson<QueryResponseEnvelope>("/api/query", spec);
}

export function interpretText(payload: InterpretRequest): Promise<ApiRequestResult<InterpretResponseEnvelope>> {
  return postJson<InterpretResponseEnvelope>("/api/interpret", payload);
}

export function buildQueryCurl(spec: ManualQuerySpec): string {
  return [
    "curl -X POST",
    `${CURL_BASE_URL}/api/query`,
    "-H 'Content-Type: application/json'",
    `-d '${JSON.stringify(spec)}'`,
  ].join(" ");
}

export function buildInterpretCurl(text: string): string {
  return [
    "curl -X POST",
    `${CURL_BASE_URL}/api/interpret`,
    "-H 'Content-Type: application/json'",
    `-d '${JSON.stringify({ text })}'`,
  ].join(" ");
}
