# Fishora Knowledge Sources

Controlled offline corpus for the Fishora RAG pipeline. This directory is the
handoff boundary between externally run research agents and the operator CLI;
**the main API never runs any corpus command**.

## Directory layout

| Path | Status | Meaning |
|---|---|---|
| `offline/research.json` | offline input | Source identification (research agent group 1) |
| `offline/fact_extraction.json` | offline input | Claim formalization (research agent group 2) |
| `offline/verification.json` | offline input | Source revalidation (research agent group 3) |
| `offline/knowledge_editor.json` | offline input | Editor handoff; its records become candidate chunks |
| `candidates/*.json` | `candidate` | One record per chunk: `claim_id` + `chunk` + `source` (title, publisher, URL, support quote) |
| `approved/*.json` | `verified` | Created **only** by the approval action; never auto-approved |
| `approval-manifest.json` | — | Written by the approval action; consumed by `require_approved_manifest` |
| `review/*.json` | operator input | Human review file: `{"approved_chunk_ids": [...]}` |

## Mandatory human approval

Agents (research, fact-extraction, verification, knowledge editor) can only
produce `candidate` records. Only the CLI approval action may create `verified`
copies, and it requires **all** of:

1. a non-empty `--reviewer`,
2. the exact confirmation token `APPROVE` (never any other string),
3. explicit `approved_chunk_ids` from the review file,
4. a source that was reviewed by a human (`reviewed_at` set).

```text
python3 -m scripts.corpus_pipeline collect \
  --stage-dir artifacts/knowledge_sources/offline \
  --candidate-dir artifacts/knowledge_sources/candidates

python3 -m scripts.corpus_pipeline approve \
  --candidate-dir artifacts/knowledge_sources/candidates \
  --review-file artifacts/knowledge_sources/review/approval.json \
  --approved-dir artifacts/knowledge_sources/approved \
  --approval-manifest artifacts/knowledge_sources/approval-manifest.json \
  --reviewer operator \
  --confirmation APPROVE
```

`collect` requires all four stage files and verifies that every editor chunk
has matching research, fact-extraction and verification records with the same
(`claim_id`, `source_id`). Unsupported labels/categories, empty source quotes,
and non-candidate statuses are rejected. `collect` never writes to an approved
directory or database.

## Corpus

- 11 labels, 34 candidate chunks, 21 sources (FishBase, FAO, and peer-reviewed
  journal articles; all URLs revalidated 2026-08-23).
- Categories: `identity`, `physical_characteristics`, `taste_texture`,
  `processing_methods`, `commercial_uses`, `substitutes` (exactly these six).
- **tenggiri**: the vernacular name is shared by five species (FishBase common
  names); candidate chunks document the ambiguity and the two main candidate
  species, `Scomberomorus commerson` and `S. guttatus`.
- **tuna**: genus-level only (`Thunnus`, seven species per FAO Scombrids
  catalogue); no single species is asserted.
- **gembolo**: unresolved; the only record is the explicit limitation that no
  scientific identity or factual culinary claims may be assigned without
  expert confirmation. No factual claim was invented for it.
- Where evidence was unavailable for a category, the factual claim was omitted
  rather than invented.

## Regeneration

The four offline stage files are generated from the single claims table in
`scripts/build_knowledge_corpus.py` (run it, then run `collect` above). The
three research-agent groups are the source of candidate generation; the
approval boundary is enforced by `apps/main_api/services/corpus.py` and is
exercised by `tests/main_api/test_corpus.py` / `test_corpus_cli.py`.