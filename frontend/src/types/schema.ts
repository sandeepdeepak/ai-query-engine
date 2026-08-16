export type ColumnMetadata = {
  name: string;
  data_type: "text" | "integer" | "boolean" | "date" | "time" | "timestamp";
  nullable: boolean;
  description: string;
};

export type TableMetadata = {
  name: string;
  description: string;
  primary_key: string[];
  columns: ColumnMetadata[];
};

export type SchemaCatalog = {
  source: "ipl-public-api";
  dialect: "postgresql";
  generated_at: string;
  expires_at: string;
  tables: TableMetadata[];
  relationships: Array<{
    from_table: string;
    from_column: string;
    to_table: string;
    to_column: string;
  }>;
};
