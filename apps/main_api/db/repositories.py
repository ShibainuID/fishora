import csv
from pathlib import Path

from sqlalchemy.orm import Session

from apps.main_api.contracts import TaxonomySeed
from apps.main_api.db.models import FishSpecies

TAXONOMY_STATUS_BY_LABEL = {
    "bandeng": "VERIFIED_TAXONOMY",
    "gelama_bunga": "VERIFIED_TAXONOMY",
    "gembolo": "TAXONOMY_REVIEW_REQUIRED",
    "gulamah": "VERIFIED_TAXONOMY",
    "kembung": "VERIFIED_TAXONOMY",
    "kuniran": "VERIFIED_TAXONOMY",
    "mujair": "VERIFIED_TAXONOMY",
    "nila": "VERIFIED_TAXONOMY",
    "senangin": "VERIFIED_TAXONOMY",
    "tenggiri": "MEDIUM_CONFIDENCE_LABEL_AMBIGUITY",
    "tuna": "MIXED_TAXONOMY",
}

def load_taxonomy_csv(path: Path) -> list[TaxonomySeed]:
    """Read the taxonomy CSV; only empty scientific_name/notes cells become None.

    Non-empty cells are preserved verbatim (no stripping). Rejects unknown
    normalized labels and any file whose normalized label set is not exactly
    the eleven supported labels.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows: list[TaxonomySeed] = []
        for row in reader:
            normalized_label = row["normalized_label"]
            if normalized_label not in TAXONOMY_STATUS_BY_LABEL:
                raise ValueError(f"unsupported normalized_label {normalized_label!r} in {path}")
            rows.append(
                TaxonomySeed(
                    raw_folder=row["raw_folder"],
                    raw_label=row["raw_label"],
                    normalized_label=normalized_label,
                    scientific_name=row["scientific_name"].strip() or None,
                    common_name_id=row["common_name_id"],
                    taxonomic_rank=row["taxonomic_rank"],
                    confidence=row["confidence"],
                    source=row["source"],
                    notes=row["notes"] or None,
                    taxonomy_status=TAXONOMY_STATUS_BY_LABEL[normalized_label],
                )
            )
    labels = {row.normalized_label for row in rows}
    if labels != set(TAXONOMY_STATUS_BY_LABEL):
        raise ValueError(
            f"taxonomy CSV normalized labels must be exactly the {len(TAXONOMY_STATUS_BY_LABEL)} "
            f"supported labels, got {sorted(labels)}"
        )
    return rows


def seed_taxonomy(session: Session, path: Path) -> int:
    """Upsert the eleven FishSpecies rows; returns the number of rows written.

    Does not commit; the caller owns the transaction.
    """
    written = 0
    for seed in load_taxonomy_csv(path):
        values = {
            "normalized_label": seed.normalized_label,
            "common_name_id": seed.common_name_id,
            "scientific_name": seed.scientific_name,
            "taxonomic_rank": seed.taxonomic_rank,
            "taxonomy_status": seed.taxonomy_status,
            "notes": seed.notes,
        }
        species = session.get(FishSpecies, f"species_{seed.normalized_label}")
        if species is None:
            session.add(FishSpecies(id=f"species_{seed.normalized_label}", **values))
            written += 1
        elif any(getattr(species, field) != value for field, value in values.items()):
            for field, value in values.items():
                setattr(species, field, value)
            written += 1
    return written