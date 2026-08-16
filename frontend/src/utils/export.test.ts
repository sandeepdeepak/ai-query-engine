import { describe, expect, it } from "vitest";

import { toCsv } from "./export";

describe("toCsv", () => {
  it("escapes commas, quotes, and null values", () => {
    const csv = toCsv({
      columns: [
        { name: "team", data_type: "text" },
        { name: "result", data_type: "text" },
      ],
      rows: [{ team: "Mumbai, Indians", result: 'Won by "5" wickets' }, { team: null, result: "" }],
      row_count: 2,
    });

    expect(csv).toBe('team,result\n"Mumbai, Indians","Won by ""5"" wickets"\n,');
  });
});
