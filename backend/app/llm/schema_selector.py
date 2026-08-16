import re

from app.schema.models import RelationshipMetadata, SchemaCatalog, TableMetadata

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
TABLE_HINTS: dict[str, set[str]] = {
    "matches": {
        "match",
        "matches",
        "game",
        "games",
        "team",
        "teams",
        "venue",
        "city",
        "toss",
        "winner",
        "won",
        "season",
        "date",
    },
    "players": {"player", "players", "batter", "batsman", "bowler", "career"},
    "innings": {"innings", "inning", "score", "total", "wickets", "overs", "extras"},
    "deliveries": {
        "ball",
        "balls",
        "delivery",
        "deliveries",
        "run",
        "runs",
        "four",
        "fours",
        "six",
        "sixes",
        "wicket",
        "wickets",
        "dismissal",
        "batter",
        "bowler",
    },
    "seasons": {"season", "seasons", "competition", "years", "year"},
}


class SchemaSelector:
    def select(self, question: str, catalog: SchemaCatalog, limit: int = 3) -> list[TableMetadata]:
        tokens = set(TOKEN_PATTERN.findall(question.lower()))
        scored: list[tuple[int, TableMetadata]] = []
        for table in catalog.tables:
            searchable = {table.name}
            searchable.update(TOKEN_PATTERN.findall(table.description.lower()))
            for column in table.columns:
                searchable.add(column.name)
                searchable.update(column.name.split("_"))
            score = len(tokens & searchable) + 3 * len(tokens & TABLE_HINTS.get(table.name, set()))
            scored.append((score, table))

        ranked = sorted(scored, key=lambda item: (-item[0], item[1].name))
        top_score = ranked[0][0]
        relevance_threshold = max(1, (top_score + 1) // 2)
        selected = [table for score, table in ranked if score >= relevance_threshold]
        if not selected:
            selected = [next(table for table in catalog.tables if table.name == "matches")]

        selected_names = {table.name for table in selected[:limit]}
        if "deliveries" in selected_names and len(selected_names) < limit:
            players = next(table for table in catalog.tables if table.name == "players")
            selected_names.add(players.name)

        return [table for table in catalog.tables if table.name in selected_names][:limit]

    @staticmethod
    def relationships_for(
        tables: list[TableMetadata], relationships: list[RelationshipMetadata]
    ) -> list[RelationshipMetadata]:
        names = {table.name for table in tables}
        return [
            relationship
            for relationship in relationships
            if relationship.from_table in names and relationship.to_table in names
        ]
