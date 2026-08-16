from collections.abc import Iterable
from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from app.query.models import QueryPlan, RestFilter, ValidationResult
from app.schema.models import SchemaCatalog, TableMetadata


class SqlValidationError(ValueError):
    pass


@dataclass(frozen=True)
class FilterValue:
    value: str


COMPARISON_OPERATORS: dict[type[exp.Expression], str] = {
    exp.EQ: "eq",
    exp.NEQ: "neq",
    exp.GT: "gt",
    exp.GTE: "gte",
    exp.LT: "lt",
    exp.LTE: "lte",
}


class SqlValidator:
    def validate(self, sql: str, catalog: SchemaCatalog, max_rows: int = 100) -> ValidationResult:
        try:
            statements = parse(sql, read="postgres")
        except ParseError as exc:
            raise SqlValidationError("SQL could not be parsed") from exc

        if len(statements) != 1 or not isinstance(statements[0], exp.Select):
            raise SqlValidationError("Exactly one SELECT statement is required")
        statement = statements[0]
        self._reject_unsupported_structure(statement)

        tables = list(statement.find_all(exp.Table))
        table_names = {table.name for table in tables}
        if len(table_names) != 1:
            raise SqlValidationError("Exactly one catalog table is required")
        table_name = next(iter(table_names))
        table = self._get_table(catalog, table_name)
        known_columns = {column.name for column in table.columns}

        selected_columns, select_param = self._projections(statement, known_columns)
        referenced_columns = {column.name for column in statement.find_all(exp.Column)}
        unknown_columns = referenced_columns - known_columns
        if unknown_columns:
            names = ", ".join(sorted(unknown_columns))
            raise SqlValidationError(f"Unknown columns for {table_name}: {names}")

        filters, or_filters = self._filters(statement.args.get("where"), known_columns)
        order = self._order(statement.args.get("order"), known_columns)
        requested_limit = self._limit(statement.args.get("limit"))
        effective_limit = min(requested_limit or max_rows, max_rows)
        limit_applied = requested_limit is None or requested_limit > max_rows
        normalized_statement = statement.copy().limit(effective_limit)

        return ValidationResult(
            valid=True,
            query_type="SELECT",
            normalized_sql=normalized_statement.sql(dialect="postgres"),
            tables=[table_name],
            columns=sorted(referenced_columns | selected_columns),
            limit_applied=limit_applied,
            plan=QueryPlan(
                table=table_name,
                select=select_param,
                filters=filters,
                or_filters=or_filters,
                order=order,
                limit=effective_limit,
            ),
        )

    @staticmethod
    def _reject_unsupported_structure(statement: exp.Select) -> None:
        if statement.args.get("joins"):
            raise SqlValidationError("Joins are not supported by the public IPL REST executor")
        if statement.args.get("group") or statement.args.get("having"):
            raise SqlValidationError("GROUP BY and HAVING are not supported by the IPL REST API")
        if statement.args.get("distinct"):
            raise SqlValidationError("DISTINCT is not supported by the IPL REST executor")
        if statement.args.get("with") or next(statement.find_all(exp.Subquery), None):
            raise SqlValidationError(
                "CTEs and subqueries are not supported by the IPL REST executor"
            )
        if next(statement.find_all(exp.AggFunc), None):
            raise SqlValidationError("Aggregate functions are disabled by the IPL REST API")
        functions = (
            function
            for function in statement.find_all(exp.Func)
            if not isinstance(function, (exp.And, exp.Or))
        )
        if next(functions, None):
            raise SqlValidationError("SQL functions are not supported by the IPL REST executor")
        if statement.args.get("locks") or statement.args.get("into"):
            raise SqlValidationError("Locking and SELECT INTO are not allowed")

    @staticmethod
    def _get_table(catalog: SchemaCatalog, table_name: str) -> TableMetadata:
        table = next((item for item in catalog.tables if item.name == table_name), None)
        if table is None:
            raise SqlValidationError(f"Unknown table: {table_name}")
        return table

    @staticmethod
    def _projections(statement: exp.Select, known_columns: set[str]) -> tuple[set[str], str]:
        columns: set[str] = set()
        selections: list[str] = []
        for projection in statement.expressions:
            if isinstance(projection, exp.Star):
                return known_columns, "*"
            if isinstance(projection, exp.Column):
                columns.add(projection.name)
                selections.append(projection.name)
                continue
            if isinstance(projection, exp.Alias) and isinstance(projection.this, exp.Column):
                columns.add(projection.this.name)
                selections.append(f"{projection.alias}:{projection.this.name}")
                continue
            raise SqlValidationError("Only columns, column aliases, or * may be selected")
        if not selections:
            raise SqlValidationError("At least one result column is required")
        return columns, ",".join(selections)

    def _filters(
        self, where: exp.Where | None, known_columns: set[str]
    ) -> tuple[list[RestFilter], list[RestFilter]]:
        if where is None:
            return [], []
        predicates = list(self._flatten_and(where.this))
        filters: list[RestFilter] = []
        or_filters: list[RestFilter] = []
        for predicate in predicates:
            if isinstance(predicate, exp.Paren):
                predicate = predicate.this
            if isinstance(predicate, exp.Or):
                if or_filters:
                    raise SqlValidationError("Only one OR filter group is supported")
                alternatives = list(self._flatten_or(predicate))
                if len(alternatives) < 2 or len(alternatives) > 4:
                    raise SqlValidationError("OR requires between 2 and 4 comparisons")
                or_filters = [self._predicate(item, known_columns) for item in alternatives]
                if any(item.operator != "eq" for item in or_filters):
                    raise SqlValidationError("OR supports equality comparisons only")
            else:
                filters.append(self._predicate(predicate, known_columns))
        return filters, or_filters

    def _predicate(self, predicate: exp.Expression, known_columns: set[str]) -> RestFilter:
        if type(predicate) in COMPARISON_OPERATORS:
            column, value = self._column_and_value(predicate.this, predicate.expression)
            self._ensure_column(column, known_columns)
            return RestFilter(
                column=column,
                operator=COMPARISON_OPERATORS[type(predicate)],
                value=value.value,
            )
        if isinstance(predicate, exp.Is) and isinstance(predicate.this, exp.Column):
            if isinstance(predicate.expression, exp.Null):
                self._ensure_column(predicate.this.name, known_columns)
                return RestFilter(column=predicate.this.name, operator="is", value="null")
        if isinstance(predicate, exp.Not) and isinstance(predicate.this, exp.Is):
            inner = predicate.this
            if isinstance(inner.this, exp.Column) and isinstance(inner.expression, exp.Null):
                self._ensure_column(inner.this.name, known_columns)
                return RestFilter(column=inner.this.name, operator="is", value="not.null")
        if isinstance(predicate, exp.In) and isinstance(predicate.this, exp.Column):
            self._ensure_column(predicate.this.name, known_columns)
            values = [self._literal(item).value for item in predicate.expressions]
            if not values or len(values) > 50:
                raise SqlValidationError("IN requires between 1 and 50 literal values")
            return RestFilter(
                column=predicate.this.name,
                operator="in",
                value=f"({','.join(values)})",
            )
        raise SqlValidationError("WHERE supports AND, comparisons, IN, and NULL checks only")

    @staticmethod
    def _flatten_and(expression: exp.Expression) -> Iterable[exp.Expression]:
        if isinstance(expression, exp.And):
            yield from SqlValidator._flatten_and(expression.left)
            yield from SqlValidator._flatten_and(expression.right)
        else:
            yield expression

    @staticmethod
    def _flatten_or(expression: exp.Expression) -> Iterable[exp.Expression]:
        if isinstance(expression, exp.Or):
            yield from SqlValidator._flatten_or(expression.left)
            yield from SqlValidator._flatten_or(expression.right)
        elif isinstance(expression, exp.And):
            raise SqlValidationError("Nested AND inside an OR group is not supported")
        else:
            yield expression

    def _column_and_value(
        self, left: exp.Expression, right: exp.Expression
    ) -> tuple[str, FilterValue]:
        if isinstance(left, exp.Column):
            return left.name, self._literal(right)
        if isinstance(right, exp.Column):
            raise SqlValidationError("Put the column on the left side of the comparison")
        raise SqlValidationError("A comparison must use one column and one literal")

    @staticmethod
    def _literal(expression: exp.Expression) -> FilterValue:
        if isinstance(expression, exp.Literal):
            value = expression.this
            if expression.is_string and any(char in value for char in ',.():"'):
                value = '"' + value.replace('"', '\\"') + '"'
            return FilterValue(value=value)
        if isinstance(expression, exp.Boolean):
            return FilterValue(value=str(expression.this).lower())
        if isinstance(expression, exp.Null):
            return FilterValue(value="null")
        raise SqlValidationError("Filter values must be literals")

    @staticmethod
    def _ensure_column(column: str, known_columns: set[str]) -> None:
        if column not in known_columns:
            raise SqlValidationError(f"Unknown filter column: {column}")

    @staticmethod
    def _order(order: exp.Order | None, known_columns: set[str]) -> str | None:
        if order is None:
            return None
        values: list[str] = []
        for ordered in order.expressions:
            if not isinstance(ordered.this, exp.Column):
                raise SqlValidationError("ORDER BY supports columns only")
            column = ordered.this.name
            SqlValidator._ensure_column(column, known_columns)
            direction = "desc" if ordered.args.get("desc") else "asc"
            values.append(f"{column}.{direction}")
        return ",".join(values)

    @staticmethod
    def _limit(limit: exp.Limit | None) -> int | None:
        if limit is None:
            return None
        expression = limit.expression
        if not isinstance(expression, exp.Literal) or expression.is_string:
            raise SqlValidationError("LIMIT must be a positive integer")
        value = int(expression.this)
        if value < 1:
            raise SqlValidationError("LIMIT must be a positive integer")
        return value
