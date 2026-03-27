import logging

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class LLMServiceError(RuntimeError):
    pass


def _fallback_models() -> list[str]:
    raw = settings.groq_fallback_models or ""
    return [model.strip() for model in raw.split(",") if model.strip()]


def _candidate_models() -> list[str]:
    ordered = [settings.groq_model, *_fallback_models()]
    unique: list[str] = []

    for model in ordered:
        if model not in unique:
            unique.append(model)

    return unique


def _is_model_decommissioned_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "model_decommissioned" in text or "decommissioned" in text


async def generate_response(messages: list[dict[str, str]]) -> str:
    if not settings.groq_api_key:
        raise LLMServiceError("GROQ_API_KEY is not configured")

    try:
        from groq import AsyncGroq
    except ImportError as exc:
        raise LLMServiceError("Groq SDK is not installed") from exc

    client = AsyncGroq(api_key=settings.groq_api_key)

    completion = None
    last_error: Exception | None = None
    candidate_models = _candidate_models()

    for index, model_name in enumerate(candidate_models):
        try:
            completion = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
            )
            break
        except Exception as exc:
            last_error = exc

            has_more_models = index < len(candidate_models) - 1
            if has_more_models and _is_model_decommissioned_error(exc):
                next_model = candidate_models[index + 1]
                logger.warning(
                    "Groq model '%s' is unavailable. Retrying with '%s'.",
                    model_name,
                    next_model,
                )
                continue

            logger.exception("Groq API request failed for model '%s'", model_name)
            raise LLMServiceError("Failed to generate AI response") from exc

    if completion is None:
        raise LLMServiceError("Failed to generate AI response") from last_error

    if not completion.choices:
        raise LLMServiceError("LLM returned no choices")

    content = completion.choices[0].message.content
    clean_text = (content or "").strip()

    if not clean_text:
        raise LLMServiceError("LLM returned an empty response")

    return clean_text