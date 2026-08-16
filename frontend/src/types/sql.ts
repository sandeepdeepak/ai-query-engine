export type GenerateSqlResponse = {
  question: string;
  provider: string;
  model: string;
  selected_tables: string[];
  clarification: {
    original_question: string;
    interpreted_question: string;
    assumptions: string[];
    entity: string;
    metric: string;
    scope: string;
    ranking: string;
    result_limit: number | null;
  };
  stages: Array<{
    name: "question_clarification" | "schema_selection" | "prompt_building" | "sql_generation";
    status: "success";
  }>;
  generation: {
    sql: string;
    explanation: string;
    tables_used: string[];
    assumptions: string[];
    confidence: number;
  };
};

export type QueryResponse = {
  question: string;
  status: "completed";
  stages: Array<{
    name: "question_clarification" | "schema_selection" | "prompt_building" | "sql_generation" | "sql_validation" | "execution" | "result_formatting";
    status: "success";
  }>;
  generation: GenerateSqlResponse;
  validation: {
    valid: true;
    query_type: "SELECT";
    normalized_sql: string;
    tables: string[];
    columns: string[];
    limit_applied: boolean;
    plan: {
      table: string;
      select: string;
      filters: Array<{ column: string; operator: string; value: string }>;
      or_filters: Array<{ column: string; operator: string; value: string }>;
      order: string | null;
      limit: number;
    };
  };
  data: {
    columns: Array<{ name: string; data_type: string }>;
    rows: Array<Record<string, unknown>>;
    row_count: number;
  };
  metadata: { execution_time_ms: number; truncated: boolean };
};
