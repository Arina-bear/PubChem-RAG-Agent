from pydantic import BaseModel, Field

from app.schemas.common import ErrorPayload, PresentationHints, WarningMessage
from app.schemas.query import ManualQuerySpec


class InterpretRequest(BaseModel):
    text: str = Field(min_length=1)


class InterpretationCandidate(BaseModel):
    label: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    query: ManualQuerySpec


class InterpretationPayload(BaseModel):
    candidates: list[InterpretationCandidate] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguities: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    needs_confirmation: bool = True
    recommended_candidate_index: int | None = None


class InterpretResponseEnvelope(BaseModel):
    trace_id: str
    source: str = "interpreter"
    status: str = "success"
    raw: dict | None = None
    normalized: InterpretationPayload | None = None
    presentation_hints: PresentationHints = Field(
        default_factory=lambda: PresentationHints(active_tab="interpretation", available_tabs=["interpretation", "json"])
    )
    warnings: list[WarningMessage] = Field(default_factory=list)
    error: ErrorPayload | None = None

