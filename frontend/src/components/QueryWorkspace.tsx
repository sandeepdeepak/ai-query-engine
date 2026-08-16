import { type FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { runQuery } from "../api/sql";
import { ResultWorkbench } from "./ResultWorkbench";

const stageLabels = {
  schema_selection: "Schema selected",
  prompt_building: "Prompt constructed",
  sql_generation: "SQL generated",
  sql_validation: "SQL validated",
  execution: "Query executed",
  result_formatting: "JSON formatted",
};

const examples = [
  "Show the first 10 matches from the 2026 season",
  "List players whose last IPL season was 2024",
  "Show completed matches in Chennai ordered by match date",
];

export function QueryWorkspace() {
  const [question, setQuestion] = useState("Show matches from the 2026 season");
  const mutation = useMutation({ mutationFn: runQuery });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim().length >= 3) mutation.mutate(question.trim());
  }

  return (
    <>
      <section className="workspace" aria-labelledby="workspace-title">
        <form onSubmit={submit}>
          <span className="step">Phase 5 query workspace</span>
          <h2 id="workspace-title">Ask the IPL database</h2>
          <label htmlFor="question">Question</label>
          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Show matches from the 2026 season"
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.preventDefault();
                if (question.trim().length >= 3) mutation.mutate(question.trim());
              }
            }}
          />
          <button type="submit" disabled={mutation.isPending || question.trim().length < 3}>
            {mutation.isPending ? "Running…" : "Run Query"}
          </button>
          <p className="hint">Only validated, single-table reads execute. Press Ctrl/⌘ + Enter to run.</p>
          <div className="examples" aria-label="Example questions">
            {examples.map((example) => (
              <button type="button" key={example} onClick={() => setQuestion(example)}>{example}</button>
            ))}
          </div>
          {mutation.isError && <p className="error" role="alert">{mutation.error.message}</p>}
        </form>

        <aside aria-label="Query stages">
          <h2>Query stages</h2>
          {!mutation.data && <p className="hint">Submit a question to follow every step.</p>}
          {mutation.data && (
            <ol>
              {mutation.data.stages.map((stage, index) => (
                <li key={stage.name}>
                  <span>{index + 1}</span>
                  <p>{stageLabels[stage.name]}</p>
                  <small>Success</small>
                </li>
              ))}
            </ol>
          )}
        </aside>
      </section>

      {mutation.data && <ResultWorkbench result={mutation.data} />}
    </>
  );
}
