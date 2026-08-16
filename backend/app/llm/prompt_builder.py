from app.schema.models import RelationshipMetadata, TableMetadata


class SqlPromptBuilder:
    def build(
        self,
        *,
        tables: list[TableMetadata],
        relationships: list[RelationshipMetadata],
    ) -> str:
        schema_lines: list[str] = []
        for table in tables:
            columns = ", ".join(
                f"{column.name} {column.data_type}{' NULL' if column.nullable else ' NOT NULL'}"
                for column in table.columns
            )
            schema_lines.append(
                f"TABLE {table.name} ({columns}); PRIMARY KEY ({', '.join(table.primary_key)})"
            )

        relationship_lines = [
            f"{item.from_table}.{item.from_column} -> {item.to_table}.{item.to_column}"
            for item in relationships
        ]
        relationship_context = (
            "\n".join(relationship_lines) or "No verified relationships in context."
        )
        schema_context = "\n".join(schema_lines)
        return f"""You translate IPL questions into one PostgreSQL query.

Rules:
- Return exactly one read-only SELECT statement.
- Use only the tables and columns in the verified schema below.
- Never use INSERT, UPDATE, DELETE, DDL, COPY, functions with side effects, or multiple statements.
- Use exactly one table. Do not use joins, CTEs, subqueries, DISTINCT, GROUP BY, or HAVING.
- Do not use aggregate, scalar, date, or SQL functions; the public REST executor rejects them.
- WHERE may use AND with =, !=, >, >=, <, <=, IN, IS NULL, or IS NOT NULL.
- One OR group of equality comparisons is allowed when the user's concept can appear in
  alternative columns. In particular, a team playing in a match means
  (home_team_name = 'Team' OR away_team_name = 'Team'); never assume home or away unless
  the user explicitly says so.
- Normalize obvious team-name spelling variants to the canonical database display name.
  For example, Royal Challengers Bangalore, Royal Challengers Bangaluru, and RCB must use
  'Royal Challengers Bengaluru' in filters. Explain the normalization as an assumption.
- ORDER BY may contain columns only.
- Prefer explicit column names.
- Add LIMIT 100 unless the query returns one aggregate row or already has a lower limit.
- IPL seasons are represented by their starting year, and available data spans 2008 through 2026.
- Do not invent names. Record unavoidable interpretation choices as assumptions.
- Treat run scorer, leading scorer, top scorer, and top batter as player-level batting
  statistics. Use batting_stats and its runs column; never use innings.runs for those intents.
- innings.runs is a team innings total, not an individual batter's runs.

Verified schema:
{schema_context}

Verified relationships:
{relationship_context}
"""
