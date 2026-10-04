from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.inference import predict, quiz_questions

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "game" / "traditional_games.json"
COMPILED_PATH = ROOT / "game" / "compiled_game_content.json"

LABEL_NAMES = {
    "SUKU": "Suku",
    "PROVINSI": "Provinsi",
    "DAERAH": "Daerah",
    "TARIAN": "Tarian",
    "RUMAH_ADAT": "Rumah adat",
    "PAKAIAN_ADAT": "Pakaian adat",
    "MAKANAN": "Makanan",
    "ALAT_MUSIK": "Alat musik",
    "BAHASA": "Bahasa",
    "UPACARA": "Upacara / tradisi",
    "TOKOH": "Tokoh",
    "CAGAR_BUDAYA": "Cagar budaya",
    "KARYA_BUDAYA": "Karya budaya",
    "PERMAINAN_ADAT": "Permainan tradisional",
    "ORGANISASI_BUDAYA": "Organisasi budaya",
}

LABEL_DISTRACTORS = list(LABEL_NAMES)
DISTRACTOR_BANK = {
    "PROVINSI": ["Aceh", "DKI Jakarta", "Jawa Barat", "Jawa Tengah", "Kalimantan Barat", "Sumatera Barat", "Sumatera Selatan", "Sumatra Utara"],
    "DAERAH": ["Jawa", "Kalimantan", "Sulawesi", "Musi Rawas", "Magelang", "Asahan", "Bangka Tengah"],
    "SUKU": ["Betawi", "Gayo", "Dayak Kanyatn", "Minangkabau", "Jawa", "Sunda"],
    "UPACARA": ["Naik Dango", "Sekaten", "Seren Taun", "Ngaben"],
}

# Koordinat ini adalah layout arena 2D ilustratif, bukan koordinat geografis.
# Frontend merendernya sebagai festival/kampung permainan, bukan peta Indonesia.
ADVENTURE_LAYOUT = [
    (0.12, 0.22), (0.30, 0.15), (0.50, 0.20), (0.72, 0.15),
    (0.86, 0.30), (0.72, 0.43), (0.50, 0.38), (0.28, 0.43),
    (0.14, 0.58), (0.32, 0.72), (0.56, 0.68), (0.80, 0.70),
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dedupe_entities(entities: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in entities:
        key = (item["text"].casefold(), item["label"])
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _curate_entity(record: dict, ent: dict, blocked_terms: set[str] | None = None) -> tuple[dict | None, str]:
    text = ent["text"].strip()
    if blocked_terms and text.casefold() in blocked_terms:
        return None, "traditional_game_name_not_ner_target"
    canonical = {k.casefold(): (k, v) for k, v in record.get("canonical_entities", {}).items()}
    if canonical:
        match = canonical.get(text.casefold())
        if not match:
            return None, "not_in_canonical_entity_map"
        canonical_text, canonical_label = match
        return {
            **ent,
            "text": canonical_text,
            "model_label": ent["label"],
            "label": canonical_label,
            "label_corrected": ent["label"] != canonical_label,
        }, "accepted"
    return None, "record_has_no_canonical_entities"


def _blocked_game_terms(records: list[dict]) -> set[str]:
    terms: set[str] = set()
    for item in records:
        terms.add(item["name"].casefold())
        for alias in item.get("aliases", []):
            terms.add(alias.casefold())
        terms.update(part.strip().casefold() for part in item["name"].split("/") if part.strip())
    return terms


def compile_record(record: dict, blocked_terms: set[str] | None = None) -> dict:
    text = record["ner_text"]
    raw_entities = _dedupe_entities(predict(text))
    entities, rejected = [], []
    for ent in raw_entities:
        curated, reason = _curate_entity(record, ent, blocked_terms)
        if curated:
            entities.append(curated)
        else:
            rejected.append({**ent, "reason": reason})
    ner_quiz = [
        {
            "prompt": f'Apa entitas kategori {LABEL_NAMES.get(ent["label"], ent["label"])} yang disebutkan dalam teks?',
            "answer": ent["text"],
            "label": ent["label"],
        }
        for ent in entities
    ]
    return {
        **record,
        "raw_entities": raw_entities,
        "entities": entities,
        "rejected_entities": rejected,
        "ner_quiz": ner_quiz,
        "entity_count": len(entities),
        "corrected_label_count": sum(bool(e.get("label_corrected")) for e in entities),
    }


def compile_all() -> list[dict]:
    records = _read_json(SEED_PATH)
    blocked = _blocked_game_terms(records)
    return [compile_record(item, blocked) for item in records]


@lru_cache(maxsize=1)
def get_catalog() -> list[dict]:
    if COMPILED_PATH.exists():
        return _read_json(COMPILED_PATH)
    return compile_all()


def public_catalog() -> list[dict]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "aliases": item.get("aliases", []),
            "region_context": item.get("region_context", ""),
            "category": item.get("category", ""),
            "players": item.get("players", ""),
            "summary": item.get("summary", ""),
            "values": item.get("values", []),
            "entity_count": item.get("entity_count", len(item.get("entities", []))),
            "source_title": item.get("source_title", ""),
            "source_url": item.get("source_url", ""),
        }
        for item in get_catalog()
    ]


def get_game(game_id: str) -> dict:
    for item in get_catalog():
        if item["id"] == game_id:
            return item
    raise KeyError(game_id)


def _choice_options(correct: str, pool: list[str], rng: random.Random, size: int = 4) -> list[str]:
    others = [x for x in dict.fromkeys(pool) if x != correct]
    rng.shuffle(others)
    options = [correct, *others[: max(0, size - 1)]]
    rng.shuffle(options)
    return options


