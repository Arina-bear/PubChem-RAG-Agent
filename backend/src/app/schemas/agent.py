from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import CompoundOverview, ErrorPayload, PresentationHints, WarningMessage


LLMProviderName = Literal["openai", "modal_glm"]
AgentSearchMode = Literal["name", "smiles", "formula", "mass_range", "clarify"]


class AgentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    provider: LLMProviderName | None = None
    model: str | None = None
    max_steps: int = Field(default=6, ge=1, le=12)
    max_output_tokens: int = Field(default=800, ge=64, le=4096)
    include_raw: bool = False

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must not be blank")
        return cleaned


class AgentToolCallTrace(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "error"] = "success"
    result: dict[str, Any] | list[Any] | str | None = None
    error_message: str | None = None


class AgentParsedQuery(BaseModel):
    compound_name: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    smiles: str | None = None
    formula: str | None = None
    mass_range: tuple[float, float] | None = None
    mass_type: Literal["molecular_weight", "exact_mass", "monoisotopic_mass"] | None = None
    language: Literal["ru", "en", "unknown"] = "unknown"
    normalized_language: Literal["en"] = "en"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ambiguities: list[str] = Field(default_factory=list)
    recommended_search_mode: AgentSearchMode = "clarify"


class AgentNormalizedPayload(BaseModel):
    user_text: str
    answer: str
    provider: LLMProviderName
    model: str
    parsed_query: AgentParsedQuery
    needs_clarification: bool = False
    clarification_question: str | None = None
    compounds: list[CompoundOverview] = Field(default_factory=list)
    tool_calls: list[AgentToolCallTrace] = Field(default_factory=list)


class AgentResponseEnvelope(BaseModel):
    trace_id: str
    source: Literal["llm-agent"] = "llm-agent"
    status: Literal["success", "needs_clarification", "error"] = "success"
    raw: dict[str, Any] | None = None
    normalized: AgentNormalizedPayload | None = None
    presentation_hints: PresentationHints = Field(
        default_factory=lambda: PresentationHints(active_tab="overview", available_tabs=["overview", "tools", "json"])
    )
    warnings: list[WarningMessage] = Field(default_factory=list)
    error: ErrorPayload | None = None
