"""Regenerate the four offline agent-stage files for the Fishora corpus.

Single source of truth for the candidate corpus: every claim below was
revalidated on 2026-08-23 against the cited URL. Run from the repo root:

    .venv/bin/python -m scripts.build_knowledge_corpus
    .venv/bin/python -m scripts.corpus_pipeline collect \
        --stage-dir artifacts/knowledge_sources/offline \
        --candidate-dir artifacts/knowledge_sources/candidates

The three research-agent groups produced research.json (source identification),
fact_extraction.json (claim formalization) and verification.json (source
revalidation); knowledge_editor.json is the editor handoff whose records become
candidate chunks. Only the CLI approval action may create `verified` copies.
"""

from __future__ import annotations

import json
from pathlib import Path

from apps.main_api.services.corpus import (
    STAGE_FILES,
    OfflineStageFile,
    OfflineStageRecord,
)

REVIEWED_AT = "2026-08-23T00:00:00+00:00"

SOURCES = {
    "fishbase_chanos_chanos": {
        "title": "Chanos chanos, Milkfish: fisheries, aquaculture, gamefish, bait",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Chanos-chanos.html",
        "publisher": "FishBase",
    },
    "marinade_4962": {
        "title": "Karakteristik Proses Pengolahan Bandeng (Chanos chanos) Presto Skala UMKM di Kecamatan Juwana, Kabupaten Pati",
        "source_type": "journal_article",
        "url": "https://doi.org/10.31629/marinade.v5i02.4962",
        "publisher": "Marinade (jurnal pengolahan produk perikanan)",
    },
    "fishbase_eleutheronema_tetradactylum": {
        "title": "Eleutheronema tetradactylum, Fourfinger threadfin: fisheries, aquaculture",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Eleutheronema-tetradactylum.html",
        "publisher": "FishBase",
    },
    "fishbase_johnius_trachycephalus": {
        "title": "Johnius trachycephalus, Leaftail croaker: fisheries",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Johnius-trachycephalus.html",
        "publisher": "FishBase",
    },
    "coj_5_1_1": {
        "title": "Business Analysis of Gulamah (Johnius trachycephalus) Salted Fish Small and Medium Enterprises (SMEs) in Perlis, Berandan Barat, Langkat, North Sumatera",
        "source_type": "journal_article",
        "url": "https://doi.org/10.29244/coj.5.1.1-8",
        "publisher": "Coastal and Ocean Journal (COJ)",
    },
    "manfish_v2i3_489": {
        "title": "Studi Potensi Ikan Gulamah (Johnius trachycephalus) Sebagai Bahan Baku Surimi dan Produk Olahan Berbasis Daging Ikan",
        "source_type": "journal_article",
        "url": "https://doi.org/10.31573/manfish.v2i3.489",
        "publisher": "Manfish Journal",
    },
    "fishbase_nibea_albiflora": {
        "title": "Nibea albiflora, Yellow drum: fisheries",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Nibea-albiflora.html",
        "publisher": "FishBase",
    },
    "fishbase_oreochromis_mossambicus": {
        "title": "Oreochromis mossambicus, Mozambique tilapia: fisheries, aquaculture, gamefish, aquarium",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Oreochromis-mossambicus.html",
        "publisher": "FishBase",
    },
    "jbau_86202": {
        "title": "Quality evaluation of fish burger from tilapia (Oreochromis mossambicus) during frozen storage (-18C)",
        "source_type": "journal_article",
        "url": "https://doi.org/10.5455/JBAU.86202",
        "publisher": "Journal of Bangladesh Agricultural University",
    },
    "fao_en_niletilapia": {
        "title": "FAO Cultured Aquatic Species Fact Sheet: Oreochromis niloticus (Nile tilapia)",
        "source_type": "species_fact_sheet",
        "url": "https://www.fao.org/fishery/docs/CDrom/aquaculture/I1129m/file/en/en_niletilapia.htm",
        "publisher": "Food and Agriculture Organization of the United Nations",
    },
    "fishbase_oreochromis_niloticus": {
        "title": "Oreochromis niloticus, Nile tilapia: fisheries, aquaculture",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Oreochromis-niloticus.html",
        "publisher": "FishBase",
    },
    "fishbase_rastrelliger_faughni": {
        "title": "Rastrelliger faughni, Island mackerel: fisheries, gamefish",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Rastrelliger-faughni.html",
        "publisher": "FishBase",
    },
    "jma_22_2_210": {
        "title": "Value Chain Analysis of Island Mackerel (Rastrelliger faughni) in Selected Coastal Municipalities in Lagonoy Gulf, Philippines",
        "source_type": "journal_article",
        "url": "https://doi.org/10.17358/jma.22.2.210",
        "publisher": "Jurnal Manajemen dan Agribisnis",
    },
    "fishbase_upeneus_moluccensis": {
        "title": "Upeneus moluccensis, Goldband goatfish: fisheries",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Upeneus-moluccensis.html",
        "publisher": "FishBase",
    },
    "foodchem_2008": {
        "title": "Sensory, microbiological and chemical assessment of the freshness of red mullet (Mullus barbatus) and goldband goatfish (Upeneus moluccensis) during storage in ice",
        "source_type": "journal_article",
        "url": "https://doi.org/10.1016/j.foodchem.2008.09.078",
        "publisher": "Food Chemistry (Elsevier)",
    },
    "fao_ac478e00": {
        "title": "FAO Species Catalogue Vol. 2: Scombrids of the World (tunas, mackerels, bonitos)",
        "source_type": "species_catalogue",
        "url": "https://www.fao.org/4/ac478e/ac478e00.htm",
        "publisher": "Food and Agriculture Organization of the United Nations",
    },
    "fao_ac478e11": {
        "title": "FAO Species Catalogue Vol. 2, chapter 11: Thunnus (genus account and keys)",
        "source_type": "species_catalogue_pdf",
        "url": "https://www.fao.org/docrep/pdf/009/ac478e/ac478e11.pdf",
        "publisher": "Food and Agriculture Organization of the United Nations",
    },
    "fishbase_scomberomorus_commerson": {
        "title": "Scomberomorus commerson, Narrow-barred Spanish mackerel: fisheries, gamefish",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Scomberomorus-commerson.html",
        "publisher": "FishBase",
    },
    "fishbase_tenggiri_common_name": {
        "title": "FishBase Common Names search: 'Tenggiri'",
        "source_type": "common_name_page",
        "url": "https://www.fishbase.se/ComNames/CommonNameSearchList.cfm?CommonName=tenggiri",
        "publisher": "FishBase",
    },
    "fishbase_scomberomorus_guttatus": {
        "title": "Scomberomorus guttatus, Indo-Pacific king mackerel: fisheries, gamefish",
        "source_type": "species_summary",
        "url": "https://www.fishbase.se/summary/Scomberomorus-guttatus.html",
        "publisher": "FishBase",
    },
    "fishora_corpus_governance": {
        "title": "Fishora corpus governance rule for unresolved labels",
        "source_type": "internal_policy",
        "url": "artifacts/knowledge_sources/README.md",
        "publisher": "Fishora corpus team",
    },
}

