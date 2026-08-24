"""Background LangGraph-style orchestration for Fishora.

Ponytail: no hard dependency on langgraph library. The graph is plain
Python + asyncio fan-out, but exposes a LangGraph-compatible `make_graph`
that falls back to a simple dict-based executor if langgraph is absent.
This keeps 1 venv + DB without adding a heavy graph engine for 7 nodes.
"""

from __future__ import annotations

import asyncio
import json
from typing import TypedDict

from pydantic import ValidationError

from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.services.embeddings import E5_DIMENSION, E5_MODEL_NAME
from apps.main_api.services.generation import (
    GeneratedKnowledgeCard,
    KnowledgeCard,
    SourceMetadata,
    SYSTEM_PROMPT,
    TAXONOMY_GUARDRAILS,
    _relational_identity,
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


class FishoraState(TypedDict, total=False):
    job_id: str
    prediction_id: str
    species_id: str
    species: SpeciesRecord
    broad_evidence: list[RetrievedChunk]
    refined_evidence: list[RetrievedChunk]
    expert_outputs: dict
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
    "physical": "Tulis physical_characteristics dari bukti kategori physical_characteristics dan identity. Jika tidak ada, null. Jawab JSON {\"physical_characteristics\": str|null, \"sources\": [{\"source_id\": str}]}",
    "taste": "Tulis taste dan texture dari bukti taste_texture. Jika tidak ada, null. JSON {\"taste\": str|null, \"texture\": str|null, \"sources\": [{\"source_id\": str}]}",
    "commercial": "Tulis processing_methods dan commercial_uses dari bukti processing_methods dan commercial_uses. JSON {\"processing_methods\": [], \"commercial_uses\": [], \"sources\": [{\"source_id\": str}]}",
    "substitute": "Tulis similar_or_substitute_species dan potential_buyer_segments dari bukti substitutes dan commercial_uses. JSON {\"similar_or_substitute_species\": [], \"potential_buyer_segments\": [], \"sources\": [{\"source_id\": str}]}",
}


def _expert_node(category: str, state: FishoraState, llm_luna) -> dict:
    evidence = state.get("refined_evidence", [])
    if llm_luna is None:
        # No LLM available (tests / empty sub2api key) -> return empty placeholders without error
        if category == "physical":
            return {"physical_characteristics": None, "sources": []}
        if category == "taste":
            return {"taste": None, "texture": None, "sources": []}
        if category == "commercial":
            return {"processing_methods": [], "commercial_uses": [], "sources": []}
        return {"similar_or_substitute_species": [], "potential_buyer_segments": [], "sources": []}
    cat_map = {
        "physical": {"physical_characteristics", "identity"},
        "taste": {"taste_texture"},
        "commercial": {"processing_methods", "commercial_uses"},
        "substitute": {"substitutes", "commercial_uses"},
    }
    subset = [c for c in evidence if c.category in cat_map[category]] or evidence[:2]
    payload = "\n".join(f"[{c.source_id}:{c.category}] {c.content[:300]}" for c in subset)
    prompt = _EXPERT_PROMPTS[category] + f"\nBukti:\n{payload}"
    try:
        raw = llm_luna.invoke(prompt)
        if hasattr(raw, "content"):
            raw = raw.content
        data = json.loads(str(raw)) if isinstance(raw, str) else raw
        sources = data.get("sources", [])
        by_source = {c.source_id for c in evidence}
        sources = [s for s in sources if s.get("source_id") in by_source][:3]
        data["sources"] = sources
    except Exception as exc:
        data = {"error": str(exc), "sources": []}
        if category == "physical":
            data["physical_characteristics"] = None
        elif category == "taste":
            data["taste"] = None
            data["texture"] = None
        elif category == "commercial":
            data["processing_methods"] = []
            data["commercial_uses"] = []
        else:
            data["similar_or_substitute_species"] = []
            data["potential_buyer_segments"] = []
    return data


def physical_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {**state.get("expert_outputs", {}), "physical": _expert_node("physical", state, llm_luna)}}


def taste_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {**state.get("expert_outputs", {}), "taste": _expert_node("taste", state, llm_luna)}}


def commercial_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {**state.get("expert_outputs", {}), "commercial": _expert_node("commercial", state, llm_luna)}}


def substitute_expert(state: FishoraState, llm_luna) -> dict:
    return {"expert_outputs": {**state.get("expert_outputs", {}), "substitute": _expert_node("substitute", state, llm_luna)}}


# ---- Critic (medium) ---------------------------------------------------

def critic_node(state: FishoraState, llm_medium=None) -> dict:
    evidence = state.get("refined_evidence", [])
    by_source = {c.source_id for c in evidence}
    outputs = state.get("expert_outputs", {})
    invalid = []
    for cat, data in outputs.items():
        for s in data.get("sources", []):
            sid = s.get("source_id")
            if sid not in by_source:
                invalid.append(f"{cat}:{sid}")
    feedback = f"invalid citations: {invalid}" if invalid else "all citations valid"
    # optional LLM refinement
    if llm_medium is not None and invalid:
        try:
            prompt = f"Cek sitasi berikut, mana yang halu? evidence ids {sorted(by_source)}, expert {outputs}. Jawab singkat."
            raw = llm_medium.invoke(prompt)
            if hasattr(raw, "content"):
                raw = raw.content
            feedback = str(raw)[:500]
        except Exception:
            pass
    return {"critic_feedback": feedback}


# ---- Writer (luna) ------------------------------------------------------

