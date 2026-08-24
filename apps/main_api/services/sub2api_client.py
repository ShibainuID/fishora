from langchain_openai import ChatOpenAI


def make_sub2api_llm(settings, model: str | None = None, timeout: float | None = None):
    """Factory for sub2api-compatible ChatOpenAI.

    Keeps SecretStr handling identical to OpenCodeGoClient: only get_secret_value()
    leaves the settings object. Blank key is rejected at construction time, not at
    settings import, so empty-evidence paths never need a key.
    """
    api_key = settings.sub2api_api_key.get_secret_value()
    if not api_key:
        raise ValueError("FISHORA_SUB2API_API_KEY must be set to construct sub2api client")
    return ChatOpenAI(
        model=model or settings.opencode_go_model,
        base_url=settings.sub2api_base_url,
        api_key=api_key,
        timeout=timeout if timeout is not None else settings.opencode_go_timeout_seconds,
    )


def make_medium_llm(settings, timeout: float | None = None):
    return make_sub2api_llm(settings, model=settings.llm_medium_model, timeout=timeout)


def make_luna_llm(settings, timeout: float | None = None):
    return make_sub2api_llm(settings, model=settings.opencode_go_model, timeout=timeout)
