"""Background LangGraph-style orchestration for Fishora.

Ponytail: no hard dependency on langgraph library. The graph is plain
Python + asyncio fan-out, but exposes a LangGraph-compatible `make_graph`
that falls back to a dict-based executor if langgraph is absent. Either way
the four experts really overlap (asyncio.gather over worker threads, since
the LLM calls block on I/O) -- see tests/main_api/test_orchestrator.py.

Grounding is fail-closed and centralised: the critic grades every claim
against the specific chunk it cites, the writer keeps only ``supported``
claims, and the card itself is built by ``KnowledgeGenerator`` so this path
inherits the same citation and empty-evidence invariants as the sync one.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, ValidationError

from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.errors import InvalidGeneratedKnowledge
from apps.main_api.services.generation import (
    GeneratedKnowledgeCard,
    KnowledgeCard,
    KnowledgeGenerator,
)
from apps.main_api.services.retrieval import CATEGORY_ORDER, VerifiedRetriever

# ponytail: try langgraph, fallback to simple executor if not installed
try:
    from langgraph.graph import StateGraph, START, END  # type: ignore
    _HAS_LANGGRAPH = True
except Exception:
    StateGraph = None  # type: ignore
    START = "START"  # type: ignore
    END = "END"  # type: ignore
    _HAS_LANGGRAPH = False

EXPERT_NAMES = ("physical", "taste", "commercial", "substitute")


class ClaimStatus(BaseModel):
    """Per-claim grounding verdict. ``chunk_ids`` are the specific verified
    chunks that carry the claim; the writer accepts only ``supported``."""

    field: str
    status: Literal["supported", "unsupported", "no_evidence"]
    chunk_ids: list[str]
    reason: str


def merge_expert_outputs(left: dict | None, right: dict | None) -> dict:
    """Fan-out reducer: four experts write the same state key concurrently, and
    without a reducer langgraph rejects that and a plain dict loses updates."""
    return {**(left or {}), **(right or {})}


class FishoraState(TypedDict, total=False):
    job_id: str
    prediction_id: str
    species_id: str
    species: SpeciesRecord
    broad_evidence: list[RetrievedChunk]
    refined_evidence: list[RetrievedChunk]
    expert_outputs: Annotated[dict, merge_expert_outputs]
    claim_statuses: list[ClaimStatus]
    critic_feedback: str | None
    final_card: KnowledgeCard | dict | None
    error: str | None


# ---- Hybrid researcher -------------------------------------------------

CARD_QUERY = (
    "Buat kartu pengetahuan bahasa Indonesia untuk {common_name}: identitas, "
    "ciri fisik, rasa dan tekstur, cara pengolahan, penggunaan komersial, dan "
    "spesies pengganti."
)


def hybrid_researcher(state: FishoraState, knowledge_repo, embedder, llm_medium=None) -> dict:
    """Broad search (6) + conditional re-query for empty categories (max 2 rounds)."""
    species_id = state["species_id"]
    species = state.get("species")
    common = species.common_name_id if species else species_id
    query = CARD_QUERY.format(common_name=common)
    # broad path reuses VerifiedRetriever logic without extra LLM
    retriever = VerifiedRetriever(knowledge_repo, embedder)
    broad = retriever.retrieve(species_id, query, max_chunks=6)
    refined = list(broad)
    # check missing categories
    present = {c.category for c in refined}
    missing = [c for c in CATEGORY_ORDER if c not in present]
    if missing and llm_medium is not None and len(refined) < 6:
        # One LLM sub-query for the first missing category (bounded)
        cat = missing[0]
        prompt = f"Untuk spesies {common}, buat query pencarian untuk kategori {cat} dalam bahasa Indonesia, 1 kalimat."
        try:
            sub_query = llm_medium.invoke(prompt)
            # langchain returns AIMessage, handle both str and message
            if hasattr(sub_query, "content"):
                sub_query = sub_query.content
            sub_query = str(sub_query).strip()[:200]
            if sub_query:
                extra = retriever.retrieve(species_id, sub_query, max_chunks=2)
                seen = {c.chunk_id for c in refined}
                for c in extra:
                    if c.chunk_id not in seen and len(refined) < 6:
                        refined.append(c)
                        seen.add(c.chunk_id)
        except Exception:
            pass  # fallback to broad only
    return {"broad_evidence": broad, "refined_evidence": refined}


# ---- Expert nodes (luna) -----------------------------------------------

_EXPERT_PROMPTS = {
    "physical": "Tulis physical_characteristics dari bukti kategori physical_characteristics dan identity. Jika tidak ada, null. Jawab JSON {\"physical_characteristics\": str|null, \"sources\": [{\"source_id\": str, \"chunk_id\": str}]}",
    "taste": "Tulis taste dan texture dari bukti taste_texture. Jika tidak ada, null. JSON {\"taste\": str|null, \"texture\": str|null, \"sources\": [{\"source_id\": str, \"chunk_id\": str}]}",
    "commercial": "Tulis processing_methods dan commercial_uses dari bukti processing_methods dan commercial_uses. JSON {\"processing_methods\": [], \"commercial_uses\": [], \"sources\": [{\"source_id\": str, \"chunk_id\": str}]}",
    "substitute": "Tulis similar_or_substitute_species dan potential_buyer_segments dari bukti substitutes dan commercial_uses. JSON {\"similar_or_substitute_species\": [], \"potential_buyer_segments\": [], \"sources\": [{\"source_id\": str, \"chunk_id\": str}]}",
}

_EXPERT_CATEGORIES = {
    "physical": {"physical_characteristics", "identity"},
    "taste": {"taste_texture"},
    "commercial": {"processing_methods", "commercial_uses"},
    "substitute": {"substitutes", "commercial_uses"},
}

# Which card fields each expert is allowed to claim; drives per-claim grading.
_EXPERT_CLAIM_FIELDS = {
    "physical": ("physical_characteristics",),
    "taste": ("taste", "texture"),
    "commercial": ("processing_methods", "commercial_uses"),
    "substitute": ("similar_or_substitute_species", "potential_buyer_segments"),
}
_CLAIM_OWNER = {
    field: expert for expert, fields in _EXPERT_CLAIM_FIELDS.items() for field in fields
}

_EMPTY_EXPERT_CLAIMS = {
    "physical": {"physical_characteristics": None},
    "taste": {"taste": None, "texture": None},
    "commercial": {"processing_methods": [], "commercial_uses": []},
    "substitute": {"similar_or_substitute_species": [], "potential_buyer_segments": []},
}


def _bind_citations(raw_sources, subset: list[RetrievedChunk]) -> list[dict]:
    """Tie every citation to one specific retrieved chunk (HANDOFF 9 P0.1).

    A bare source_id is resolved only when the source contributes exactly one
    chunk to this expert's evidence, so the chunk is determined, not guessed.
    """
    by_chunk = {chunk.chunk_id: chunk for chunk in subset}
    chunks_by_source: dict[str, list[str]] = {}
    for chunk in subset:
        chunks_by_source.setdefault(chunk.source_id, []).append(chunk.chunk_id)
    bound: list[dict] = []
    seen: set[str] = set()
    for entry in raw_sources or []:
        if not isinstance(entry, dict):
            continue
        chunk_id = entry.get("chunk_id")
        if chunk_id not in by_chunk:
            candidates = chunks_by_source.get(entry.get("source_id"), [])
            chunk_id = candidates[0] if len(candidates) == 1 else None
        if chunk_id is None or chunk_id in seen:
            continue
        bound.append({"source_id": by_chunk[chunk_id].source_id, "chunk_id": chunk_id})
        seen.add(chunk_id)
    return bound[:3]


def _expert_node(category: str, state: FishoraState, llm_luna) -> dict:
    evidence = state.get("refined_evidence", [])
    if llm_luna is None:
        # No LLM available (tests / empty sub2api key): claim nothing rather
        # than error, and let the writer decide whether that is fatal.
        return {**_EMPTY_EXPERT_CLAIMS[category], "sources": []}
    # No cross-category fallback: giving an expert evidence outside its own
    # categories is exactly how off-topic claims get a plausible citation.
    subset = [c for c in evidence if c.category in _EXPERT_CATEGORIES[category]]
    payload = "\n".join(
        f"[chunk_id: {c.chunk_id}] [source_id: {c.source_id}] [{c.category}] {c.content[:300]}"
        for c in subset
    )
    prompt = _EXPERT_PROMPTS[category] + f"\nBukti:\n{payload}"
    try:
        raw = llm_luna.invoke(prompt)
        if hasattr(raw, "content"):
            raw = raw.content
        data = json.loads(str(raw)) if isinstance(raw, str) else raw
        data["sources"] = _bind_citations(data.get("sources"), subset)
    except Exception:
        data = {**_EMPTY_EXPERT_CLAIMS[category], "error": "expert generation failed", "sources": []}
    return data


def physical_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {"physical": _expert_node("physical", state, llm_luna)}}


def taste_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {"taste": _expert_node("taste", state, llm_luna)}}


def commercial_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {"commercial": _expert_node("commercial", state, llm_luna)}}


def substitute_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {"substitute": _expert_node("substitute", state, llm_luna)}}


# ---- Critic (medium) ---------------------------------------------------

# Function words carry no grounding signal, so overlap on them would let any
# citation pass the content check.
_STOPWORDS = frozenset({
    "adalah", "akan", "atau", "bagi", "banyak", "bisa", "dalam", "dapat",
    "dari", "dengan", "hingga", "ikan", "itu", "juga", "karena", "kemudian",
    "lain", "lebih", "namun", "oleh", "pada", "paling", "sangat", "sebagai",
    "serta", "setelah", "sudah", "telah", "terhadap", "tetapi", "tidak",
    "untuk", "yang",
})


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[0-9a-z]{4,}", text.lower())} - _STOPWORDS


def _claim_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return " ".join(str(item) for item in value)


def _is_verified(chunk: RetrievedChunk | None) -> bool:
    return (
        chunk is not None
        and chunk.chunk_verification_status == "verified"
        and chunk.source_verification_status == "verified"
    )


def _grade_claim(field: str, value, citations, by_chunk: dict) -> ClaimStatus:
    """Grade one claim: it must be tied to a verified retrieved chunk whose
    content actually shares vocabulary with the claim."""
    text = _claim_text(value).strip()
    if not text:
        return ClaimStatus(field=field, status="no_evidence", chunk_ids=[], reason="tidak ada klaim")
    cited = [c["chunk_id"] for c in citations if _is_verified(by_chunk.get(c.get("chunk_id")))]
    if not cited:
        return ClaimStatus(
            field=field, status="unsupported", chunk_ids=[],
            reason="klaim tidak terikat pada chunk terverifikasi",
        )
    claim_tokens = _tokens(text)
    grounded = [cid for cid in cited if claim_tokens & _tokens(by_chunk[cid].content)]
    if not grounded:
        return ClaimStatus(
            field=field, status="unsupported", chunk_ids=[],
            reason="isi chunk yang disitasi tidak menyebut klaim",
        )
    return ClaimStatus(
        field=field, status="supported", chunk_ids=grounded,
        reason="didukung isi chunk terverifikasi",
    )


def _llm_downgrade(statuses: list[ClaimStatus], by_chunk: dict, llm_medium) -> list[ClaimStatus]:
    """One bounded adjudication pass. It may only downgrade: an LLM outage or a
    malformed answer must never turn an ungrounded claim into a supported one."""
    supported = [s for s in statuses if s.status == "supported"]
    if not supported:
        return statuses
    claims = {
        s.field: [by_chunk[cid].content[:300] for cid in s.chunk_ids] for s in supported
    }
    prompt = (
        "Untuk setiap field, tentukan apakah kutipan bukti mendukung klaim. "
        "Jawab JSON {field: \"supported\"|\"unsupported\"}.\n"
        f"Klaim dan bukti: {json.dumps(claims, ensure_ascii=False)}"
    )
    try:
        raw = llm_medium.invoke(prompt)
        if hasattr(raw, "content"):
            raw = raw.content
        verdicts = json.loads(str(raw)) if isinstance(raw, str) else raw
    except Exception:
        return statuses
    if not isinstance(verdicts, dict):
        return statuses
    return [
        s.model_copy(update={"chunk_ids": [], "status": "unsupported", "reason": "ditolak critic LLM"})
        if s.status == "supported" and verdicts.get(s.field) == "unsupported"
        else s
        for s in statuses
    ]


def critic_node(state: FishoraState, llm_medium=None) -> dict:
    evidence = state.get("refined_evidence", [])
    by_chunk = {chunk.chunk_id: chunk for chunk in evidence}
    outputs = state.get("expert_outputs", {})
    statuses: list[ClaimStatus] = []
    for expert, fields in _EXPERT_CLAIM_FIELDS.items():
        data = outputs.get(expert) or {}
        citations = [c for c in data.get("sources", []) if isinstance(c, dict)]
        for field in fields:
            statuses.append(_grade_claim(field, data.get(field), citations, by_chunk))
    if llm_medium is not None:
        statuses = _llm_downgrade(statuses, by_chunk, llm_medium)
    feedback = "; ".join(f"{s.field}={s.status}" for s in statuses)
    return {"claim_statuses": statuses, "critic_feedback": feedback}


# ---- Writer (luna) ------------------------------------------------------

def _supported_claims(outputs: dict, statuses: list[ClaimStatus]) -> dict:
    """Only ``supported`` claims survive into the card (HANDOFF 9 P0.3)."""
    claims: dict = {}
    for status in statuses:
        if status.status != "supported":
            continue
        owner = _CLAIM_OWNER.get(status.field)
        value = (outputs.get(owner) or {}).get(status.field)
        if value not in (None, [], ""):
            claims[status.field] = value
    return claims


def _polish(claims: dict, llm_luna) -> dict:
    """Language pass over supported claims only: the writer LLM may reword a
    claim but can never add a field the critic did not mark supported."""
    if not claims:
        return claims
    prompt = (
        "Perbaiki bahasa Indonesia pada nilai berikut tanpa menambah fakta baru "
        "dan tanpa menambah field. Jawab JSON dengan key yang sama.\n"
        f"{json.dumps(claims, ensure_ascii=False)}"
    )
    try:
        raw = llm_luna.invoke(prompt)
        if hasattr(raw, "content"):
            raw = raw.content
        data = json.loads(str(raw)) if isinstance(raw, str) else raw
    except Exception:
        return claims
    if not isinstance(data, dict):
        return claims
    for field, value in data.items():
        if field in claims and isinstance(value, type(claims[field])):
            claims[field] = value
    return claims


def writer_node(state: FishoraState, llm_luna, species: SpeciesRecord | None = None) -> dict:
    sp = species or state.get("species")
    if sp is None:
        return {"error": "knowledge generation failed: no species record", "final_card": None}
    # Never re-trust a row's verification status from earlier in the graph.
    evidence = [c for c in state.get("refined_evidence", []) if _is_verified(c)]
    generator = KnowledgeGenerator()
    if not evidence:
        return {"final_card": generator.empty_card(sp)}

    statuses = state.get("claim_statuses") or []
    by_chunk = {chunk.chunk_id: chunk for chunk in evidence}
    claims = _supported_claims(state.get("expert_outputs", {}), statuses)
    if llm_luna is not None:
        claims = _polish(claims, llm_luna)

    # Cite only the chunks that actually carried a surviving claim.
    cited: list[str] = []
    for status in statuses:
        if status.status != "supported" or status.field not in claims:
            continue
        for chunk_id in status.chunk_ids:
            source_id = by_chunk[chunk_id].source_id
            if source_id not in cited:
                cited.append(source_id)

    try:
        generated = GeneratedKnowledgeCard(
            common_name=sp.common_name_id,
            scientific_name=sp.scientific_name,
            taxonomy_status=sp.taxonomy_status,
            physical_characteristics=claims.get("physical_characteristics"),
            taste=claims.get("taste"),
            texture=claims.get("texture"),
            processing_methods=claims.get("processing_methods", []),
            commercial_uses=claims.get("commercial_uses", []),
            similar_or_substitute_species=claims.get("similar_or_substitute_species", []),
            potential_buyer_segments=claims.get("potential_buyer_segments", []),
            limitations=[],
            sources=[{"source_id": source_id} for source_id in cited],
        )
    except ValidationError:
        return {"error": "knowledge validation failed", "final_card": None}
    # build_card is the fail-closed gate: evidence with no citation raises here
    # rather than completing the job with an empty, uncited card.
    try:
        card = generator.build_card(sp, evidence, generated)
    except InvalidGeneratedKnowledge:
        return {"error": "knowledge generation failed: no grounded claim", "final_card": None}
    return {"final_card": card}


# ---- Graph factory -----------------------------------------------------

def make_graph(knowledge_repo=None, embedder=None, llm_luna=None, llm_medium=None):
    """Return a graph-like object with .invoke(state) and .ainvoke(state).

    If langgraph is installed, build a real StateGraph; otherwise return an
    executor that mirrors the same node order and the same expert fan-out.
    """
    if _HAS_LANGGRAPH and knowledge_repo is not None:
        graph = StateGraph(FishoraState)
        graph.add_node("researcher", lambda s: hybrid_researcher(s, knowledge_repo, embedder, llm_medium))
        graph.add_node("physical", lambda s: physical_expert(s, llm_luna))
        graph.add_node("taste", lambda s: taste_expert(s, llm_luna))
        graph.add_node("commercial", lambda s: commercial_expert(s, llm_luna))
        graph.add_node("substitute", lambda s: substitute_expert(s, llm_luna))
        graph.add_node("critic", lambda s: critic_node(s, llm_medium))
        graph.add_node("writer", lambda s: writer_node(s, llm_luna, s.get("species")))
        graph.add_edge(START, "researcher")
        # fan-out
        graph.add_edge("researcher", "physical")
        graph.add_edge("researcher", "taste")
        graph.add_edge("researcher", "commercial")
        graph.add_edge("researcher", "substitute")
        for n in EXPERT_NAMES:
            graph.add_edge(n, "critic")
        graph.add_edge("critic", "writer")
        graph.add_edge("writer", END)
        return graph.compile()

    # Fallback simple executor (ponytail: no langgraph dependency)
    class SimpleGraph:
        async def ainvoke(self, state: FishoraState) -> FishoraState:
            s = dict(state)
            s.update(hybrid_researcher(s, knowledge_repo, embedder, llm_medium))
            # Expert LLM calls block on network I/O, so real overlap needs
            # threads; gather also keeps the single merge point for the reducer.
            results = await asyncio.gather(
                *(asyncio.to_thread(_expert_node, name, s, llm_luna) for name in EXPERT_NAMES)
            )
            s["expert_outputs"] = merge_expert_outputs(
                s.get("expert_outputs"), dict(zip(EXPERT_NAMES, results))
            )
            s.update(critic_node(s, llm_medium))
            s.update(writer_node(s, llm_luna, s.get("species")))
            return s

        def invoke(self, state: FishoraState) -> FishoraState:
            # run_graph is sync (BackgroundTasks worker thread), so there is no
            # loop to reuse here.
            return asyncio.run(self.ainvoke(state))

    return SimpleGraph()


def run_graph(job_id: str, species_id: str, prediction_id: str, knowledge_repo, embedder, llm_luna, llm_medium, species_repo, job_repo):
    """Background entry: loads species, runs graph, persists result. Sync for BackgroundTasks."""
    try:
        species = species_repo.get_by_id(species_id) if species_repo else None
        graph = make_graph(knowledge_repo, embedder, llm_luna, llm_medium)
        state: FishoraState = {"job_id": job_id, "prediction_id": prediction_id, "species_id": species_id, "species": species, "expert_outputs": {}}
        result = graph.invoke(state)
        final = result.get("final_card")
        err = result.get("error")
        if final is not None and err is None:
            data = final.model_dump(mode="json") if hasattr(final, "model_dump") else final
            job_repo.update(job_id, status="completed", final_card=data, expert_outputs=result.get("expert_outputs"), critic_feedback=result.get("critic_feedback"))
        else:
            # generic error, hide raw detail in response but keep expert_outputs for debug
            job_repo.update(job_id, status="failed", error="knowledge generation failed", expert_outputs=result.get("expert_outputs"))
    except Exception:
        try:
            job_repo.update(job_id, status="failed", error="knowledge generation failed")
        except Exception:
            pass
