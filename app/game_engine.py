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
        # Also block slash-separated display variants.
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


def _all_entities(catalog: list[dict]) -> list[dict]:
    return [ent for item in catalog for ent in item.get("entities", [])]


def build_session(mode: str, count: int = 5, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    catalog = get_catalog()
    entities = _all_entities(catalog)
    questions: list[dict] = []

    if mode == "label":
        candidates = [(game, ent) for game in catalog for ent in game.get("entities", [])]
        rng.shuffle(candidates)
        for game, ent in candidates[:count]:
            options = _choice_options(ent["label"], LABEL_DISTRACTORS, rng)
            questions.append({
                "type": "label",
                "prompt": f'Kategori budaya apakah “{ent["text"]}” pada teks berikut?',
                "context": game["ner_text"],
                "options": [{"value": x, "label": LABEL_NAMES.get(x, x)} for x in options],
                "answer": ent["label"],
                "explanation": f'{ent["text"]} dikenali model sebagai {LABEL_NAMES.get(ent["label"], ent["label"])}.',
                "game_id": game["id"],
                "game_name": game["name"],
            })

    elif mode == "blank":
        candidates = [(game, ent) for game in catalog for ent in game.get("entities", [])]
        rng.shuffle(candidates)
        for game, ent in candidates[:count]:
            curated_pool = DISTRACTOR_BANK.get(ent["label"], [])
            options = _choice_options(ent["text"], curated_pool, rng)
            masked = game["ner_text"][: ent["start"]] + "_____" + game["ner_text"][ent["end"] :]
            questions.append({
                "type": "blank",
                "prompt": "Lengkapi bagian yang hilang berdasarkan konteks budaya.",
                "context": masked,
                "options": [{"value": x, "label": x} for x in options],
                "answer": ent["text"],
                "explanation": f'Jawaban berasal dari entitas {LABEL_NAMES.get(ent["label"], ent["label"])} yang dikenali model.',
                "game_id": game["id"],
                "game_name": game["name"],
            })

    elif mode == "gamefact":
        shuffled = catalog[:]
        rng.shuffle(shuffled)
        for game in shuffled[:count]:
            all_names = [g["name"] for g in catalog]
            options = _choice_options(game["name"], all_names, rng)
            questions.append({
                "type": "gamefact",
                "prompt": "Permainan tradisional apa yang sesuai dengan deskripsi ini?",
                "context": game["summary"] + " " + game["how_to_play"],
                "options": [{"value": x, "label": x} for x in options],
                "answer": game["name"],
                "explanation": f'{game["name"]}: {game["region_context"]}. Nilai belajar: {", ".join(game.get("values", []))}.',
                "game_id": game["id"],
                "game_name": game["name"],
            })

    elif mode == "mixed":
        modes = ["label", "blank", "gamefact"]
        per_mode = max(1, count // len(modes))
        combined: list[dict] = []
        for idx, child in enumerate(modes):
            child_count = per_mode if idx < len(modes) - 1 else max(1, count - len(combined))
            combined.extend(build_session(child, child_count, rng.randint(0, 10_000_000))["questions"])
        rng.shuffle(combined)
        questions = combined[:count]
    else:
        raise ValueError(f"Mode game tidak dikenal: {mode}")

    return {
        "mode": mode,
        "count": len(questions),
        "questions": questions,
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
