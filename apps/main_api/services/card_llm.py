"""The chat model one knowledge card runs on."""


def card_llm(deps, settings, session_id: str | None):
    """The injected LLM port when present (tests, alternative providers; W2),
    else the configured provider's client (OpenRouter by default, or OpenCode
    Go) built from settings with this card's session id (a fresh one when
    None). None when the active provider has no key configured."""
    if getattr(deps, "llm", None) is not None:
        return deps.llm
    if settings is None or not settings.llm_api_key:
        return None
    from apps.main_api.services.generation import make_llm

    return make_llm(settings, session_id=session_id)
