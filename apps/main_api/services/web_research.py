"""Web research for the fields a card leaves empty (operator-only leads).

When the approved corpus has no evidence for a card field, one OpenRouter call
with the ``openrouter:web_search`` server tool lets the model search an
allow-list of reference, government and journal sites. The model answers with
claims that each cite one URL from its own search results. Every claim then goes
through the same claim verifier as the card (field category, numbers, taxa, LLM
entailment) against the page excerpt the search returned for that URL.

Supported findings are stored in the knowledge job's trace and shown to the
operator as unverified web leads with their links. They never reach the card,
the lot snapshot or the corpus: adding a source to the approved corpus stays a
human step (scripts/corpus_pipeline.py).
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.services import claim_verifier
from apps.main_api.services.llm_output import reply_json

logger = logging.getLogger(__name__)

# Reference databases, fisheries agencies and journal publishers, the same kinds
# of source the approved corpus uses. A subdomain of a listed domain is allowed.
ALLOWED_DOMAINS = (
    "fishbase.se", "fishbase.org", "sealifebase.se", "fao.org", "fisheries.noaa.gov",
    "frdc.com.au", "fish.gov.au", "kkp.go.id", "doi.org", "sciencedirect.com",
    "springer.com", "nature.com", "wiley.com", "mdpi.com", "tandfonline.com",
    "frontiersin.org", "researchgate.net",
)
# Card field -> the evidence category the claim verifier lets ground it.
FIELD_CATEGORY = {
    "physical_characteristics": "physical_characteristics",
    "taste": "taste_texture",
    "texture": "taste_texture",
    "processing_methods": "processing_methods",
    "commercial_uses": "commercial_uses",
    "potential_buyer_segments": "commercial_uses",
    "similar_or_substitute_species": "substitutes",
}
MAX_SEARCHES = 3
RESULTS_PER_SEARCH = 5
EXCERPT_CHARS = 4000

PROMPT = """Search the web for facts about this fish, only for these card fields: {fields}.
Species: {common} ({scientific}).

