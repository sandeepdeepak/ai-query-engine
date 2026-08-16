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

        if re.search(r"\b(top|highest|leading)\s+(run\s+)?scorers?\b", canonical, re.I):
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
        else:
            interpreted = f"Using IPL cricket data, answer this request: {canonical}"

        return QuestionClarification(
            original_question=normalized,
            interpreted_question=interpreted,
            assumptions=assumptions,
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
