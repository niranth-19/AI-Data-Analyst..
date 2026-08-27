from groq import Groq

from app.core.config import get_settings

settings = get_settings()


class AIServiceError(Exception):
    pass


class AIConfigurationError(AIServiceError):
    pass


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if not settings.GROQ_API_KEY:
        raise AIConfigurationError(
            "GROQ_API_KEY is not configured. Add it to backend/.env to enable AI features."
        )
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY, timeout=settings.GROQ_TIMEOUT_SECONDS)
    return _client


def chat_completion(system_prompt: str, user_prompt: str) -> str:
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=settings.GROQ_MAX_TOKENS,
        )
    except AIConfigurationError:
        raise
    except Exception as exc:
        raise AIServiceError(f"AI service request failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise AIServiceError("AI service returned an empty response.")
    return content