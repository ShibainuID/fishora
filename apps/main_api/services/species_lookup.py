"""A catch outside the 11 trained species: find its scientific name, then list it.

The operator types the local market name (e.g. "baronang"). One OpenRouter call
with the web search server tool looks it up on FishBase, FAO, Wikipedia and the
other allow-listed sites and proposes up to three scientific names. A proposal
is kept only when the page excerpt its URL returned names both the local name
and the scientific name, so the link between the two is written in a source,
not inferred by the model. The operator picks one (or none); that human choice
is what creates the species.

A species added this way is ``TAXONOMY_REVIEW_REQUIRED``: buyers see that the
name still needs expert review, and the CV model does not know it until it is
retrained. Its knowledge card starts empty (the approved corpus has nothing on
it) and the web research step looks for leads for every field.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

import httpx

from apps.main_api.contracts import SpeciesRecord
from apps.main_api.errors import InvalidUnlistedSpecies
from apps.main_api.services import web_research
from apps.main_api.services.llm_output import reply_json

logger = logging.getLogger(__name__)

# Local and market names live in Wikipedia far more than in the reference
# databases, so the name lookup also searches it; card facts never do.
LOOKUP_DOMAINS = web_research.ALLOWED_DOMAINS + ("wikipedia.org",)
MAX_CANDIDATES = 3
MAX_NAME_LENGTH = 60
REVIEW_STATUS = "TAXONOMY_REVIEW_REQUIRED"
_NAME = re.compile(r"^[A-Za-z][A-Za-z '\-]*$")
_RANKS = {"species", "genus", "family"}

PROMPT = """Find the scientific name of the fish sold in Indonesia under the local name "{name}".
Search reference sources (FishBase, FAO, Wikipedia). The local name may cover several species.

Rules:
- Give at most {limit} candidates, most likely first.
- Each candidate cites exactly one URL from your search results whose text contains BOTH the local name "{name}" and the scientific name.
- rank is "species" for a binomial, "genus" or "family" when the name only covers a group.
- If no source links the local name to a scientific name, return no candidates. Do not guess.
Answer only JSON: {{"candidates": [{{"scientific_name": "<name>", "english_name": "<English common name or null>", "rank": "species"|"genus"|"family", "url": "<url>"}}]}}
"""


@dataclass(frozen=True)
class NameMatch:
    scientific_name: str
    english_name: str | None
    rank: str
    url: str
    title: str
    existing_species_id: str | None = None


def clean_name(local_name: str) -> str:
    """The local name as typed, trimmed; rejects anything that is not a plain name."""
    name = " ".join((local_name or "").split())
    if not name or len(name) > MAX_NAME_LENGTH or not _NAME.match(name):
        raise InvalidUnlistedSpecies("local name must be 1 to 60 letters, spaces, hyphens or apostrophes")
    return name


def label_for(local_name: str) -> str:
    """``Ikan Baronang`` -> ``baronang``: lowercase ASCII words joined by underscores."""
    ascii_name = unicodedata.normalize("NFKD", local_name).encode("ascii", "ignore").decode().lower()
    words = [w for w in re.split(r"[^a-z]+", ascii_name) if w]
    if words and words[0] == "ikan" and len(words) > 1:  # "ikan" just means "fish"
        words = words[1:]
    return "_".join(words)


def _mentions(text: str, name: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(name.lower())}(?![a-z])", text.lower()) is not None


def lookup(local_name: str, settings, species_repo=None, post=httpx.post) -> list[NameMatch]:
    """Scientific-name candidates for a local fish name, each tied to a source."""
    name = clean_name(local_name)
    search_name = name[5:] if name.lower().startswith("ikan ") else name
    data = web_research.search(settings, PROMPT.format(name=search_name, limit=MAX_CANDIDATES), post,
                               LOOKUP_DOMAINS)
    message = data["choices"][0]["message"]
    excerpts = web_research.page_excerpts(message, LOOKUP_DOMAINS)
    known = {s.scientific_name.lower(): s.id for s in (species_repo.list_all() if species_repo else [])
             if s.scientific_name}

    matches: list[NameMatch] = []
    for item in reply_json(message.get("content") or "").get("candidates", []):
        if not isinstance(item, dict):
            continue
        scientific = " ".join(str(item.get("scientific_name") or "").split())
        url = str(item.get("url") or "").strip()
        rank = str(item.get("rank") or "species").lower()
        if not scientific or url not in excerpts or rank not in _RANKS:
            continue
        title, text = excerpts[url]
        # The source itself must tie the local name to the scientific name.
        if not (_mentions(text, search_name) and _mentions(text, scientific)):
            continue
        if any(m.scientific_name.lower() == scientific.lower() for m in matches):
            continue
        english = item.get("english_name")
        matches.append(NameMatch(scientific_name=scientific, english_name=str(english).strip() if english else None,
                                 rank=rank, url=url, title=title, existing_species_id=known.get(scientific.lower())))
        if len(matches) == MAX_CANDIDATES:
            break
    return matches


def register(species_repo, local_name: str, *, scientific_name: str | None = None,
             taxonomic_rank: str | None = None, source_url: str | None = None,
             operator_id: str | None = None) -> SpeciesRecord:
    """The species to declare the catch as: an existing one when the name or the
    scientific name is already known, otherwise a new species under review."""
    name = clean_name(local_name)
    label = label_for(name)
    if not label:
        raise InvalidUnlistedSpecies("local name must contain letters")
    existing = species_repo.get_by_normalized_label(label)
    if existing is not None:
        return existing
    scientific = " ".join((scientific_name or "").split()) or None
    if scientific:
        if len(scientific) > 160 or not re.match(r"^[A-Za-z][A-Za-z .\-]*$", scientific):
            raise InvalidUnlistedSpecies("scientific name is not a plain Latin name")
        for record in species_repo.list_all():
            if record.scientific_name and record.scientific_name.lower() == scientific.lower():
                return record
    rank = (taxonomic_rank or "").lower()
    rank = rank if scientific and rank in _RANKS else "unknown"
    display = " ".join(w[:1].upper() + w[1:] for w in label.split("_"))
    source = f"name source: {source_url}" if scientific and source_url else "no source found for a scientific name"
    record = SpeciesRecord(
        id=f"species_{label}"[:80], normalized_label=label[:80], common_name_id=display,
        scientific_name=scientific, taxonomic_rank=rank, taxonomy_status=REVIEW_STATUS,
        notes=f"Added from an operator's catch (operator {operator_id or 'unknown'}); {source}.",
    )
    try:
        return species_repo.create(record)
    except Exception:
        # Two operators listing the same fish at once: the other insert won.
        again = species_repo.get_by_normalized_label(label)
        if again is not None:
            return again
        raise
