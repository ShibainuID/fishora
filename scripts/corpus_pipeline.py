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

`approve` requires the `FISHORA_CORPUS_APPROVAL_KEY` environment variable: the
HMAC-SHA256 signing key for the approval manifest. The key is never stored or
logged.
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

    args = parser.parse_args(argv)
    if args.command == "collect":
        count = collect_candidate_stages(args.stage_dir, args.candidate_dir)
        print(f"collected {count} candidate chunks -> {args.candidate_dir}")
        return count
    approval_key = os.environ.get(APPROVAL_KEY_ENV, "")
    if not approval_key:
        parser.error(f"{APPROVAL_KEY_ENV} environment variable is required")
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