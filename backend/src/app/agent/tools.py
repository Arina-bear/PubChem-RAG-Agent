import asyncio
from typing import Any, Literal

from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from app.adapter.pubchem_adapter import PubChemAdapter
from app.agent.tracing import ToolTraceRecorder
from app.errors.models import AppError, ErrorCode
from app.normalizers.compound import extract_description_text, extract_synonyms, normalize_compound, to_match_card


def _error_payload(error: AppError) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": error.code.value,
            "message": error.message,
            "retriable": error.retriable,
            "details": error.details or None,
        },
    }


def _unexpected_error_payload(error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": ErrorCode.UPSTREAM_UNAVAILABLE.value,
            "message": f"Непредвиденная ошибка tool execution: {error}",
            "retriable": False,
            "details": None,
        },
    }


async def _fetch_overview(
    adapter: PubChemAdapter,
    *,
    cid: int,
    include_synonyms: bool,
) -> tuple[dict[str, Any], Any]:
    snapshot = await adapter.fetch_compound_snapshot(
        cid,
        include_synonyms=include_synonyms,
        include_image=False,
    )
    overview = normalize_compound(
        cid=snapshot["cid"],
        properties_payload=snapshot["properties"],
        synonyms_payload=snapshot["synonyms"],
        image_data_url=None,
    )
    return snapshot, overview


async def _search_matches(
    adapter: PubChemAdapter,
    *,
    input_mode: Literal["name", "smiles", "formula", "inchikey"],
    identifier: str,
    limit: int,
) -> dict[str, Any]:
    cids = await adapter.resolve_cids(input_mode, identifier, limit=limit)
    snapshots_and_overviews = await asyncio.gather(
        *[
            _fetch_overview(adapter, cid=cid, include_synonyms=False)
            for cid in cids[:limit]
        ]
    )
    matches = [to_match_card(overview).model_dump(mode="json") for _, overview in snapshots_and_overviews]
    return {
        "ok": True,
        "query": {
            "input_mode": input_mode,
            "identifier": identifier,
            "limit": limit,
        },
        "count": len(matches),
        "match_cids": [item["cid"] for item in matches],
        "matches": matches,
    }


