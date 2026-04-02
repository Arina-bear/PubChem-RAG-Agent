import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.adapter.pubchem_adapter import PubChemAdapter
from app.errors.models import AppError
from app.normalizers.compound import normalize_compound
from app.schemas.common import CompoundOverview


class SearchCompoundByNameArgs(BaseModel):
    name: str = Field(min_length=1, max_length=160, description="Compound name or search keyword from the user.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class SearchCompoundBySmilesArgs(BaseModel):
    smiles: str = Field(min_length=1, max_length=512, description="SMILES string to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("smiles", mode="before")
    @classmethod
    def strip_smiles(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("smiles must not be blank")
        return cleaned


class SearchCompoundByFormulaArgs(BaseModel):
    formula: str = Field(min_length=1, max_length=64, description="Molecular formula to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("formula", mode="before")
    @classmethod
    def strip_formula(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("formula must not be blank")
        return cleaned


class SearchCompoundByMassRangeArgs(BaseModel):
    min_mass: float = Field(description="Lower bound of the requested mass range.")
    max_mass: float = Field(description="Upper bound of the requested mass range.")
    mass_type: Literal["molecular_weight", "exact_mass", "monoisotopic_mass"] = Field(
        default="molecular_weight",
        description="Mass field to search in PubChem. Supported values: molecular_weight, exact_mass, monoisotopic_mass.",
    )
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @model_validator(mode="after")
    def validate_bounds(self) -> "SearchCompoundByMassRangeArgs":
        if self.min_mass > self.max_mass:
            raise ValueError("min_mass must be less than or equal to max_mass")
        return self


class GetCompoundSummaryArgs(BaseModel):
    cid: int = Field(gt=0, description="PubChem compound identifier (CID).")


class NameToSmilesArgs(BaseModel):
    name: str = Field(min_length=1, max_length=160, description="Compound name that should be converted to canonical SMILES.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class SearchBySynonymArgs(BaseModel):
    synonym: str = Field(min_length=1, max_length=160, description="Synonym or alternative compound name.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("synonym", mode="before")
    @classmethod
    def strip_synonym(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("synonym must not be blank")
        return cleaned


class AskUserForClarificationArgs(BaseModel):
    question: str = Field(min_length=5, max_length=300, description="One concrete clarification question for the user.")
    reason: str | None = Field(default=None, max_length=300, description="Why the current query cannot be executed safely yet.")

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        return cleaned

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


@dataclass(slots=True)
class PubChemToolDefinition:
    name: str
    input_model: type[BaseModel]
    handler: Callable[[BaseModel], Awaitable[dict[str, Any]]]

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": inspect.getdoc(self.handler) or "",
                "parameters": self.input_model.model_json_schema(),
                "strict": True,
            },
        }


class PubChemToolbox:
    def __init__(self, adapter: PubChemAdapter) -> None:
        self.adapter = adapter
        self._definitions = {
            "search_compound_by_name": PubChemToolDefinition(
                name="search_compound_by_name",
                input_model=SearchCompoundByNameArgs,
                handler=self.search_compound_by_name,
            ),
            "search_compound_by_smiles": PubChemToolDefinition(
                name="search_compound_by_smiles",
                input_model=SearchCompoundBySmilesArgs,
                handler=self.search_compound_by_smiles,
            ),
            "search_compound_by_formula": PubChemToolDefinition(
                name="search_compound_by_formula",
                input_model=SearchCompoundByFormulaArgs,
                handler=self.search_compound_by_formula,
            ),
            "search_compound_by_mass_range": PubChemToolDefinition(
                name="search_compound_by_mass_range",
                input_model=SearchCompoundByMassRangeArgs,
                handler=self.search_compound_by_mass_range,
            ),
            "get_compound_summary": PubChemToolDefinition(
                name="get_compound_summary",
                input_model=GetCompoundSummaryArgs,
                handler=self.get_compound_summary,
            ),
            "name_to_smiles": PubChemToolDefinition(
                name="name_to_smiles",
                input_model=NameToSmilesArgs,
                handler=self.name_to_smiles,
            ),
            "search_by_synonym": PubChemToolDefinition(
                name="search_by_synonym",
                input_model=SearchBySynonymArgs,
                handler=self.search_by_synonym,
            ),
            "ask_user_for_clarification": PubChemToolDefinition(
                name="ask_user_for_clarification",
                input_model=AskUserForClarificationArgs,
                handler=self.ask_user_for_clarification,
            ),
        }

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [definition.to_openai_tool() for definition in self._definitions.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        definition = self._definitions.get(name)
        if definition is None:
            return {
                "ok": False,
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Tool '{name}' не зарегистрирован.",
                },
            }

        try:
            validated = definition.input_model.model_validate(arguments)
        except ValidationError as exc:
            return {
                "ok": False,
                "error": {
                    "code": "INVALID_TOOL_ARGUMENTS",
                    "message": "Tool arguments не прошли валидацию.",
                    "details": exc.errors(),
                },
            }

        try:
            return await definition.handler(validated)
        except AppError as error:
            return {
                "ok": False,
                "error": {
                    "code": error.code.value,
                    "message": error.message,
                    "details": error.details or None,
                },
            }

    async def search_compound_by_name(self, payload: SearchCompoundByNameArgs) -> dict[str, Any]:
        """Search PubChem by an explicit compound name or concise keyword. Use this first when the user likely named a substance."""
        return await self._search_by_identifier(input_mode="name", identifier=payload.name, limit=payload.limit, matched_by="name")

    async def search_compound_by_smiles(self, payload: SearchCompoundBySmilesArgs) -> dict[str, Any]:
        """Search PubChem by an exact SMILES string. Use this when a structure string is available or after name_to_smiles resolves one."""
        return await self._search_by_identifier(
            input_mode="smiles",
            identifier=payload.smiles,
            limit=payload.limit,
            matched_by="smiles",
        )

    async def search_compound_by_formula(self, payload: SearchCompoundByFormulaArgs) -> dict[str, Any]:
        """Search PubChem by molecular formula. Use this when the user knows the exact or approximate formula."""
        return await self._search_by_identifier(
            input_mode="formula",
            identifier=payload.formula,
            limit=payload.limit,
            matched_by="formula",
        )

    async def search_compound_by_mass_range(self, payload: SearchCompoundByMassRangeArgs) -> dict[str, Any]:
        """Search PubChem by a bounded mass range. Use this when the user gives an approximate mass instead of an exact identifier."""
        cids = await self.adapter.resolve_cids_by_mass_range(
            min_mass=payload.min_mass,
            max_mass=payload.max_mass,
            mass_type=payload.mass_type,
            limit=payload.limit,
        )
        compounds = await self._fetch_overviews(cids)
        return {
            "ok": True,
            "query": {
                "input_mode": "mass_range",
                "mass_type": payload.mass_type,
                "min_mass": payload.min_mass,
                "max_mass": payload.max_mass,
            },
            "count": len(compounds),
            "matches": [compound.model_dump(mode="json") for compound in compounds],
        }

    async def get_compound_summary(self, payload: GetCompoundSummaryArgs) -> dict[str, Any]:
        """Fetch a compact normalized summary for a specific PubChem CID, including names, formula, masses, SMILES and synonym preview."""
        overview = await self._fetch_overview(payload.cid, include_synonyms=True)
        return {
            "ok": True,
            "cid": payload.cid,
            "compound": overview.model_dump(mode="json"),
        }

    async def name_to_smiles(self, payload: NameToSmilesArgs) -> dict[str, Any]:
        """Resolve a compound name to canonical SMILES through PubChem. Use this when the user names a compound but downstream logic benefits from structure search."""
        cids = await self.adapter.resolve_cids("name", payload.name, limit=1)
        if not cids:
            return {
                "ok": False,
                "error": {
                    "code": "NO_MATCH",
                    "message": f"PubChem не нашёл SMILES для названия '{payload.name}'.",
                },
            }

        overview = await self._fetch_overview(cids[0], include_synonyms=False)
        return {
            "ok": True,
            "input_name": payload.name,
            "cid": overview.cid,
            "resolved_title": overview.title,
            "canonical_smiles": overview.canonical_smiles,
            "molecular_formula": overview.molecular_formula,
        }

    async def search_by_synonym(self, payload: SearchBySynonymArgs) -> dict[str, Any]:
        """Search PubChem by a synonym or alternative compound name. Use this when the user provides a common name, trade name, abbreviation or alias."""
        return await self._search_by_identifier(
            input_mode="name",
            identifier=payload.synonym,
            limit=payload.limit,
            matched_by="synonym",
        )

    async def ask_user_for_clarification(self, payload: AskUserForClarificationArgs) -> dict[str, Any]:
        """Ask the user one clarification question instead of guessing. Use this when the query is too ambiguous for a safe PubChem lookup."""
        return {
            "ok": True,
            "needs_clarification": True,
            "question": payload.question,
            "reason": payload.reason,
        }

    async def _search_by_identifier(self, *, input_mode: str, identifier: str, limit: int, matched_by: str) -> dict[str, Any]:
        cids = await self.adapter.resolve_cids(input_mode, identifier, limit=limit)
        compounds = await self._fetch_overviews(cids)
        return {
            "ok": True,
            "query": {
                "input_mode": input_mode,
                "identifier": identifier,
                "matched_by": matched_by,
            },
            "count": len(compounds),
            "matches": [compound.model_dump(mode="json") for compound in compounds],
        }

    async def _fetch_overviews(self, cids: list[int]) -> list[CompoundOverview]:
        return await asyncio.gather(*(self._fetch_overview(cid, include_synonyms=False) for cid in cids))

    async def _fetch_overview(self, cid: int, *, include_synonyms: bool) -> CompoundOverview:
        snapshot = await self.adapter.fetch_compound_snapshot(
            cid,
            include_synonyms=include_synonyms,
            include_image=False,
        )
        return normalize_compound(
            cid=snapshot["cid"],
            properties_payload=snapshot["properties"],
            synonyms_payload=snapshot["synonyms"],
            image_data_url=None,
        )
