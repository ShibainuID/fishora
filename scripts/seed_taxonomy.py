"""Seed fish_species from the taxonomy CSV (idempotent upsert of the 11 labels).

Usage: FISHORA_DATABASE_URL=... python -m scripts.seed_taxonomy
"""

from pathlib import Path

from apps.main_api.config import MainSettings
from apps.main_api.db.repositories import seed_taxonomy
from apps.main_api.db.session import session_factory

TAXONOMY_PATH = Path("artifacts/Dataset/fishora_dataset/metadata/taxonomy.csv")


def main() -> None:
    settings = MainSettings()
    with session_factory(settings)() as session:
        written = seed_taxonomy(session, TAXONOMY_PATH)
        session.commit()
    print(f"seeded {written} taxonomy rows")


if __name__ == "__main__":
    main()