from functools import lru_cache

from app.core.config import get_settings
from app.llm.provider import MockSqlGenerator, OpenAiSqlGenerator, SqlGenerator


class AiProviderConfigurationError(RuntimeError):
    pass


@lru_cache
def get_sql_generator() -> SqlGenerator:
    settings = get_settings()
    if settings.ai_provider == "mock":
        return MockSqlGenerator()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise AiProviderConfigurationError("OpenAI API key is not configured")
    return OpenAiSqlGenerator(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
    )