# (claim_id, species_label, source_id, category, content, source_quote)
CLAIMS = [
    # --- bandeng (Chanos chanos, milkfish) ---------------------------------
    ("claim_bandeng_identity_001", "bandeng", "fishbase_chanos_chanos", "identity",
     "Bandeng is the milkfish Chanos chanos (Fabricius, 1775), the only species in family "
     "Chanidae (order Gonorynchiformes); a marine, freshwater and brackish benthopelagic, "
     "amphidromous species of the Indo-West Pacific.",
     "Teleostei (teleosts) > Gonorynchiformes (Milkfishes) > Chanidae (Milkfish) ... Marine; "
     "freshwater; brackish; benthopelagic; amphidromous"),
    ("claim_bandeng_physical_001", "bandeng", "fishbase_chanos_chanos", "physical_characteristics",
     "Milkfish have an elongate, somewhat compressed body with a small toothless mouth, falcate "
     "pectoral fins and a large deeply forked caudal fin; olive green dorsally with silvery "
     "flanks; adults reach 180 cm SL and 14 kg.",
     "body elongate and somewhat compressed; mouth small and toothless ... pectoral fins falcate; "
     "caudal fin large and deeply forked ... Colour of the body olive green dorsally; flanks "
     "silvery; unpaired fins with dark margins ... Max length: 180 cm SL ... max. published "
     "weight: 14.0 kg"),
    ("claim_bandeng_processing_001", "bandeng", "marinade_4962", "processing_methods",
     "In Indonesia, bandeng is processed as 'bandeng presto' (pressure-cooked milkfish with "
     "softened bones); the presto processing chain at small and medium enterprise scale is "
     "documented for Juwana District, Pati Regency, Central Java.",
     "Handoko, Y. P., Apriani, D. A. K., & Amrizal, S. N. (2022). KARAKTERISTIK PROSES "
     "PENGOLAHAN BANDENG (Chanos chanos) PRESTO SKALA UMKM DI KECAMATAN JUWANA, KABUPATEN PATI. "
     "Marinade, 5(02), 157-165."),
    ("claim_bandeng_commercial_001", "bandeng", "fishbase_chanos_chanos", "commercial_uses",
     "Milkfish is highly commercial in both capture fisheries and aquaculture; larvae are "
     "collected from rivers and grown in culture ponds into juveniles marketed fresh, smoked, "
     "canned or frozen, and brood stock can be raised and spawned in captivity.",
     "Fisheries: highly commercial; aquaculture: commercial ... Larvae are collected from rivers "
     "and are grown in culture ponds into juveniles which are marketed fresh, smoked, canned or "
     "frozen. Brood stocks can be raised and spawned in captivity to produce larvae in the "
     "hatchery"),

    # --- senangin (Eleutheronema tetradactylum, fourfinger threadfin) -------
    ("claim_senangin_identity_001", "senangin", "fishbase_eleutheronema_tetradactylum", "identity",
     "Senangin is the fourfinger threadfin Eleutheronema tetradactylum (Shaw, 1804), family "
     "Polynemidae (Threadfins), distinguished by four free pectoral filaments; an Indo-Pacific "
     "marine, freshwater and brackish pelagic-neritic species.",
     "Teleostei (teleosts) > Carangaria/misc (Various families in series Carangaria) > "
     "Polynemidae (Threadfins) ... pectoral filaments 4 ... Marine; freshwater; brackish; "
     "pelagic-neritic; amphidromous"),
    ("claim_senangin_physical_001", "senangin", "fishbase_eleutheronema_tetradactylum", "physical_characteristics",
     "Fourfinger threadfin grow to 200 cm TL and 145 kg (common length 50 cm TL); pectoral fin "
     "membranes are vivid yellow in life (dusky yellow in large specimens) and pectoral "
     "filaments are white; the species is a protandrous hermaphrodite.",
     "Max length: 200 cm TL ... common length: 50.0 cm TL ... max. published weight: 145.0 kg "
     "... pectoral fin membranes vivid yellow in life, except in large specimens > ca 35 cm SL "
     "which is dusky yellow; pectoral filaments white ... Protandrous hermaphrodites."),
    ("claim_senangin_commercial_001", "senangin", "fishbase_eleutheronema_tetradactylum", "commercial_uses",
     "Fourfinger threadfin is a highly commercial food fish with commercial aquaculture; "
     "adults occur mainly over shallow muddy bottoms in coastal waters and enter rivers; "
     "marketed fresh, frozen, and dried or salted.",
     "Adults occur mainly over shallow muddy bottoms in coastal waters. Also enter rivers ... "
     "Marketed fresh, frozen, and dried or salted. ... Fisheries: highly commercial; "
     "aquaculture: commercial"),

    # --- gulamah (Johnius trachycephalus, leaftail croaker) -----------------
    ("claim_gulamah_identity_001", "gulamah", "fishbase_johnius_trachycephalus", "identity",
     "Gulamah is the leaftail croaker Johnius trachycephalus (Bleeker, 1851), a small sciaenid "
     "(drums or croakers) of the Indo-Pacific (Thailand, Sumatra, Borneo) reaching 13 cm SL; it "
     "inhabits shallow coastal waters, estuaries and rivers and is a food fish.",
     "Teleostei (teleosts) > Eupercaria/misc (Various families in series Eupercaria) > "
     "Sciaenidae (Drums or croakers) ... Max length: 13.0 cm SL ... Inhabits shallow coastal "
     "waters, estuaries and rivers (Ref. 9772). A food fish."),
    ("claim_gulamah_processing_001", "gulamah", "coj_5_1_1", "processing_methods",
     "Gulamah is processed into salted fish (ikan asin) by small and medium enterprises; the "
     "salted-fish gulamah business is documented in Perlis, Berandan Barat, Langkat, North "
     "Sumatra.",
     "Shalichaty, S. F., Ratrinia, P. W., & Damanik, S. (2021). BUSINESS ANALYSIS OF GULAMAH "
     "(Johnius trachycephalus) SALTED FISH SMALL AND MEDIUM ENTERPRISES (SMEs) IN PERLIS, "
     "BERANDAN BARAT, LANGKAT, NORTH SUMATERA. Coastal and Ocean Journal (COJ), 5(1), 1-8."),
    ("claim_gulamah_processing_002", "gulamah", "manfish_v2i3_489", "processing_methods",
     "Gulamah is studied as raw material for surimi and fish-meat-based processed products, "
     "expanding its use beyond salted fish.",
     "Laksono, U. T., Lasmi, L., Sasongko, L. W., & Nofreeana, A. (2022). Studi Potensi Ikan "
     "Gulamah (Johnius trachycephalus) Sebagai Bahan Baku Surimi dan Produk Olahan Berbasis "
     "Daging Ikan. Manfish Journal, 3(2), 119-127."),

    # --- gelama_bunga (Nibea albiflora, yellow drum) ------------------------
    ("claim_gelama_bunga_identity_001", "gelama_bunga", "fishbase_nibea_albiflora", "identity",
     "Gelama bunga is the yellow drum Nibea albiflora (Richardson, 1846), family Sciaenidae "
     "(drums or croakers), a temperate benthopelagic species of the Northwest Pacific (southern "
     "Japan and East China Sea) reaching 43.5 cm SL and 1.5 kg.",
     "Teleostei (teleosts) > Eupercaria/misc (Various families in series Eupercaria) > "
     "Sciaenidae (Drums or croakers) ... Max length: 43.5 cm SL ... max. published weight: 1.5 "
     "kg ... Northwest Pacific: southern Japan and East China Sea."),
    ("claim_gelama_bunga_commercial_001", "gelama_bunga", "fishbase_nibea_albiflora", "commercial_uses",
     "Yellow drum is a commercially fished species found near shore on mud to sandy-mud bottoms "
     "in semi-enclosed sea areas, and is also used in Chinese medicine.",
     "Found near shore, including semi-enclosed sea areas, in mud to sandy mud bottom ... Used "
     "in Chinese medicine ... Fisheries: commercial"),

    # --- mujair (Oreochromis mossambicus, Mozambique tilapia) ---------------
    ("claim_mujair_identity_001", "mujair", "fishbase_oreochromis_mossambicus", "identity",
     "Mujair is the Mozambique tilapia Oreochromis mossambicus (Peters, 1852), family "
     "Cichlidae (subfamily Pseudocrenilabrinae); a highly euryhaline freshwater/brackish "
     "benthopelagic maternal mouthbrooder, widely introduced for aquaculture and often "
     "outcompeting local species where it escapes to the wild.",
     "Teleostei (teleosts) > Cichliformes (Cichlids, convict blennies) > Cichlidae (Cichlids) > "
     "Pseudocrenilabrinae ... Highly euryhaline ... maternal mouthbrooder ... Widely introduced "
     "for aquaculture, but escaped and established itself in the wild in many countries, often "
     "outcompeting local species"),
    ("claim_mujair_taste_001", "mujair", "fishbase_oreochromis_mossambicus", "taste_texture",
     "Mozambique tilapia has excellent palatability with a small head, large dress-out weight "
     "and fillets without small bones.",
     "Excellent palatability (Ref. 6465), with small head and large dress-out weight (Ref. 61), "
     "and filets without small bones (Ref. 57960)."),
    ("claim_mujair_processing_001", "mujair", "jbau_86202", "processing_methods",
     "Mozambique tilapia is used to make fish burgers; the quality of the tilapia fish burger "
     "was evaluated during frozen storage at -18C.",
     "Lithi, U., Faridullah, M., Uddin, M., Mehbub, M., & Zafar, M. (2020). Quality evaluation "
     "of fish burger from tilapia (Oreochromis mossambicus) during frozen storage (-18c). "
     "Journal of Bangladesh Agricultural University."),

    # --- nila (Oreochromis niloticus, Nile tilapia) -------------------------
    ("claim_nila_identity_001", "nila", "fao_en_niletilapia", "identity",
     "Nila is the Nile tilapia Oreochromis niloticus (Linnaeus, 1758) [Cichlidae]; globally the "
     "most important tilapia species in fish farming, and the predominant cultured species "
     "among tilapias.",
     "Oreochromis niloticus (Linnaeus, 1758) [Cichlidae] ... Several species of tilapia are "
     "cultured commercially, but Nile tilapia is the predominant cultured species worldwide."),
    ("claim_nila_physical_001", "nila", "fishbase_oreochromis_niloticus", "physical_characteristics",
     "Nile tilapia is a large deep-bodied tilapia with a relatively small head; its most "
     "distinguishing characteristic is regular vertical stripes throughout the depth of the "
     "caudal fin at all life stages; reaches 60 cm SL and 4.3 kg.",
     "A large deep-bodied tilapia, with a relatively small head ... Most distinguishing "
     "characteristic is the presence, at all life stages, of regular vertical stripes "
     "throughout depth of caudal fin ... Max length: 60.0 cm SL ... max. published weight: 4.3 kg"),
    ("claim_nila_commercial_001", "nila", "fao_en_niletilapia", "commercial_uses",
     "Tilapia is the second most important group of farmed fish after carps and the most widely "
     "grown of any farmed fish; global tilapia production was projected to increase from 1.5 "
     "million tonnes in 2003 to 2.5 million tonnes by 2010, with a sales value above USD 5 "
     "billion, most of it attributed to Nile tilapia.",
     "Tilapia (including all species) is the second most important group of farmed fish after "
     "carps, and the most widely grown of any farmed fish ... global production of all species "
     "of tilapia is projected to increase from 1.5 million tonnes in 2003 to 2.5 million tonnes "
     "by 2010, with a sales value of more than USD 5 billion. Most of this enhanced production "
     "is expected to be attributed to Nile tilapia."),
    ("claim_nila_taste_001", "nila", "fao_en_niletilapia", "taste_texture",
     "Nile tilapia fillets are described as an ideal menu addition due to their reasonable "
     "price, year-round supply, mild, delicious flavour and flexibility in preparation; "
     "virtually all casual dining restaurant chains in the USA feature tilapia.",
     "which are an ideal menu addition due to their reasonable price, year-round supply, mild, "
     "delicious flavour and flexibility in preparation. Virtually all casual dining restaurant "
     "chains in the USA feature tilapia"),

    # --- kembung (Rastrelliger faughni, island mackerel) --------------------
    ("claim_kembung_identity_001", "kembung", "fishbase_rastrelliger_faughni", "identity",
     "Kembung corresponds to the island mackerel Rastrelliger faughni Matsui, 1967, family "
     "Scombridae (mackerels, tunas, bonitos), an epipelagic neritic species of the Indo-West "
     "Pacific; recognised by a black blotch behind the pectoral fin base and a yellowish "
     "silver belly.",
     "Teleostei (teleosts) > Scombriformes (Mackerels) > Scombridae (Mackerels, tunas, bonitos) "
     "> Scombrinae ... A black blotch behind pectoral fin base. The belly is yellowish silver"),
    ("claim_kembung_physical_001", "kembung", "fishbase_rastrelliger_faughni", "physical_characteristics",
     "Island mackerel reach 24 cm FL and 750 g, with the head longer than the body depth, 2 to 6 "
     "large spots at the base of the first dorsal fin, and a swim bladder present; they form "
     "schools of equally sized individuals in waters where surface temperature does not fall "
     "below 17C.",
     "Head longer than body depth. ... Swim bladder present. ... 2 to 6 large spots are at the "
     "base of the first dorsal fin ... Max length: 24.0 cm FL ... max. published weight: 750.00 "
     "g ... Forms schools of equally sized individuals."),
    ("claim_kembung_commercial_001", "kembung", "jma_22_2_210", "commercial_uses",
     "Island mackerel (Rastrelliger faughni) supports a commercial fishery and an analysed "
     "value chain in coastal municipalities, e.g. in Lagonoy Gulf, Philippines; FishBase lists "
     "it as commercial and gamefish.",
     "Jamer, M. M. N., & Manzano, M. T. J. (2025). Value Chain Analysis of Island Mackerel "
     "(Rastrelliger faughni) in Selected Coastal Municipalities in Lagonoy Gulf, Philippines. "
     "Jurnal Manajemen Dan Agribisnis, 22(2), 210."),

    # --- kuniran (Upeneus moluccensis, goldband goatfish) -------------------
    ("claim_kuniran_identity_001", "kuniran", "fishbase_upeneus_moluccensis", "identity",
     "Kuniran is the goldband goatfish Upeneus moluccensis (Bleeker, 1855), family Mullidae "
     "(goatfishes), distinguished by a mid-lateral yellow or gold stripe from the eye to the "
     "upper caudal-fin base, white barbels and red caudal-fin bars.",
     "Teleostei (teleosts) > Mulliformes (Goatfishes) > Mullidae (Goatfishes) ... one "
     "mid-lateral body stripe yellow or gold from eye to upper caudal-fin base ... white "
     "barbels; silvery-rose body"),
    ("claim_kuniran_physical_001", "kuniran", "fishbase_upeneus_moluccensis", "physical_characteristics",
     "Goldband goatfish reach 22.5 cm TL (common length 18 cm TL); they form large schools in "
     "coastal waters with a muddy substrate and usually swim fast with short stops to feed.",
     "Found in coastal waters with a muddy substrate. Forms large schools ... Usually fast "
     "swimming with short stops to feed ... Max length: 22.5 cm TL ... common length: 18.0 cm TL"),
    ("claim_kuniran_commercial_001", "kuniran", "fishbase_upeneus_moluccensis", "commercial_uses",
     "Goldband goatfish is a commercial food fish sold fresh in markets; it is also utilized "
     "for fish meal and valued for its roe.",
     "Sold fresh in markets. Utilized for fish meal. Valued also for its roe ... Fisheries: "
     "commercial"),
    ("claim_kuniran_processing_001", "kuniran", "foodchem_2008", "processing_methods",
     "Freshness of goldband goatfish (Upeneus moluccensis) is assessed by sensory, "
     "microbiological and chemical methods during storage in ice.",
     "OZYURT, G., KULEY, E., OZKUTUK, S., & OZOGUL, F. (2009). Sensory, microbiological and "
     "chemical assessment of the freshness of red mullet (Mullus barbatus) and goldband goatfish "
     "(Upeneus moluccensis) during storage in ice. Food Chemistry, 114(2), 505-510."),

    # --- tuna (genus Thunnus) -----------------------------------------------
    ("claim_tuna_identity_001", "tuna", "fao_ac478e00", "identity",
     "The 'tuna' label is pinned at genus level to Thunnus (family Scombridae), which the FAO "
     "Scombrids of the World catalogue treats as seven species: T. alalunga, T. albacares, "
     "T. atlanticus, T. maccoyii, T. obesus, T. thynnus and T. tonggol.",
     "Thunnus: Thunnus alalunga, Thunnus albacares, Thunnus atlanticus, Thunnus maccoyii, "
     "Thunnus obesus, Thunnus thynnus, Thunnus tonggol"),
    ("claim_tuna_identity_002", "tuna", "fao_ac478e11", "identity",
     "The Thunnus chapter of the FAO Scombrids catalogue (AC478E11.pdf) carries the illustrated "
     "key to genera and species of Scombridae and the per-species accounts of all seven Thunnus "
     "species.",
     "2.1 Illustrated Key to Genera and Species of Scombridae ... Thunnus ... Thunnus alalunga, "
     "Thunnus albacares, Thunnus atlanticus, Thunnus maccoyii, Thunnus obesus, Thunnus thynnus, "
     "Thunnus tonggol"),
    ("claim_tuna_commercial_001", "tuna", "fao_ac478e00", "commercial_uses",
     "The FAO Scombrids catalogue is the reference inventory for tuna and mackerel fisheries: "
     "it covers all 49 known scombrid species with wide-ranging information on habitat, biology "
     "and fisheries.",
     "The present volume covers all 49 species of scombrids known so far ... wide-ranging "
     "information on habitat, biology, and fisheries"),

    # --- tenggiri (Scomberomorus, ambiguous label) --------------------------
    ("claim_tenggiri_identity_001", "tenggiri", "fishbase_tenggiri_common_name", "identity",
     "'Tenggiri' (Bahasa Indonesia and Malay, Indonesia and Malaysia) is a vernacular name "
     "shared by five species: Sarda orientalis, Scomberomorus commerson, Scomberomorus "
     "guttatus, Scomberomorus koreanus and Scomberomorus lineolatus; the label is therefore "
     "ambiguous without a species assignment.",
     "List of Common Names for 'Tenggiri' [n=7] ... Species: Sarda orientalis, Scomberomorus "
     "commerson, Scomberomorus guttatus, Scomberomorus koreanus, Scomberomorus lineolatus"),
    ("claim_tenggiri_identity_002", "tenggiri", "fishbase_scomberomorus_commerson", "identity",
     "Scomberomorus commerson (Lacepede, 1800), the narrow-barred Spanish mackerel, is one "
     "candidate species for 'tenggiri': a large pelagic scombrid of the Indo-West Pacific "
     "reaching 240 cm FL, with iridescent blue-grey back and numerous thin wavy vertical "
     "bands.",
     "Scomberomorus commerson (Lacepede, 1800) ... Narrow-barred Spanish mackerel ... Max "
     "length: 240 cm FL ... Colour of back iridescent blue-grey, sides silver with bluish "
     "reflections, marked with numerous thin, wavy vertical bands"),
    ("claim_tenggiri_identity_003", "tenggiri", "fishbase_scomberomorus_guttatus", "identity",
     "Scomberomorus guttatus (Bloch & Schneider, 1801), the Indo-Pacific king mackerel, is "
     "another candidate species for 'tenggiri', reaching 81.5 cm FL and 4 kg; sides silvery "
     "white with several rows of round dark brownish spots along the lateral line.",
     "Scomberomorus guttatus (Bloch & Schneider, 1801) ... Indo-Pacific king mackerel ... Sides "
     "silvery white with several rows of round dark brownish spots scattered in about three "
     "irregular rows along the lateral line ... Max length: 81.5 cm FL ... max. published "
     "weight: 4.0 kg"),
    ("claim_tenggiri_processing_001", "tenggiri", "fishbase_scomberomorus_commerson", "processing_methods",
     "S. commerson is marketed mainly fresh, also dried-salted, commonly made into fish balls, "
     "and frozen, smoked or canned; a lipid-soluble ciguatoxin-like toxin has been found in the "
     "flesh of specimens from the east coast of Queensland, Australia.",
     "Marketed mainly fresh; also dried-salted; commonly made into fish balls (Ref. 9684), "
     "frozen, smoked, and canned (Ref. 9987). ... A lipid-soluble toxin, similar to ciguatoxin "
     "has been found in the flesh of specimens caught on the east coast of Queensland, "
     "Australia."),

    # --- gembolo (unresolved) -----------------------------------------------
    ("claim_gembolo_identity_001", "gembolo", "fishora_corpus_governance", "identity",
     "LIMITATION: no scientific identity, physical description, taste/texture, processing or "
     "commercial claim may be assigned to the label 'gembolo' without expert confirmation; the "
     "label is unresolved in this corpus and only this limitation record exists for it.",
     "No scientific identity or factual culinary claims may be assigned to the label 'gembolo' "
     "without expert confirmation."),
]


def main() -> None:
    offline_dir = Path("artifacts/knowledge_sources/offline")
    offline_dir.mkdir(parents=True, exist_ok=True)
    sources = [
        {
            "id": source_id,
            "reviewed_at": REVIEWED_AT,
            "verification_status": "candidate",
            **metadata,
        }
        for source_id, metadata in SOURCES.items()
    ]
    for filename in STAGE_FILES:
        stage = filename[: -len(".json")]
        records = [
            OfflineStageRecord(
                claim_id=claim_id,
                source_id=source_id,
                species_label=species_label,
                category=category,
                content=content,
                source_quote=quote,
                stage=stage,
                verification_status="candidate",
            )
            for claim_id, species_label, source_id, category, content, quote in CLAIMS
        ]
        payload = OfflineStageFile(stage=stage, sources=sources, records=records)
        (offline_dir / filename).write_text(
            json.dumps(json.loads(payload.model_dump_json()), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(f"wrote {len(STAGE_FILES)} stage files with {len(CLAIMS)} claims "
          f"and {len(SOURCES)} sources -> {offline_dir}")


if __name__ == "__main__":
    main()