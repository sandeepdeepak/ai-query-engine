from app.llm.models import GenerateSqlResponse, GenerationStage
from app.llm.prompt_builder import SqlPromptBuilder
from app.llm.provider import SqlGenerator
from app.llm.question_clarifier import IplQuestionClarifier
from app.llm.schema_selector import SchemaSelector
from app.schema.service import SchemaService


class SqlGenerationService:
    def __init__(
        self,
        *,
        schema_service: SchemaService,
        generator: SqlGenerator,
        selector: SchemaSelector | None = None,
        prompt_builder: SqlPromptBuilder | None = None,
        clarifier: IplQuestionClarifier | None = None,
    ) -> None:
        self._schema_service = schema_service
        self._generator = generator
        self._selector = selector or SchemaSelector()
        self._prompt_builder = prompt_builder or SqlPromptBuilder()
        self._clarifier = clarifier or IplQuestionClarifier()

    async def generate(self, question: str) -> GenerateSqlResponse:
        guardrail = self._clarifier.clarify(question)
        clarification = guardrail
        analyze = getattr(self._generator, "clarify", None)
        if callable(analyze):
            clarification = await analyze(
                question=question,
                domain_hint=guardrail.interpreted_question,
            )
        interpreted_question = clarification.interpreted_question
        catalog = self._schema_service.get_catalog()
        selection_context = (
            f"{interpreted_question}\nIPL guardrail: {guardrail.interpreted_question}"
        )
        tables = self._selector.select(selection_context, catalog)
        relationships = self._selector.relationships_for(tables, catalog.relationships)
        system_prompt = self._prompt_builder.build(tables=tables, relationships=relationships)
        generation = await self._generator.generate(
            system_prompt=system_prompt, question=interpreted_question
        )
        allowed_tables = {table.name for table in tables}
        if not set(generation.tables_used).issubset(allowed_tables):
            raise ValueError("Generator referenced a table outside the selected schema")
        return GenerateSqlResponse(
            question=question,
            clarification=clarification,
            provider=self._generator.provider_name,
            model=self._generator.model_name,
            selected_tables=[table.name for table in tables],
            stages=[
                GenerationStage(name="question_clarification", status="success"),
                GenerationStage(name="schema_selection", status="success"),
                GenerationStage(name="prompt_building", status="success"),
                GenerationStage(name="sql_generation", status="success"),
            ],
            generation=generation,
        )
