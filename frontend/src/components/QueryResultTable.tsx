import { useMemo, useState } from "react";

import type { QueryResponse } from "../types/sql";

type SortState = { column: string; direction: "asc" | "desc" } | null;

export function QueryResultTable({ data }: { data: QueryResponse["data"] }) {
  const [sort, setSort] = useState<SortState>(null);
  const rows = useMemo(() => {
    if (!sort) return data.rows;
    return [...data.rows].sort((left, right) => {
      const a = left[sort.column];
      const b = right[sort.column];
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      const comparison = typeof a === "number" && typeof b === "number"
        ? a - b
        : String(a).localeCompare(String(b), undefined, { numeric: true });
      return sort.direction === "asc" ? comparison : -comparison;
    });
  }, [data.rows, sort]);

  function toggleSort(column: string) {
    setSort((current) => current?.column === column
      ? { column, direction: current.direction === "asc" ? "desc" : "asc" }
      : { column, direction: "asc" });
  }

  if (!data.rows.length) return <p className="hint">The query returned no rows.</p>;
  return (
    <div className="result-table-wrap">
      <table>
        <thead>
          <tr>
            {data.columns.map((column) => (
              <th key={column.name}>
                <button type="button" className="sort-button" onClick={() => toggleSort(column.name)}>
                  <span>{column.name}</span>
                  <small>{sort?.column === column.name ? (sort.direction === "asc" ? "↑" : "↓") : column.data_type}</small>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {data.columns.map((column) => (
                <td key={column.name} className={row[column.name] == null ? "null-value" : ""}>
                  {row[column.name] == null ? "null" : String(row[column.name])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