def _label_question(game: dict, ent: dict, rng: random.Random) -> dict:
    options = _choice_options(ent["label"], LABEL_DISTRACTORS, rng)
    return {
        "type": "label",
        "prompt": f'Kategori budaya apakah “{ent["text"]}” pada teks berikut?',
        "context": game["ner_text"],
        "options": [{"value": x, "label": LABEL_NAMES.get(x, x)} for x in options],
        "answer": ent["label"],
        "explanation": f'{ent["text"]} digunakan sebagai {LABEL_NAMES.get(ent["label"], ent["label"])} pada materi yang telah dikurasi.',
        "game_id": game["id"],
        "game_name": game["name"],
    }


def _blank_question(game: dict, ent: dict, rng: random.Random) -> dict:
    options = _choice_options(ent["text"], DISTRACTOR_BANK.get(ent["label"], []), rng)
    masked = game["ner_text"][: ent["start"]] + "_____" + game["ner_text"][ent["end"] :]
    return {
        "type": "blank",
        "prompt": "Lengkapi bagian yang hilang berdasarkan konteks budaya.",
        "context": masked,
        "options": [{"value": x, "label": x} for x in options],
        "answer": ent["text"],
        "explanation": f'Jawaban merupakan entitas {LABEL_NAMES.get(ent["label"], ent["label"])} yang ditemukan model dan lolos kurasi materi.',
        "game_id": game["id"],
        "game_name": game["name"],
    }


def _gamefact_question(game: dict, catalog: list[dict], rng: random.Random) -> dict:
    options = _choice_options(game["name"], [g["name"] for g in catalog], rng)
    return {
        "type": "gamefact",
        "prompt": "Permainan tradisional apa yang sesuai dengan deskripsi ini?",
        "context": (game.get("summary", "") + " " + game.get("how_to_play", "")).strip(),
        "options": [{"value": x, "label": x} for x in options],
        "answer": game["name"],
        "explanation": f'{game["name"]}: {game.get("region_context", "Indonesia")}. Nilai belajar: {", ".join(game.get("values", []))}.',
        "game_id": game["id"],
        "game_name": game["name"],
    }


def _all_entities(catalog: list[dict]) -> list[dict]:
    return [ent for item in catalog for ent in item.get("entities", [])]


def build_session(mode: str, count: int = 5, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    catalog = get_catalog()
    questions: list[dict] = []

    if mode == "label":
        candidates = [(game, ent) for game in catalog for ent in game.get("entities", [])]
        rng.shuffle(candidates)
        questions = [_label_question(game, ent, rng) for game, ent in candidates[:count]]

    elif mode == "blank":
        candidates = [(game, ent) for game in catalog for ent in game.get("entities", [])]
        rng.shuffle(candidates)
        questions = [_blank_question(game, ent, rng) for game, ent in candidates[:count]]

    elif mode == "gamefact":
        shuffled = catalog[:]
        rng.shuffle(shuffled)
        questions = [_gamefact_question(game, catalog, rng) for game in shuffled[:count]]

    elif mode == "mixed":
        modes = ["label", "blank", "gamefact"]
        combined: list[dict] = []
        for idx, child in enumerate(modes):
            remaining = max(1, count - len(combined))
            child_count = max(1, count // len(modes)) if idx < len(modes) - 1 else remaining
            combined.extend(build_session(child, child_count, rng.randint(0, 10_000_000))["questions"])
        rng.shuffle(combined)
        questions = combined[:count]
    else:
        raise ValueError(f"Mode game tidak dikenal: {mode}")

    return {"mode": mode, "count": len(questions), "questions": questions}


def adventure_map() -> dict:
    catalog = get_catalog()
    nodes = []
    for idx, game in enumerate(catalog):
        x, y = ADVENTURE_LAYOUT[idx % len(ADVENTURE_LAYOUT)]
        nodes.append({
            "id": game["id"],
            "name": game["name"],
            "region_context": game.get("region_context", "Indonesia"),
            "summary": game.get("summary", ""),
            "values": game.get("values", []),
            "entity_count": game.get("entity_count", len(game.get("entities", []))),
            "x": x,
            "y": y,
            "order": idx + 1,
            "difficulty": 1 + (idx // 4),
        })
    return {
        "title": "Festival Permainan Nusantara",
        "note": "Arena 2D ini bersifat ilustratif dan bukan peta geografis Indonesia.",
        "node_count": len(nodes),
        "nodes": nodes,
    }


def build_adventure_challenge(game_id: str, count: int = 3, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    catalog = get_catalog()
    game = get_game(game_id)
    candidates: list[dict] = []
    entities = game.get("entities", [])[:]
    rng.shuffle(entities)
    for ent in entities:
        candidates.append(_label_question(game, ent, rng))
        if DISTRACTOR_BANK.get(ent["label"]):
            candidates.append(_blank_question(game, ent, rng))
    candidates.append(_gamefact_question(game, catalog, rng))
    rng.shuffle(candidates)
    selected = candidates[: max(1, min(count, len(candidates)))]
    return {
        "game": {
            "id": game["id"],
            "name": game["name"],
            "region_context": game.get("region_context", ""),
            "summary": game.get("summary", ""),
            "values": game.get("values", []),
            "source_title": game.get("source_title", ""),
            "source_url": game.get("source_url", ""),
        },
        "count": len(selected),
        "questions": selected,
    }


def custom_text_game(text: str) -> dict:
    entities = _dedupe_entities(predict(text))
    questions = quiz_questions(text)
    return {
        "text": text,
        "entities": entities,
        "questions": questions,
        "entity_count": len(entities),
    }
