import type { GenerateSqlResponse, QueryResponse } from "../types/sql";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function generateSql(question: string): Promise<GenerateSqlResponse> {
  const response = await fetch(`${apiBaseUrl}/sql/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "SQL generation failed");
  }
  return response.json() as Promise<GenerateSqlResponse>;
}

export async function runQuery(question: string): Promise<QueryResponse> {
  const response = await fetch(`${apiBaseUrl}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, max_rows: 100 }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Query failed");
  }
  return response.json() as Promise<QueryResponse>;
}
