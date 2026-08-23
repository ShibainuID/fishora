from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SpeciesRecord:
    id: str
    normalized_label: str
    common_name_id: str
    scientific_name: str | None
    taxonomic_rank: str
    taxonomy_status: str
    notes: str | None


@dataclass
class PredictionRecord:
    id: str
    image_reference: str
    predicted_species_id: str
    confidence: float
    top_candidates: list[dict[str, object]]
    model_version: str
    verification_status: Literal["pending", "confirmed", "corrected"]
    verified_species_id: str | None = None


@dataclass(frozen=True)
class TaxonomySeed:
    raw_folder: str
    raw_label: str
    normalized_label: str
    scientific_name: str | None
    common_name_id: str
    taxonomic_rank: str
    confidence: str
    source: str
    notes: str | None
    taxonomy_status: str