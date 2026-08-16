import type { QueryResponse } from "../types/sql";

function escapeCsv(value: unknown): string {
  if (value == null) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv(data: QueryResponse["data"]): string {
  const names = data.columns.map((column) => column.name);
  const lines = [names.map(escapeCsv).join(",")];
  for (const row of data.rows) {
    lines.push(names.map((name) => escapeCsv(row[name])).join(","));
  }
  return lines.join("\n");
}

export function downloadText(filename: string, contents: string, mimeType: string): void {
  const url = URL.createObjectURL(new Blob([contents], { type: mimeType }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
