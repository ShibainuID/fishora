"""Offline operator CLI for the Fishora corpus pipeline.

Runs only on the operator's machine against `artifacts/knowledge_sources/`;
the main API never invokes these commands.

Usage:
  python3 -m scripts.corpus_pipeline collect \
    --stage-dir artifacts/knowledge_sources/offline \
    --candidate-dir artifacts/knowledge_sources/candidates

  FISHORA_CORPUS_APPROVAL_KEY=... python3 -m scripts.corpus_pipeline approve \
    --candidate-dir artifacts/knowledge_sources/candidates \
    --review-file artifacts/knowledge_sources/review/approval.json \
    --approved-dir artifacts/knowledge_sources/approved \
    --approval-manifest artifacts/knowledge_sources/approval-manifest.json \
    --reviewer operator \
    --confirmation APPROVE

  FISHORA_CORPUS_APPROVAL_KEY=... python3 -m scripts.corpus_pipeline ingest \
    --approved-dir artifacts/knowledge_sources/approved \
    --approval-manifest artifacts/knowledge_sources/approval-manifest.json \
    --embedding-model intfloat/multilingual-e5-base

`approve` and `ingest` require the `FISHORA_CORPUS_APPROVAL_KEY` environment
variable: the HMAC-SHA256 signing key for the approval manifest. `ingest`
reads the database URL only from `FISHORA_DATABASE_URL` (credentials never
appear in process arguments), prints `ingested N verified chunks` only after
the single database transaction commits, and never accepts the candidate
corpus as approved input. The key is never stored or logged.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from apps.main_api.services.corpus import (
    APPROVAL_TOKEN,
    ApprovalManifest,
    approve_candidates,
    collect_candidate_stages,
)

APPROVAL_KEY_ENV = "FISHORA_CORPUS_APPROVAL_KEY"


def main(argv: list[str] | None = None) -> int | ApprovalManifest:
    parser = argparse.ArgumentParser(prog="python3 -m scripts.corpus_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    collect_p = sub.add_parser("collect", help="collect candidate chunks from the four offline stage files")
    collect_p.add_argument("--stage-dir", type=Path, required=True)
    collect_p.add_argument("--candidate-dir", type=Path, required=True)

    approve_p = sub.add_parser("approve", help="mandatory human approval gate (signed manifest)")
    approve_p.add_argument("--candidate-dir", type=Path, required=True)
    approve_p.add_argument("--review-file", type=Path, required=True)
    approve_p.add_argument("--approved-dir", type=Path, required=True)
    approve_p.add_argument("--approval-manifest", type=Path, required=True)
    approve_p.add_argument("--reviewer", required=True)
    approve_p.add_argument("--confirmation", required=True,
                           help=f"must be exactly {APPROVAL_TOKEN}")

    ingest_p = sub.add_parser("ingest", help="ingest the signed approved corpus into Postgres/pgvector")
    ingest_p.add_argument("--approved-dir", type=Path, required=True)
    ingest_p.add_argument("--approval-manifest", type=Path, required=True)
    ingest_p.add_argument("--embedding-model", default="intfloat/multilingual-e5-base")

    args = parser.parse_args(argv)
    if args.command == "collect":
        count = collect_candidate_stages(args.stage_dir, args.candidate_dir)
        print(f"collected {count} candidate chunks -> {args.candidate_dir}")
        return count
    approval_key = os.environ.get(APPROVAL_KEY_ENV, "")
    if not approval_key:
        parser.error(f"{APPROVAL_KEY_ENV} environment variable is required")
    if args.command == "ingest":
        # Credentials come from the environment only, never from process args.
        database_url = os.environ.get("FISHORA_DATABASE_URL", "")
        if not database_url:
            parser.error("FISHORA_DATABASE_URL environment variable is required")
        candidates_dir = (Path(__file__).resolve().parents[1]
                          / "artifacts/knowledge_sources/candidates").resolve()
        if args.approved_dir.resolve() == candidates_dir:
            parser.error(f"{args.approved_dir} is the candidate corpus, not an approved input")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from apps.main_api.db.repositories import SqlKnowledgeRepository
        from apps.main_api.db.sql_repositories import SqlSpeciesRepository
        from apps.main_api.services.embeddings import LocalE5Embedder
        from apps.main_api.services.ingestion import ingest_approved_corpus

        factory = sessionmaker(bind=create_engine(database_url), expire_on_commit=False)
        count = ingest_approved_corpus(
            args.approved_dir,
            args.approval_manifest,
            SqlSpeciesRepository(factory),
            SqlKnowledgeRepository(factory),
            LocalE5Embedder(args.embedding_model),
            approval_key,
        )
        print(f"ingested {count} verified chunks")
        return count
    manifest = approve_candidates(
        args.candidate_dir,
        args.review_file,
        args.approved_dir,
        args.approval_manifest,
        args.reviewer,
        args.confirmation,
        datetime.now(timezone.utc),
        approval_key,
    )
    print(f"approved {len(manifest.approved_chunk_ids)} chunks "
          f"({len(manifest.approved_source_ids)} sources) by {manifest.reviewer}")
    return manifest


if __name__ == "__main__":
    main()