def writer_node(state: FishoraState, llm_luna, species: SpeciesRecord | None = None) -> dict:
    evidence = state.get("refined_evidence", [])
    outputs = state.get("expert_outputs", {})
    # merge expert fragments into a single GeneratedKnowledgeCard-like dict
    merged = {
        "physical_characteristics": outputs.get("physical", {}).get("physical_characteristics"),
        "taste": outputs.get("taste", {}).get("taste"),
        "texture": outputs.get("taste", {}).get("texture"),
        "processing_methods": outputs.get("commercial", {}).get("processing_methods", []),
        "commercial_uses": outputs.get("commercial", {}).get("commercial_uses", []),
        "similar_or_substitute_species": outputs.get("substitute", {}).get("similar_or_substitute_species", []),
        "potential_buyer_segments": outputs.get("substitute", {}).get("potential_buyer_segments", []),
        "limitations": [],
        "sources": [],
    }
    # collect sources from all experts, dedup, keep verified only
    by_source = {c.source_id: c for c in evidence}
    seen = set()
    for cat in ["physical", "taste", "commercial", "substitute"]:
        for s in outputs.get(cat, {}).get("sources", []):
            sid = s.get("source_id")
            if sid in by_source and sid not in seen:
                merged["sources"].append({"source_id": sid})
                seen.add(sid)
    # if writer LLM provided, let it refine the merge
    if llm_luna is not None and evidence:
        try:
            payload = json.dumps(merged, ensure_ascii=False)
            prompt = (
                "Gabungkan output expert menjadi kartu pengetahuan. Perbaiki bahasa Indonesia, jangan tambah fakta baru. "
                f"Bukti ids {list(by_source.keys())}. Output expert: {payload}. Jawab JSON sesuai skema GeneratedKnowledgeCard."
            )
            raw = llm_luna.invoke(prompt)
            if hasattr(raw, "content"):
                raw = raw.content
            data = json.loads(str(raw)) if isinstance(raw, str) else raw
            # keep only valid sources
            data["sources"] = [s for s in data.get("sources", []) if s.get("source_id") in by_source]
            merged.update({k: v for k, v in data.items() if k in merged})
        except Exception:
            pass
    # enforce relational identity + guardrails + server enrichment (mirror generation.py)
    sp = species or state.get("species")
    if sp is None:
        # fallback if no species record
        return {"final_card": merged}
    common_name, scientific_name, taxonomy_status, guardrails = _relational_identity(sp)
    # build final KnowledgeCard
    # collect source metadata
    sources_meta = []
    for s in merged.get("sources", []):
        sid = s["source_id"]
        chunk = by_source.get(sid)
        if chunk:
            sources_meta.append(
                SourceMetadata(
                    source_id=sid,
                    title=chunk.source_title,
                    source_type=chunk.source_type,
                    url=chunk.source_url or "",
                    publisher=chunk.source_publisher or "",
                    reviewed_at=chunk.source_reviewed_at,
                    verification_status="verified",
                )
            )
    # validate via GeneratedKnowledgeCard then build KnowledgeCard
    try:
        gen = GeneratedKnowledgeCard(
            common_name=common_name,
            scientific_name=scientific_name,
            taxonomy_status=taxonomy_status,
            physical_characteristics=merged.get("physical_characteristics"),
            taste=merged.get("taste"),
            texture=merged.get("texture"),
            processing_methods=merged.get("processing_methods", []),
            commercial_uses=merged.get("commercial_uses", []),
            similar_or_substitute_species=merged.get("similar_or_substitute_species", []),
            potential_buyer_segments=merged.get("potential_buyer_segments", []),
            limitations=(merged.get("limitations", []) + guardrails),
            sources=[{"source_id": s.source_id} for s in sources_meta],
        )
    except ValidationError as exc:
        return {"error": str(exc), "final_card": None}
    card = KnowledgeCard(
        common_name=gen.common_name,
        scientific_name=gen.scientific_name,
        taxonomy_status=gen.taxonomy_status,
        physical_characteristics=gen.physical_characteristics,
        taste=gen.taste,
        texture=gen.texture,
        processing_methods=gen.processing_methods,
        commercial_uses=gen.commercial_uses,
        similar_or_substitute_species=gen.similar_or_substitute_species,
        potential_buyer_segments=gen.potential_buyer_segments,
        limitations=gen.limitations,
        sources=sources_meta,
    )
    return {"final_card": card}


# ---- Graph factory -----------------------------------------------------

def make_graph(knowledge_repo=None, embedder=None, llm_luna=None, llm_medium=None):
    """Return a graph-like object with .invoke(state) and .ainvoke(state).

    If langgraph is installed, build a real StateGraph; otherwise return a
    simple sequential/parallel executor that mirrors the same node order.
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
        for n in ["physical", "taste", "commercial", "substitute"]:
            graph.add_edge(n, "critic")
        graph.add_edge("critic", "writer")
        graph.add_edge("writer", END)
        return graph.compile()

    # Fallback simple executor (ponytail: no langgraph dependency)
    class SimpleGraph:
        def invoke(self, state: FishoraState) -> FishoraState:
            s = dict(state)
            s.update(hybrid_researcher(s, knowledge_repo, embedder, llm_medium))
            # parallel experts via sequential (tests inject fast fakes, so fine)
            # In production, could use asyncio.gather with threads
            for fn in [physical_expert, taste_expert, commercial_expert, substitute_expert]:
                s.update(fn(s, llm_luna))
            s.update(critic_node(s, llm_medium))
            s.update(writer_node(s, llm_luna, s.get("species")))
            return s

        async def ainvoke(self, state: FishoraState) -> FishoraState:
            return self.invoke(state)

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
