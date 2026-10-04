from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    text: str = Field(min_length=2, max_length=5000)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Teks terlalu pendek.")
        return value


class EntityOut(BaseModel):
    text: str
    label: str
    start: int
    end: int


class PredictResponse(BaseModel):
    text: str
    entities: list[EntityOut]
    model_loaded: bool


class QuizQuestion(BaseModel):
    prompt: str
    answer: str
    label: str


class QuizResponse(BaseModel):
    text: str
    questions: list[QuizQuestion]


class GameSessionRequest(BaseModel):
    mode: Literal["label", "blank", "gamefact", "mixed"] = "mixed"
    count: int = Field(default=5, ge=1, le=12)
    seed: int | None = None


class AdventureChallengeRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=5)
    seed: int | None = None


class CustomGameRequest(PredictRequest):
    pass
