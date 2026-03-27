from app.core.config import get_settings

settings = get_settings()


def call_llm(prompt: str) -> str:
    if settings.llm_provider == "mock":
        return (
            "Here is your personalized guidance: prioritize a 6-month emergency fund, "
            "keep EMI below 30% of income, and automate your goal SIP contributions. "
            "Your question was analyzed with your latest profile context."
        )

    return "LLM provider integration pending."
