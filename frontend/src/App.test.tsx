import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  it("shows the product workflow and schema explorer", async () => {
    const schema = {
      source: "ipl-public-api",
      dialect: "postgresql",
      generated_at: "2026-08-16T00:00:00Z",
      expires_at: "2026-08-16T00:15:00Z",
      relationships: [],
      tables: [{
        name: "matches",
        description: "IPL matches",
        primary_key: ["match_id"],
        columns: [{ name: "match_id", data_type: "text", nullable: false, description: "ID" }],
      }],
    };
    const generation = {
      question: "Show matches from the 2026 season",
      provider: "mock",
      model: "test-model",
      selected_tables: ["matches"],
      stages: [
        { name: "schema_selection", status: "success" },
        { name: "prompt_building", status: "success" },
        { name: "sql_generation", status: "success" },
      ],
      generation: {
        sql: "SELECT match_id FROM matches WHERE season_year = 2026 LIMIT 100",
        explanation: "Lists matches.",
        tables_used: ["matches"],
        assumptions: [],
        confidence: 0.9,
      },
    };
    const queryResponse = {
      question: generation.question,
      status: "completed",
      stages: [
        ...generation.stages,
        { name: "sql_validation", status: "success" },
        { name: "execution", status: "success" },
        { name: "result_formatting", status: "success" },
      ],
      generation,
      validation: {
        valid: true,
        query_type: "SELECT",
        normalized_sql: generation.generation.sql,
        tables: ["matches"],
        columns: ["match_id"],
        limit_applied: false,
        plan: {
          table: "matches",
          select: "match_id",
          filters: [{ column: "season_year", operator: "eq", value: "2026" }],
          or_filters: [],
          order: null,
          limit: 100,
        },
      },
      data: {
        columns: [{ name: "match_id", data_type: "text" }],
        rows: [{ match_id: "2026-01" }],
        row_count: 1,
      },
      metadata: { execution_time_ms: 20, truncated: false },
    };
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => schema })
      .mockResolvedValueOnce({ ok: true, json: async () => queryResponse }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    );

    expect(screen.getByRole("heading", { name: "AI Query Engine" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Query" })).toBeEnabled();
    expect(await screen.findByRole("heading", { name: "Schema Explorer" })).toBeInTheDocument();
    expect(await screen.findByText("1 tables")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run Query" }));
    expect(await screen.findByText("2026-01")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "SQL" }));
    expect(screen.getByText(generation.generation.sql)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Overview" }));
    expect(screen.getByText("90%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Validation" }));
    expect(screen.getByText("season_year eq 2026")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "JSON" }));
    expect(screen.getByText(/"status": "completed"/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
