"""Task 5: semantic chunking of approved knowledge records.

One candidate record is one semantic unit (species, source, category): it
stays whole at or below ``max_tokens``, even far below ``min_tokens`` — short
units are never merged to reach a target size. Longer content splits on
sentence boundaries; a single oversized sentence splits at token-ID
boundaries. Overlap applies only when a record actually splits, and every
emitted chunk is within ``max_tokens`` real tokenizer tokens.
"""

import pytest

from tests.main_api.fakes import WhitespaceTokenizer

LONG_SENTENCE = "Kalimat ikan bandeng menjelaskan ciri tubuh dan konteks sumber."


@pytest.fixture
def candidate():
    from apps.main_api.services.corpus import CandidateChunk

    return CandidateChunk(
        id="chunk_bandeng_phys_001",
        species_label="bandeng",
        source_id="fishbase_chanos_chanos",
        category="physical_characteristics",
        content="Ikan bandeng memiliki tubuh memanjang dengan sirip ekor bercabang.",
        source_quote="quote",
        stage="knowledge_editor",
        verification_status="candidate",
    )


@pytest.fixture
def tokenizer():
    return WhitespaceTokenizer()


def _chunk_candidate(candidate, tokenizer, **kwargs):
    from apps.main_api.services.chunking import chunk_candidate

    return chunk_candidate(candidate, tokenizer, **kwargs)


def _tokens(tokenizer, text):
    return tokenizer.encode(text)


def test_short_semantic_section_stays_one_category_chunk(candidate, tokenizer):
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) == 1
    assert chunks[0].id == candidate.id
    assert chunks[0].category == "physical_characteristics"
    assert chunks[0].species_label == "bandeng"
    assert chunks[0].source_id == candidate.source_id
    assert chunks[0].content == candidate.content


def test_short_section_below_min_tokens_is_never_split_or_merged(candidate, tokenizer):
    candidate.content = " ".join("kata" for _ in range(150))
    chunks = _chunk_candidate(candidate, tokenizer, min_tokens=300)
    assert len(chunks) == 1
    assert chunks[0].content == candidate.content


def test_long_section_splits_on_sentence_boundaries_and_only_then_overlaps(candidate, tokenizer):
    text = " ".join(LONG_SENTENCE for _ in range(180))
    candidate.content = text
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.category == candidate.category
        assert chunk.species_label == candidate.species_label
        assert chunk.source_id == candidate.source_id
        assert len(_tokens(tokenizer, chunk.content)) <= 600
    assert all(chunk.content.endswith(".") for chunk in chunks[:-1]), "chunks end at sentence boundaries"
    for previous, following in zip(chunks, chunks[1:]):
        assert _tokens(tokenizer, following.content)[:50] == _tokens(tokenizer, previous.content)[-50:]


def test_short_section_gets_no_overlap(candidate, tokenizer):
    candidate.content = "Ikan bandeng memiliki tubuh memanjang."
    (chunk,) = _chunk_candidate(candidate, tokenizer)
    assert chunk.content == candidate.content


def test_oversized_single_sentence_splits_token_ids_safely(candidate, tokenizer):
    candidate.content = " ".join("panjang" for _ in range(1000))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) > 1
    for chunk in chunks:
        assert 0 < len(_tokens(tokenizer, chunk.content)) <= 600
    for previous, following in zip(chunks, chunks[1:]):
        assert _tokens(tokenizer, following.content)[:50] == _tokens(tokenizer, previous.content)[-50:]
    assert tokenizer.decode(_tokens(tokenizer, chunks[0].content)) == chunks[0].content


def test_splits_never_mix_category_species_or_source(candidate, tokenizer):
    candidate.content = " ".join(LONG_SENTENCE for _ in range(90))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) > 1
    assert {c.category for c in chunks} == {candidate.category}
    assert {c.species_label for c in chunks} == {candidate.species_label}
    assert {c.source_id for c in chunks} == {candidate.source_id}