import csv
from pathlib import Path

import pytest

from apps.main_api.db.repositories import load_taxonomy_csv

TAXONOMY = Path("/home/athilla/Documents/IF_ITB/Lomba/COMPFEST/AIC-2026/artifacts/Dataset/fishora_dataset/metadata/taxonomy.csv")
EXPECTED = {
    "bandeng", "gelama_bunga", "gembolo", "gulamah", "kembung", "kuniran",
    "mujair", "nila", "senangin", "tenggiri", "tuna",
}


def test_taxonomy_has_exact_supported_labels_and_guardrails():
    rows = load_taxonomy_csv(TAXONOMY)
    by_label = {row.normalized_label: row for row in rows}
    assert set(by_label) == EXPECTED
    assert {label: row.taxonomy_status for label, row in by_label.items()} == {
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
    assert by_label["tuna"].scientific_name == "Thunnus spp."
    assert by_label["gembolo"].scientific_name is None
    assert by_label["tenggiri"].scientific_name == "Scomberomorus commerson"


def _write_taxonomy_csv(tmp_path, mutate):
    """Copy the real taxonomy CSV into tmp_path, applying mutate(rows) in place."""
    with TAXONOMY.open(newline="", encoding="utf-8") as fh:
        rows = [dict(row) for row in csv.DictReader(fh)]
    mutate(rows)
    out = tmp_path / "taxonomy.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return out


def test_taxonomy_rejects_duplicate_and_missing_label(tmp_path):
    # Eleven rows total, but tuna duplicated and bandeng missing: a row-count
    # check alone would accept this, the label-set check must reject it.
    def mutate(rows):
        duplicate_tuna = dict(rows[0])  # first real row is tuna
        rows[:] = [row for row in rows if row["normalized_label"] != "bandeng"]
        rows.append(duplicate_tuna)

    path = _write_taxonomy_csv(tmp_path, mutate=mutate)
    with pytest.raises(ValueError, match="labels"):
        load_taxonomy_csv(path)


def test_taxonomy_preserves_notes_verbatim(tmp_path):
    padded = "  note with surrounding whitespace  "

    def mutate(rows):
        for row in rows:
            if row["normalized_label"] == "tuna":
                row["notes"] = padded
            elif row["normalized_label"] == "bandeng":
                row["notes"] = ""

    path = _write_taxonomy_csv(tmp_path, mutate=mutate)
    by_label = {row.normalized_label: row for row in load_taxonomy_csv(path)}
    assert by_label["tuna"].notes == padded
    assert by_label["bandeng"].notes is None