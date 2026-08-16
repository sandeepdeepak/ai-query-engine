import re

from app.llm.models import QuestionClarification


class IplQuestionClarifier:
    """Make common IPL language explicit before schema selection and SQL generation."""

    _team_aliases = {
        "rcb": "Royal Challengers Bengaluru",
        "royal challengers bangalore": "Royal Challengers Bengaluru",
        "royal challengers bangaluru": "Royal Challengers Bengaluru",
    }

    def clarify(self, question: str) -> QuestionClarification:
        normalized = " ".join(question.split())
        canonical = normalized
        assumptions: list[str] = []
        for alias, team in self._team_aliases.items():
            replaced = re.sub(rf"\b{re.escape(alias)}\b", team, canonical, flags=re.IGNORECASE)
            if replaced != canonical:
                canonical = replaced
                assumptions.append(f"Normalized '{alias}' to '{team}'.")

        if re.search(
            r"\bhighest\s+(individual\s+)?runs?\b",
            canonical,
            re.I,
        ) and not re.search(r"\b(total|season|career|aggregate|accumulated)\b", canonical, re.I):
            interpreted = (
                "Find the single highest individual batter score in one IPL match innings "
                "across all available IPL seasons. Return exactly one batter and the "
                "match-level batting figures, ordered by runs descending."
            )
            assumptions.append(
                "Without season or career wording, 'highest run' means the highest "
                "individual score in one match innings, not runs from one delivery."
            )
        elif re.search(r"\bpurple\s+cap\b", canonical, re.I):
            season = self._season(canonical)
            interpreted = (
                "Find the IPL Purple Cap winner: the single bowler with the highest "
                "season-level total of bowler-credited wickets"
            )
            if season:
                interpreted += f" in the {season} IPL season"
            interpreted += (
                ". Return exactly one bowler, ordered by wickets descending, then economy "
                "ascending as a deterministic tie-breaker."
            )
            assumptions.append(
                "'Purple Cap' means the season's leading bowler by credited wickets."
            )
        elif re.search(r"\borange\s+cap\b", canonical, re.I):
            season = self._season(canonical)
            interpreted = (
                "Find the IPL Orange Cap winner: the single batter with the highest "
                "season-level total of individual batting runs"
            )
            if season:
                interpreted += f" in the {season} IPL season"
            interpreted += ". Return exactly one batter, ordered by runs descending."
            assumptions.append(
                "'Orange Cap' means the season's leading batter by individual runs."
            )
        elif re.search(r"\b(top|highest|leading)\s+(run\s+)?scorers?\b", canonical, re.I):
            team = self._team_after_of(canonical)
            season = self._season(canonical)
            interpreted = "Rank IPL batters by their total individual batting runs"
            if team:
                interpreted += f" while batting for {team}"
            if season:
                interpreted += f" in the {season} IPL season"
            interpreted += (
                ", highest total first. Return player-level totals, not team innings totals."
            )
            assumptions.append(
                "'Run scorers' means individual batters ranked by accumulated batting runs."
            )
        elif re.search(
            r"\b(top|highest|leading|most)\s+(wicket\s+)?(takers?|wickets?)\b",
            canonical,
            re.I,
        ):
            interpreted = (
                "Rank IPL bowlers by season-level total wickets credited to the bowler, "
                "highest wickets first. Do not count run-outs or retired dismissals as "
                "bowler wickets."
            )
            interpreted = self._append_context(interpreted, canonical)
            assumptions.append("'Wicket takers' means bowler-credited season wicket totals.")
        elif re.search(
            r"\b(best bowling|bowling figures|most wickets in (a |one )?match)\b",
            canonical,
            re.I,
        ):
            interpreted = (
                "Rank single-match IPL bowling figures by wickets, then by fewer runs "
                "conceded. Return the bowler and match-level figures."
            )
            interpreted = self._append_context(interpreted, canonical)
        elif re.search(
            r"\b(highest individual score|best batting score|most runs in (a |one )?match)\b",
            canonical,
            re.I,
        ):
            interpreted = (
                "Rank single-match IPL batter innings by individual runs, highest first. "
                "Return batter and match-level batting figures."
            )
            interpreted = self._append_context(interpreted, canonical)
        elif re.search(r"\b(head[ -]to[ -]head|h2h)\b", canonical, re.I):
            interpreted = (
                "Return the IPL head-to-head record for the requested team pair, including "
                "meetings and wins for each team. " + canonical
            )
        elif re.search(
            r"\b(win percentage|most wins|team record|team performance|standings)\b",
            canonical,
            re.I,
        ):
            interpreted = (
                "Return the IPL team season summary with matches, wins, losses, ties, "
                "no-results, and win percentage. " + canonical
            )
        elif re.search(
            r"\b(venue stats|average (first innings )?score|chasing wins|batting first wins)\b",
            canonical,
            re.I,
        ):
            interpreted = (
                "Return venue-level IPL season statistics for scoring and match outcomes. "
                + canonical
            )
        else:
            interpreted = f"Using IPL cricket data, answer this request: {canonical}"

        intent = self._infer_intent(interpreted)
        return QuestionClarification(
            original_question=normalized,
            interpreted_question=interpreted,
            assumptions=assumptions,
            **intent,
        )

    @staticmethod
    def _season(question: str) -> str | None:
        match = re.search(r"\b(20\d{2})\b", question)
        return match.group(1) if match else None

    @staticmethod
    def _team_after_of(question: str) -> str | None:
        match = re.search(
            r"\bof\s+(.+?)(?:\s+(?:from|in|during)\s+(?:the\s+)?20\d{2}|\s+20\d{2}|$)",
            question,
            re.IGNORECASE,
        )
        return match.group(1).strip() if match else None

    @classmethod
    def _append_context(cls, interpreted: str, question: str) -> str:
        team = cls._team_after_of(question)
        season = cls._season(question)
        if team:
            interpreted += f" Team: {team}."
        if season:
            interpreted += f" IPL season: {season}."
        return interpreted

    @staticmethod
    def _infer_intent(interpreted: str) -> dict[str, str | int | None]:
        lowered = interpreted.lower()
        if "single highest individual batter score" in lowered:
            return {
                "entity": "batter",
                "metric": "match innings runs",
                "scope": "single_match_all_time",
                "ranking": "runs descending",
                "result_limit": 1,
            }
        if "purple cap" in lowered:
            return {
                "entity": "bowler",
                "metric": "season wickets",
                "scope": "season",
                "ranking": "wickets descending, economy ascending",
                "result_limit": 1,
            }
        if "orange cap" in lowered:
            return {
                "entity": "batter",
                "metric": "season runs",
                "scope": "season",
                "ranking": "runs descending",
                "result_limit": 1,
            }
        if "single-match ipl bowling" in lowered:
            return {
                "entity": "bowler",
                "metric": "match bowling figures",
                "scope": "single_match",
                "ranking": "wickets descending, runs conceded ascending",
                "result_limit": None,
            }
        if "head-to-head" in lowered:
            return {
                "entity": "team_pair",
                "metric": "head-to-head results",
                "scope": "requested_seasons",
                "ranking": "none",
                "result_limit": None,
            }
        return {
            "entity": "ipl_record",
            "metric": "as requested",
            "scope": "as requested",
            "ranking": "as requested",
            "result_limit": None,
        }
