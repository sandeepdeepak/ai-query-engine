import { QueryWorkspace } from "./components/QueryWorkspace";
import { SchemaExplorer } from "./components/SchemaExplorer";

export default function App() {
  return (
    <main className="shell">
      <header>
        <p className="eyebrow">Member 1 deliverable</p>
        <h1>AI Query Engine</h1>
        <p className="subtitle">Natural language → SQL → structured data</p>
      </header>

      <QueryWorkspace />
      <SchemaExplorer />
    </main>
  );
}
