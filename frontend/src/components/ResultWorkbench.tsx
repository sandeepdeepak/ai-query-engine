import { useState } from "react";

import type { QueryResponse } from "../types/sql";
import { downloadText, toCsv } from "../utils/export";
import { QueryResultTable } from "./QueryResultTable";

type ResultTab = "overview" | "sql" | "validation" | "data" | "json";
const tabs: Array<{ id: ResultTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "sql", label: "SQL" },
  { id: "validation", label: "Validation" },
  { id: "data", label: "Data" },
  { id: "json", label: "JSON" },
];

export function ResultWorkbench({ result }: { result: QueryResponse }) {
  const [activeTab, setActiveTab] = useState<ResultTab>("data");
  const [copied, setCopied] = useState(false);
  const generation = result.generation.generation;

  async function copySql() {
    await navigator.clipboard.writeText(result.validation.normalized_sql);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="result-card" aria-labelledby="result-title">
      <div className="result-heading">
        <div>
          <span className="step">Validated result</span>
          <h2 id="result-title">{result.data.row_count} rows returned</h2>
        </div>
        <div className="result-actions">
          <button type="button" className="secondary-button" onClick={() => downloadText("ipl-query.csv", toCsv(result.data), "text/csv")}>CSV</button>
          <button type="button" className="secondary-button" onClick={() => downloadText("ipl-query.json", JSON.stringify(result, null, 2), "application/json")}>JSON</button>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Result views">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >{tab.label}</button>
        ))}
      </div>

      <div className="tab-panel" role="tabpanel">
        {activeTab === "overview" && (
          <div className="overview-grid">
            <Metric label="Rows" value={String(result.data.row_count)} />
            <Metric label="Execution" value={`${result.metadata.execution_time_ms} ms`} />
            <Metric label="Provider" value={result.generation.provider} />
            <Metric label="Model" value={result.generation.model} />
            <Metric label="Confidence" value={`${Math.round(generation.confidence * 100)}%`} />
            <Metric label="Truncated" value={result.metadata.truncated ? "Yes" : "No"} />
            <div className="wide-detail">
              <h3>Interpreted IPL question</h3>
              <p>{result.generation.clarification.interpreted_question}</p>
              <div className="schema-tags">
                <code>entity: {result.generation.clarification.entity}</code>
                <code>metric: {result.generation.clarification.metric}</code>
                <code>scope: {result.generation.clarification.scope}</code>
                <code>ranking: {result.generation.clarification.ranking}</code>
              </div>
            </div>
            <div className="wide-detail">
              <h3>Explanation</h3>
              <p>{generation.explanation}</p>
            </div>
            {generation.assumptions.length > 0 && (
              <div className="wide-detail">
                <h3>Assumptions</h3>
                <ul>{generation.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "sql" && (
          <div>
            <div className="panel-toolbar">
              <p className="hint">Normalized PostgreSQL</p>
              <button type="button" className="secondary-button" onClick={copySql}>{copied ? "Copied" : "Copy SQL"}</button>
            </div>
            <pre className="sql-preview"><code>{result.validation.normalized_sql}</code></pre>
          </div>
        )}

        {activeTab === "validation" && (
          <div className="validation-grid">
            <Metric label="Status" value="Passed" tone="success" />
            <Metric label="Query type" value={result.validation.query_type} />
            <Metric label="Table" value={result.validation.plan.table} />
            <Metric label="Row limit" value={String(result.validation.plan.limit)} />
            <Metric label="Limit enforced" value={result.validation.limit_applied ? "Yes" : "No"} />
            <Metric label="Order" value={result.validation.plan.order ?? "None"} />
            <div className="wide-detail">
              <h3>Allowed columns</h3>
              <div className="schema-tags">{result.validation.columns.map((column) => <code key={column}>{column}</code>)}</div>
            </div>
            <div className="wide-detail">
              <h3>REST filters</h3>
              {result.validation.plan.filters.length
                ? result.validation.plan.filters.map((filter) => <code className="filter-code" key={`${filter.column}-${filter.operator}`}>{filter.column} {filter.operator} {filter.value}</code>)
                : <p className="hint">No filters</p>}
            </div>
            {result.validation.plan.or_filters.length > 0 && (
              <div className="wide-detail">
                <h3>Any-of filters (OR)</h3>
                {result.validation.plan.or_filters.map((filter) => <code className="filter-code" key={`${filter.column}-${filter.operator}`}>{filter.column} {filter.operator} {filter.value}</code>)}
              </div>
            )}
          </div>
        )}

        {activeTab === "data" && <QueryResultTable data={result.data} />}
        {activeTab === "json" && <pre className="json-preview"><code>{JSON.stringify(result, null, 2)}</code></pre>}
      </div>
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "success" }) {
  return (
    <div className="metric">
      <small>{label}</small>
      <strong className={tone === "success" ? "success-text" : ""}>{value}</strong>
    </div>
  );
}
