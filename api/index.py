from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.game_engine import (
    adventure_map,
    build_adventure_challenge,
    build_session,
    custom_text_game,
    get_game,
    public_catalog,
)
from app.inference import get_nlp, predict, quiz_questions
from app.schemas import (
    AdventureChallengeRequest,
    CustomGameRequest,
    GameSessionRequest,
    PredictRequest,
    PredictResponse,
    QuizResponse,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = ROOT / "web" / "index.html"
WEB_CLASSIC = ROOT / "web" / "classic.html"
WEB_NER = ROOT / "web" / "ner.html"
MODEL_MANIFEST = ROOT / "models" / "production" / "manifest.json"
WEB_CSS = ROOT / "web" / "adventure2d.css"
WEB_JS = ROOT / "web" / "adventure2d.js"

app = FastAPI(
    title="NusantaraEdu Games 2D",
    version="3.0.0",
    description="Petualangan 2D permainan tradisional Indonesia berbasis NusantaraEdu-NER.",
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


@app.get("/classic", response_class=HTMLResponse, include_in_schema=False)
def classic_home():
    return _html(WEB_CLASSIC if WEB_CLASSIC.exists() else WEB_INDEX)


@app.get("/ner", response_class=HTMLResponse, include_in_schema=False)
def ner_home():
    return _html(WEB_NER if WEB_NER.exists() else WEB_INDEX)




@app.get("/web/adventure2d.css", include_in_schema=False)
def adventure_css():
    if not WEB_CSS.exists():
        raise HTTPException(status_code=404, detail="Stylesheet 2D tidak ditemukan.")
    return FileResponse(WEB_CSS, media_type="text/css")


@app.get("/web/adventure2d.js", include_in_schema=False)
def adventure_js():
    if not WEB_JS.exists():
        raise HTTPException(status_code=404, detail="Script 2D tidak ditemukan.")
    return FileResponse(WEB_JS, media_type="application/javascript")


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
            "adventure_2d": True,
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


@app.get("/api/game/adventure-map")
def game_adventure_map():
    return adventure_map()


@app.post("/api/game/adventure/{game_id}")
def game_adventure(game_id: str, payload: AdventureChallengeRequest):
    try:
        return build_adventure_challenge(game_id, payload.count, payload.seed)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pos permainan tidak ditemukan.") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/game/custom")
def game_custom(payload: CustomGameRequest):
    try:
        return custom_text_game(payload.text)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
