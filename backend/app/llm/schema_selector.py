import re

from app.schema.models import RelationshipMetadata, SchemaCatalog, TableMetadata

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
DERIVED_ANALYTICS_TABLES = {
    "batting_stats",
    "bowling_stats",
    "player_match_batting",
    "player_match_bowling",
    "team_season_stats",
    "head_to_head_stats",
    "venue_stats",
}
TABLE_HINTS: dict[str, set[str]] = {
    "batting_stats": {
        "batter",
        "batters",
        "batting",
        "scorer",
        "scorers",
        "player-level",
        "rank",
        "ranked",
        "individual",
    },
    "bowling_stats": {"bowler", "bowlers", "bowling", "wicket", "wickets", "economy"},
    "player_match_batting": {"single", "match", "batter", "innings", "strike", "score"},
    "player_match_bowling": {"single", "match", "bowler", "figures", "economy", "wickets"},
    "team_season_stats": {"team", "season", "wins", "losses", "percentage", "standings"},
    "head_to_head_stats": {"head", "h2h", "meetings", "pair", "record"},
    "venue_stats": {"venue", "scoring", "chasing", "outcomes", "average"},
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
        routed_view: str | None = None
        if {"head", "to"}.issubset(tokens) or "h2h" in tokens:
            routed_view = "head_to_head_stats"
        elif {"venue", "level"}.issubset(tokens):
            routed_view = "venue_stats"
        elif {"team", "season", "summary"}.issubset(tokens):
            routed_view = "team_season_stats"
        elif {"single", "match", "bowling"}.issubset(tokens):
            routed_view = "player_match_bowling"
        elif {"single", "match", "batter"}.issubset(tokens):
            routed_view = "player_match_batting"
        elif tokens & {"bowler", "bowlers"} and {"total", "wickets"}.issubset(tokens):
            routed_view = "bowling_stats"
        if routed_view:
            return [next(table for table in catalog.tables if table.name == routed_view)]
        if tokens & {"scorer", "scorers", "batter", "batters"} and tokens & {
            "run",
            "runs",
            "batting",
        }:
            return [next(table for table in catalog.tables if table.name == "batting_stats")]
        scored: list[tuple[int, TableMetadata]] = []
        for table in catalog.tables:
            if table.name in DERIVED_ANALYTICS_TABLES:
                continue
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
