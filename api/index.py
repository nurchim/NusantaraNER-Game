from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.game_engine import build_session, custom_text_game, get_game, public_catalog
from app.inference import get_nlp, predict, quiz_questions
from app.schemas import CustomGameRequest, GameSessionRequest, PredictRequest, PredictResponse, QuizResponse

ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = ROOT / "web" / "index.html"
WEB_NER = ROOT / "web" / "ner.html"
MODEL_MANIFEST = ROOT / "models" / "production" / "manifest.json"

app = FastAPI(
    title="NusantaraEdu Games",
    version="2.0.0",
    description="Game edukasi permainan tradisional Indonesia berbasis model NusantaraEdu-NER.",
    docs_url="/api/docs",
    redoc_url=None,
)


def _html(path: Path) -> HTMLResponse:
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Interface tidak ditemukan: {path.name}")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return _html(WEB_INDEX)


@app.get("/game", response_class=HTMLResponse, include_in_schema=False)
def game_home():
    return _html(WEB_INDEX)


@app.get("/ner", response_class=HTMLResponse, include_in_schema=False)
def ner_home():
    return _html(WEB_NER if WEB_NER.exists() else WEB_INDEX)


@app.get("/api/health")
def health():
    try:
        nlp = get_nlp()
        labels = sorted(nlp.get_pipe("ner").labels) if "ner" in nlp.pipe_names else []
        return {
            "status": "ok",
            "model": nlp.meta.get("name", "nusantara_ner"),
            "pipeline": list(nlp.pipe_names),
            "label_count": len(labels),
            "game_catalog": len(public_catalog()),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/model-info")
def model_info():
    if not MODEL_MANIFEST.exists():
        return {"status": "missing", "model_path": "models/production/model-best"}
    return {"status": "ok", **json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))}


@app.post("/api/predict", response_model=PredictResponse)
def api_predict(payload: PredictRequest):
    try:
        return {"text": payload.text, "entities": predict(payload.text), "model_loaded": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/quiz", response_model=QuizResponse)
def api_quiz(payload: PredictRequest):
    try:
        return {"text": payload.text, "questions": quiz_questions(payload.text)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/game/catalog")
def game_catalog():
    return {"items": public_catalog(), "count": len(public_catalog())}


@app.get("/api/game/catalog/{game_id}")
def game_detail(game_id: str):
    try:
        return get_game(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Permainan tidak ditemukan.") from exc


@app.post("/api/game/session")
def game_session(payload: GameSessionRequest):
    try:
        return build_session(payload.mode, payload.count, payload.seed)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/game/custom")
def game_custom(payload: CustomGameRequest):
    try:
        return custom_text_game(payload.text)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
