from __future__ import annotations

import os
import sys
import warnings
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "production" / "model-best"

QUIZ_TEMPLATES = {
    "SUKU": "Suku apa yang disebutkan dalam teks?",
    "PROVINSI": "Provinsi apa yang disebutkan dalam teks?",
    "DAERAH": "Daerah apa yang disebutkan dalam teks?",
    "TARIAN": "Tarian apa yang disebutkan dalam teks?",
    "RUMAH_ADAT": "Rumah adat apa yang disebutkan dalam teks?",
    "PAKAIAN_ADAT": "Pakaian adat apa yang disebutkan dalam teks?",
    "MAKANAN": "Makanan tradisional apa yang disebutkan dalam teks?",
    "ALAT_MUSIK": "Alat musik tradisional apa yang disebutkan dalam teks?",
    "BAHASA": "Bahasa apa yang disebutkan dalam teks?",
    "UPACARA": "Upacara atau tradisi apa yang disebutkan dalam teks?",
    "TOKOH": "Tokoh siapa yang disebutkan dalam teks?",
    "CAGAR_BUDAYA": "Cagar budaya apa yang disebutkan dalam teks?",
    "KARYA_BUDAYA": "Karya budaya apa yang disebutkan dalam teks?",
    "PERMAINAN_ADAT": "Permainan tradisional apa yang disebutkan dalam teks?",
    "ORGANISASI_BUDAYA": "Organisasi budaya apa yang disebutkan dalam teks?",
}


def _prepare_spacy_runtime() -> bool:
    """Handle only the known optional h5py/NumPy ABI conflict.

    spaCy/Thinc does not need h5py for this NER pipeline. In some mixed local
    Jupyter environments h5py can fail with ``numpy.dtype size changed``.
    For that specific case, h5py is treated as unavailable. Other errors are
    not hidden.
    """
    warnings.filterwarnings(
        "ignore",
        message=r".*pynvml package is deprecated.*",
        category=FutureWarning,
    )
    try:
        import h5py  # noqa: F401
        return False
    except ImportError:
        return False
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        known_abi_error = (
            "numpy.dtype size changed" in message
            or "binary incompatibility" in message.lower()
        )
        if not known_abi_error:
            raise
        for name in list(sys.modules):
            if name == "h5py" or name.startswith("h5py."):
                sys.modules.pop(name, None)
        sys.modules["h5py"] = None
        return True


@lru_cache(maxsize=1)
def get_nlp():
    _prepare_spacy_runtime()
    import spacy

    model_path = Path(os.getenv("NER_MODEL_PATH", str(DEFAULT_MODEL)))
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model NER tidak ditemukan di {model_path}. "
            "Pastikan models/production/model-best ikut dalam deployment."
        )
    return spacy.load(model_path)


def predict(text: str) -> list[dict]:
    doc = get_nlp()(text)
    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start": int(ent.start_char),
            "end": int(ent.end_char),
        }
        for ent in doc.ents
    ]


def quiz_questions(text: str) -> list[dict]:
    questions: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for ent in predict(text):
        key = (ent["label"], ent["text"].casefold())
        if key in seen:
            continue
        seen.add(key)
        questions.append(
            {
                "prompt": QUIZ_TEMPLATES.get(
                    ent["label"],
                    f"Apa entitas kategori {ent['label']} yang disebutkan dalam teks?",
                ),
                "answer": ent["text"],
                "label": ent["label"],
            }
        )
    return questions[:8]