class SearchByNameArgs(BaseModel):
    name: str = Field(min_length=1, max_length=160, description="Compound name or search keyword.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class SearchBySmilesArgs(BaseModel):
    smiles: str = Field(min_length=1, max_length=512, description="SMILES string to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("smiles")
    @classmethod
    def strip_smiles(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("smiles must not be blank")
        return cleaned


class SearchByFormulaArgs(BaseModel):
    formula: str = Field(min_length=1, max_length=64, description="Molecular formula to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("formula")
    @classmethod
    def strip_formula(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("formula must not be blank")
        return cleaned


class SearchByInChIKeyArgs(BaseModel):
    inchikey: str = Field(min_length=1, max_length=64, description="InChIKey string to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("inchikey")
    @classmethod
    def strip_inchikey(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("inchikey must not be blank")
        return cleaned


class SearchByMassRangeArgs(BaseModel):
    min_mass: float = Field(description="Lower bound of the mass range.")
    max_mass: float = Field(description="Upper bound of the mass range.")
    mass_type: Literal["molecular_weight", "exact_mass", "monoisotopic_mass"] = Field(
        default="molecular_weight",
        description="Which PubChem mass field to search by.",
    )
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")


class CompoundSummaryArgs(BaseModel):
    cid: int = Field(gt=0, description="PubChem compound CID.")


class NameToSmilesArgs(BaseModel):
    name: str = Field(min_length=1, max_length=160, description="Compound name to resolve to canonical SMILES.")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class SearchBySynonymArgs(BaseModel):
    synonym: str = Field(min_length=1, max_length=160, description="Alternative name or synonym for the compound.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("synonym")
    @classmethod
    def strip_synonym(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("synonym must not be blank")
        return cleaned


class ClarificationArgs(BaseModel):
    question: str = Field(min_length=1, description="Clarifying question to ask the user.")
    reason: str | None = Field(default=None, description="Short reason why clarification is needed.")


def build_pubchem_tools(
    adapter: PubChemAdapter,
    recorder: ToolTraceRecorder,
) -> list[Any]:
    @tool("search_compound_by_name", args_schema=SearchByNameArgs)
    async def search_compound_by_name(name: str, limit: int = 5) -> dict[str, Any]:
        """Search PubChem compounds by explicit compound name or keyword."""
        arguments = {"name": name, "limit": limit}
        try:
            result = await _search_matches(adapter, input_mode="name", identifier=name, limit=limit)
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="search_compound_by_name", arguments=arguments, result=result)
        return result

    @tool("search_compound_by_smiles", args_schema=SearchBySmilesArgs)
    async def search_compound_by_smiles(smiles: str, limit: int = 5) -> dict[str, Any]:
        """Search PubChem compounds by an exact SMILES string."""
        arguments = {"smiles": smiles, "limit": limit}
        try:
            result = await _search_matches(adapter, input_mode="smiles", identifier=smiles, limit=limit)
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="search_compound_by_smiles", arguments=arguments, result=result)
        return result

    @tool("search_compound_by_formula", args_schema=SearchByFormulaArgs)
    async def search_compound_by_formula(formula: str, limit: int = 5) -> dict[str, Any]:
        """Search PubChem compounds by exact molecular formula."""
        arguments = {"formula": formula, "limit": limit}
        try:
            result = await _search_matches(adapter, input_mode="formula", identifier=formula, limit=limit)
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="search_compound_by_formula", arguments=arguments, result=result)
        return result

    @tool("search_compound_by_inchikey", args_schema=SearchByInChIKeyArgs)
    async def search_compound_by_inchikey(inchikey: str, limit: int = 5) -> dict[str, Any]:
        """Search PubChem compounds by exact InChIKey."""
        arguments = {"inchikey": inchikey, "limit": limit}
        try:
            result = await _search_matches(adapter, input_mode="inchikey", identifier=inchikey, limit=limit)
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="search_compound_by_inchikey", arguments=arguments, result=result)
        return result

    @tool("search_compound_by_mass_range", args_schema=SearchByMassRangeArgs)
    async def search_compound_by_mass_range(
        min_mass: float,
        max_mass: float,
        mass_type: Literal["molecular_weight", "exact_mass", "monoisotopic_mass"] = "molecular_weight",
        limit: int = 5,
    ) -> dict[str, Any]:
        """Search PubChem compounds by a bounded mass range."""
        arguments = {
            "min_mass": min_mass,
            "max_mass": max_mass,
            "mass_type": mass_type,
            "limit": limit,
        }
        try:
            cids = await adapter.resolve_cids_by_mass_range(
                min_mass=min_mass,
                max_mass=max_mass,
                mass_type=mass_type,
                limit=limit,
            )
            snapshots_and_overviews = await asyncio.gather(
                *[
                    _fetch_overview(adapter, cid=cid, include_synonyms=False)
                    for cid in cids[:limit]
                ]
            )
            matches = [to_match_card(overview).model_dump(mode="json") for _, overview in snapshots_and_overviews]
            result = {
                "ok": True,
                "query": {
                    "input_mode": "mass_range",
                    "min_mass": min_mass,
                    "max_mass": max_mass,
                    "mass_type": mass_type,
                    "limit": limit,
                },
                "count": len(matches),
                "match_cids": [item["cid"] for item in matches],
                "matches": matches,
            }
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="search_compound_by_mass_range", arguments=arguments, result=result)
        return result

    @tool("get_compound_summary", args_schema=CompoundSummaryArgs)
    async def get_compound_summary(cid: int) -> dict[str, Any]:
        """Fetch a compact PubChem summary for a single CID."""
        arguments = {"cid": cid}
        try:
            snapshot, overview = await _fetch_overview(adapter, cid=cid, include_synonyms=True)
            description_payload = await adapter.fetch_description(cid)
            compound_payload = overview.model_dump(mode="json")
            compound_payload["description"] = extract_description_text(description_payload)
            result = {
                "ok": True,
                "cid": cid,
                "compound": compound_payload,
                "synonyms": extract_synonyms(snapshot["synonyms"])[:20],
                "description": extract_description_text(description_payload),
            }
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="get_compound_summary", arguments=arguments, result=result)
        return result

    @tool("name_to_smiles", args_schema=NameToSmilesArgs)
    async def name_to_smiles(name: str) -> dict[str, Any]:
        """Resolve a compound name to its canonical SMILES representation."""
        arguments = {"name": name}
        try:
            cids = await adapter.resolve_cids("name", name, limit=1)
            _, overview = await _fetch_overview(adapter, cid=cids[0], include_synonyms=False)
            result = {
                "ok": True,
                "input_name": name,
                "cid": overview.cid,
                "resolved_title": overview.title,
                "canonical_smiles": overview.canonical_smiles,
                "molecular_formula": overview.molecular_formula,
                "molecular_weight": overview.molecular_weight,
            }
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="name_to_smiles", arguments=arguments, result=result)
        return result

    @tool("search_by_synonym", args_schema=SearchBySynonymArgs)
    async def search_by_synonym(synonym: str, limit: int = 5) -> dict[str, Any]:
        """Search PubChem compounds by synonym or alternative name."""
        arguments = {"synonym": synonym, "limit": limit}
        try:
            result = await _search_matches(adapter, input_mode="name", identifier=synonym, limit=limit)
            result["query"]["input_mode"] = "synonym"
        except AppError as error:
            result = _error_payload(error)
        except Exception as error:  # pragma: no cover - defensive
            result = _unexpected_error_payload(error)
        recorder.record(tool_name="search_by_synonym", arguments=arguments, result=result)
        return result

    @tool("ask_user_for_clarification", args_schema=ClarificationArgs)
    async def ask_user_for_clarification(question: str, reason: str | None = None) -> dict[str, Any]:
        """Ask the user a short clarification question when the request is too ambiguous for a safe lookup."""
        result = {
            "ok": True,
            "needs_clarification": True,
            "question": question,
            "reason": reason,
        }
        recorder.record(
            tool_name="ask_user_for_clarification",
            arguments={"question": question, "reason": reason},
            result=result,
        )
        return result

    return [
        search_compound_by_name,
        search_compound_by_smiles,
        search_compound_by_formula,
        search_compound_by_inchikey,
        search_compound_by_mass_range,
        get_compound_summary,
        name_to_smiles,
        search_by_synonym,
        ask_user_for_clarification,
    ]
