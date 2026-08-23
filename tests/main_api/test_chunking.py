"""Task 5: semantic chunking of approved knowledge records (round 1).

One candidate record is one semantic unit (species, source, category): it
stays whole at or below ``max_tokens``, even far below ``min_tokens`` — short
units are never merged to reach a target size. Longer content splits on
sentence boundaries; a single sentence above 600 tokens splits into windows
with exactly one 50-token overlap; 551-600 token sentences are never split.
Overlap is applied exactly once per split — never doubled by combining window
overlap with a carry — and every emitted chunk re-encodes to at most
``max_tokens`` tokens. Chunking never emits special token text ([CLS], [SEP],
<s>, </s>).
"""

import pytest

from tests.main_api.fakes import SpecialTokenTokenizer, WhitespaceTokenizer

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
    return tokenizer.encode(text, add_special_tokens=False)


def _assert_chunks_within_budget(chunks, tokenizer, max_tokens=600):
    for chunk in chunks:
        assert len(_tokens(tokenizer, chunk.content)) <= max_tokens, chunk.id


def _assert_single_fifty_token_overlap(chunks, tokenizer):
    for previous, following in zip(chunks, chunks[1:]):
        assert _tokens(tokenizer, following.content)[:50] == _tokens(tokenizer, previous.content)[-50:]
        # the overlap appears exactly once: the head run is not repeated
        assert _tokens(tokenizer, following.content)[50:100] != _tokens(tokenizer, following.content)[:50]


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


def test_short_section_gets_no_overlap(candidate, tokenizer):
    candidate.content = "Ikan bandeng memiliki tubuh memanjang."
    (chunk,) = _chunk_candidate(candidate, tokenizer)
    assert chunk.content == candidate.content


def test_551_token_sentence_is_one_whole_chunk(candidate, tokenizer):
    candidate.content = " ".join(f"k{i}" for i in range(551))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) == 1
    assert chunks[0].content == candidate.content


def test_600_token_sentence_is_one_whole_chunk(candidate, tokenizer):
    candidate.content = " ".join(f"k{i}" for i in range(600))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) == 1
    assert chunks[0].content == candidate.content


def test_601_token_sentence_splits_into_windows_with_single_overlap(candidate, tokenizer):
    candidate.content = " ".join(f"k{i}" for i in range(601))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) == 2
    assert len(_tokens(tokenizer, chunks[0].content)) == 600
    assert len(_tokens(tokenizer, chunks[1].content)) == 51
    _assert_chunks_within_budget(chunks, tokenizer)
    _assert_single_fifty_token_overlap(chunks, tokenizer)


def test_long_section_splits_on_sentence_boundaries_and_only_then_overlaps(candidate, tokenizer):
    text = " ".join(LONG_SENTENCE for _ in range(180))
    candidate.content = text
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.category == candidate.category
        assert chunk.species_label == candidate.species_label
        assert chunk.source_id == candidate.source_id
    assert all(chunk.content.endswith(".") for chunk in chunks[:-1]), "chunks end at sentence boundaries"
    _assert_chunks_within_budget(chunks, tokenizer)
    _assert_single_fifty_token_overlap(chunks, tokenizer)


def test_oversized_sentence_splits_token_ids_safely(candidate, tokenizer):
    candidate.content = " ".join(f"p{i}" for i in range(1000))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) > 1
    _assert_chunks_within_budget(chunks, tokenizer)
    _assert_single_fifty_token_overlap(chunks, tokenizer)
    assert tokenizer.decode(_tokens(tokenizer, chunks[0].content)) == chunks[0].content


def test_splits_never_mix_category_species_or_source(candidate, tokenizer):
    candidate.content = " ".join(LONG_SENTENCE for _ in range(90))
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) > 1
    assert {c.category for c in chunks} == {candidate.category}
    assert {c.species_label for c in chunks} == {candidate.species_label}
    assert {c.source_id for c in chunks} == {candidate.source_id}


def test_overlap_is_never_doubled_across_window_and_sentence_boundaries(candidate, tokenizer):
    """A window already carries its own overlap; a following carry must not
    duplicate it inside the next chunk."""
    candidate.content = (
        " ".join(f"w{i}" for i in range(700)) + ". " +
        " ".join(f"x{i}" for i in range(100)) + ". " +
        " ".join(f"y{i}" for i in range(50)) + "."
    )
    chunks = _chunk_candidate(candidate, tokenizer)
    assert len(chunks) == 2
    _assert_chunks_within_budget(chunks, tokenizer)
    _assert_single_fifty_token_overlap(chunks, tokenizer)


def test_chunks_never_contain_special_token_text_601(candidate):
    special = SpecialTokenTokenizer()
    candidate.content = " ".join(f"k{i}" for i in range(601))
    chunks = _chunk_candidate(candidate, special)
    assert len(chunks) == 2
    for chunk in chunks:
        for special_text in ("[CLS]", "[SEP]", "<s>", "</s>"):
            assert special_text not in chunk.content
    _assert_chunks_within_budget(chunks, special)
    _assert_single_fifty_token_overlap(chunks, special)


def test_chunks_never_contain_special_token_text_long_input(candidate):
    special = SpecialTokenTokenizer()
    candidate.content = " ".join(LONG_SENTENCE for _ in range(180))
    chunks = _chunk_candidate(candidate, special)
    assert len(chunks) > 1
    for chunk in chunks:
        for special_text in ("[CLS]", "[SEP]", "<s>", "</s>"):
            assert special_text not in chunk.content
    _assert_chunks_within_budget(chunks, special)
    _assert_single_fifty_token_overlap(chunks, special)