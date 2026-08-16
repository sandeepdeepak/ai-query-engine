import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchSchema } from "../api/schema";

export function SchemaExplorer() {
  const schemaQuery = useQuery({ queryKey: ["schema"], queryFn: fetchSchema, staleTime: 15 * 60_000 });
  const [selectedTable, setSelectedTable] = useState("matches");

  if (schemaQuery.isPending) return <section className="schema-card">Loading schema…</section>;
  if (schemaQuery.isError) {
    return <section className="schema-card error">Schema unavailable. Start the FastAPI backend.</section>;
  }

  const current = schemaQuery.data.tables.find((table) => table.name === selectedTable)
    ?? schemaQuery.data.tables[0];

  return (
    <section className="schema-card" aria-labelledby="schema-title">
      <div className="schema-heading">
        <div>
          <span className="step">Verified IPL metadata</span>
          <h2 id="schema-title">Schema Explorer</h2>
        </div>
        <span className="source-badge">{schemaQuery.data.tables.length} tables</span>
      </div>
      <div className="schema-layout">
        <nav aria-label="IPL tables" className="table-list">
          {schemaQuery.data.tables.map((table) => (
            <button
              className={table.name === current.name ? "table-button active" : "table-button"}
              key={table.name}
              onClick={() => setSelectedTable(table.name)}
              type="button"
            >
              <strong>{table.name}</strong>
              <small>{table.columns.length} columns</small>
            </button>
          ))}
        </nav>
        <div className="column-panel">
          <h3>{current.name}</h3>
          <p>{current.description}</p>
          <div className="columns" role="table" aria-label={`${current.name} columns`}>
            {current.columns.map((column) => (
              <div className="column-row" role="row" key={column.name}>
                <code>{column.name}</code>
                <span>{column.data_type}</span>
                <small>{current.primary_key.includes(column.name) ? "Primary key" : column.nullable ? "Nullable" : "Required"}</small>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