Rules:
- One claim = one fact. Cite exactly one URL from your search results that states it.
- Keep the scope of the source: if it is about a processed product, one population or a related species, the claim must say so.
- Do not infer anything that is not written. Fewer claims are better than a guess.
- Write in plain English.
Answer only JSON: {{"claims": [{{"field": "<field>", "text": "<claim>", "url": "<url>"}}]}}
"""


def enabled(settings) -> bool:
    """Only on OpenRouter (the search is its server tool) and only with a key."""
    return (settings is not None and getattr(settings, "web_research_enabled", False)
            and settings.llm_provider == "openrouter" and bool(settings.llm_api_key))


def gaps(card: dict | None) -> list[str]:
    """Card fields the verified sources left empty."""
    if not card:
        return []
    return [f for f in FIELD_CATEGORY if not card.get(f)]


def _allowed(url: str, domains=ALLOWED_DOMAINS) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def search(settings, prompt: str, post=httpx.post, domains=ALLOWED_DOMAINS) -> dict:
    """One OpenRouter chat call with the web search server tool, limited to ``domains``."""
    tool = {"type": "openrouter:web_search", "parameters": {
        "engine": "exa", "max_uses": MAX_SEARCHES, "max_results": RESULTS_PER_SEARCH,
        "allowed_domains": list(domains),
    }}
    body = {"model": settings.openrouter_model, "messages": [{"role": "user", "content": prompt}], "tools": [tool]}
    if settings.opencode_go_reasoning_effort:
        body["reasoning"] = {"effort": settings.opencode_go_reasoning_effort}
    response = post(
        f"{settings.openrouter_base_url.rstrip('/')}/chat/completions", json=body,
        headers={"Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}", "X-Title": "Fishora"},
        timeout=settings.opencode_go_timeout_seconds * 2,
    )
    response.raise_for_status()
    return response.json()


def page_excerpts(message: dict, domains=ALLOWED_DOMAINS) -> dict[str, tuple[str, str]]:
    """The page excerpts the search returned, by URL: the only evidence a claim may cite."""
    excerpts: dict[str, tuple[str, str]] = {}
    for annotation in message.get("annotations") or []:
        cite = annotation.get("url_citation") or {}
        url, content = cite.get("url"), cite.get("content")
        if url and content and _allowed(url, domains) and url not in excerpts:
            excerpts[url] = (cite.get("title") or url, content[:EXCERPT_CHARS])
    return excerpts


def research(species: SpeciesRecord, fields: list[str], settings, verifier_llm,
             known_binomials=(), post=httpx.post) -> dict:
    """Search, then keep only claims the claim verifier labels ``supported``."""
    prompt = PROMPT.format(fields=", ".join(fields), common=species.common_name_id,
                           scientific=species.scientific_name or "scientific name not fixed")
    data = search(settings, prompt, post)
    message = data["choices"][0]["message"]
    excerpts = page_excerpts(message)

    claims: list[claim_verifier.Claim] = []
    chunks: dict[str, RetrievedChunk] = {}
    uncited = 0
    for item in reply_json(message.get("content") or "").get("claims", []):
        if not isinstance(item, dict):
            continue
        fld, text, url = item.get("field"), str(item.get("text") or "").strip(), str(item.get("url") or "").strip()
        if fld not in fields or not text:
            continue
        if url not in excerpts:  # not among its own search results, or off the allow-list
            uncited += 1
            continue
        chunk_id = f"web:{fld}:{url}"
        if chunk_id not in chunks:
            title, content = excerpts[url]
            # "verified" only lets the excerpt through the verifier's own gate;
            # nothing built here is stored as a chunk or shown as verified.
            chunks[chunk_id] = RetrievedChunk(
                chunk_id=chunk_id, species_id=species.id, source_id=url, source_type="web",
                category=FIELD_CATEGORY[fld], content=content, distance=0.0,
                chunk_verification_status="verified", source_verification_status="verified",
                source_title=title, source_publisher=None, source_url=url, source_reviewed_at=None,
            )
        claims.append(claim_verifier.Claim(id=len(claims), field=fld, text=text, chunk_ids=[chunk_id]))

    result = claim_verifier.verify(claims, list(chunks.values()), verifier_llm, known_binomials)
    findings = []
    for claim in result.supported():
        chunk = chunks[claim.chunk_ids[0]]
        findings.append({"field": claim.field, "text": claim.text, "url": chunk.source_url, "title": chunk.source_title})
    usage = data.get("usage") or {}
    return {
        "findings": findings,
        "checked": len(claims),
        "rejected": len(claims) - len(findings) + uncited,
        "searches": (usage.get("server_tool_use_details") or {}).get("web_search_requests"),
        "cost_usd": usage.get("cost"),
        "verifier_error": result.llm_error,
    }


def run_for_job(job_id: str, job_repo, species_repo, settings, llm) -> None:
    """Background step after a card job completes: research its empty fields and
    store the outcome under ``trace["web_research"]``. Never raises."""
    if not enabled(settings) or job_repo is None or species_repo is None or llm is None:
        return
    try:
        job = job_repo.get(job_id)
        if job is None or job.status != "completed":
            return
        fields = gaps(job.final_card)
        species = species_repo.get_by_id(job.species_id)
        if not fields or species is None:
            return
        trace = dict(job.trace or {})
        trace["web_research"] = {"status": "running", "fields": fields, "findings": []}
        job_repo.update(job_id, trace=trace)
        from apps.main_api.services.orchestrator import known_binomials

        try:
            outcome = {"status": "done", "fields": fields,
                       **research(species, fields, settings, llm, known_binomials(species_repo))}
        except Exception as exc:
            logger.warning("web research for job %s failed: %s: %s", job_id, type(exc).__name__, exc)
            outcome = {"status": "failed", "fields": fields, "findings": [], "error": type(exc).__name__}
        trace["web_research"] = outcome
        job_repo.update(job_id, trace=trace)
    except Exception:
        logger.exception("web research for job %s crashed", job_id)
