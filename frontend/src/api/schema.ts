import type { SchemaCatalog } from "../types/schema";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function fetchSchema(): Promise<SchemaCatalog> {
  const response = await fetch(`${apiBaseUrl}/schema`);
  if (!response.ok) {
    throw new Error("Could not load IPL schema metadata");
  }
  return response.json() as Promise<SchemaCatalog>;
}
