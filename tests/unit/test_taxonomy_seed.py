from pathlib import Path

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