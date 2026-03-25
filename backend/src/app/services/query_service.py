import asyncio
import uuid

from app.adapter.pubchem_adapter import PubChemAdapter
from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.normalizers.compound import extract_synonyms, normalize_compound, to_match_card
from app.schemas.common import PresentationHints, WarningMessage
from app.schemas.query import ManualQuerySpec, QueryNormalizedPayload, QueryResponseEnvelope, ResolvedQuery


SUPPORTED_INPUT_MODES = {"cid", "name", "smiles", "inchikey", "formula"}
SUPPORTED_OPERATIONS = {"property", "record", "synonyms"}


class QueryService:
    def __init__(self, settings: Settings, adapter: PubChemAdapter) -> None:
        self.settings = settings
        self.adapter = adapter

    async def execute(self, spec: ManualQuerySpec) -> QueryResponseEnvelope:
        self._validate_capabilities(spec)
        limit = spec.pagination.limit if spec.pagination else self.settings.candidate_limit

        resolved_cids = await self.adapter.resolve_cids(spec.input_mode, spec.identifier, limit=limit)
        snapshots = await asyncio.gather(*(self.adapter.fetch_compound_snapshot(cid) for cid in resolved_cids[:limit]))

        normalized_compounds = [
            normalize_compound(
                cid=snapshot["cid"],
                properties_payload=snapshot["properties"],
                synonyms_payload=snapshot["synonyms"],
                image_data_url=snapshot["image_data_url"],
            )
            for snapshot in snapshots
        ]
        if not normalized_compounds:
            raise AppError(
                ErrorCode.NO_MATCH,
                "PubChem не вернул подходящих соединений.",
                http_status=404,
            )

        primary = normalized_compounds[0]
        synonyms = extract_synonyms(snapshots[0]["synonyms"])
        warnings = self._build_warnings(spec)

        return QueryResponseEnvelope(
            trace_id=str(uuid.uuid4()),
            source="pubchem-pug-rest",
            status="success",
            raw={
                "resolved_cids": resolved_cids,
                "items": snapshots,
            }
            if spec.include_raw
            else None,
            normalized=QueryNormalizedPayload(
                query=ResolvedQuery(
                    domain=spec.domain,
                    input_mode=spec.input_mode,
                    identifier=spec.identifier,
                    operation=spec.operation,
                ),
                matches=[to_match_card(item) for item in normalized_compounds],
                primary_result=primary,
                synonyms=synonyms,
            ),
            presentation_hints=PresentationHints(
                active_tab="synonyms" if spec.operation == "synonyms" else "overview",
                available_tabs=["overview", "synonyms", "json"],
            ),
            warnings=warnings,
            error=None,
        )

    def _validate_capabilities(self, spec: ManualQuerySpec) -> None:
        if spec.domain != "compound":
            raise AppError(
                ErrorCode.UNSUPPORTED_QUERY,
                "В текущей версии поддерживается только домен compound.",
                http_status=400,
            )
        if spec.input_mode not in SUPPORTED_INPUT_MODES:
            raise AppError(
                ErrorCode.UNSUPPORTED_QUERY,
                f"Режим ввода '{spec.input_mode}' пока не поддерживается.",
                http_status=400,
            )
        if spec.operation not in SUPPORTED_OPERATIONS:
            raise AppError(
                ErrorCode.UNSUPPORTED_QUERY,
                f"Операция '{spec.operation}' пока не поддерживается.",
                http_status=400,
            )

    def _build_warnings(self, spec: ManualQuerySpec) -> list[WarningMessage]:
        warnings: list[WarningMessage] = []
        if spec.operation == "record":
            warnings.append(
                WarningMessage(
                    code="RECORD_NORMALIZED",
                    message="Операция record сейчас сводится к тому же обзору, что и property.",
                )
            )
        if spec.input_mode in {"name", "smiles"}:
            warnings.append(
                WarningMessage(
                    code="PRIMARY_IS_FIRST_MATCH",
                    message="Основным результатом выбран первый найденный кандидат PubChem.",
                )
            )
        return warnings
