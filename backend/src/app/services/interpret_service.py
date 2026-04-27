import re
import uuid

from app.errors.models import AppError, ErrorCode
from app.schemas.common import PresentationHints, WarningMessage
from app.schemas.interpret import InterpretationCandidate, InterpretationPayload, InterpretRequest, InterpretResponseEnvelope
from app.schemas.query import QueryRequest

CID_PATTERN = re.compile(r"\bcid[:\s#-]*(\d+)\b", re.IGNORECASE)
SMILES_LABEL_PATTERN = re.compile(r"\bsmiles[:\s]+([A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]+)")
INCHIKEY_PATTERN = re.compile(r"\b[A-Z]{14}-[A-Z]{10}-[A-Z]\b")
FORMULA_PATTERN = re.compile(r"^(?:[A-Z][a-z]?\d*)+$")
UNSUPPORTED_DESCRIPTOR_PATTERN = re.compile(
    r"\b("
    r"benzol|benzene|ring|mass|weight|around|about|approximately|antibiotic|hydrophobic|like|similar|"
    r"бензол\w*|кольц\w*|масс\w*|вес\w*|около|примерно|антибиотик\w*|гидрофоб\w*|похож\w*|схож\w*|свойств\w*"
    r")\b",
    re.IGNORECASE,
)
COMMAND_PREFIX_PATTERN = re.compile(
    r"^\s*(?:please\s+|пожалуйста\s+)?"
    r"(?:(?:find|lookup|search|show|get|identify|resolve|найди|найти|найдите|поищи|ищи|покажи|показать|"
    r"получи|получить)\s+)+"
    r"(?:(?:compound|molecule|chemical|substance|structure|соединение|соединенией|молекулу|молекула|"
    r"вещество|структуру)\s+)?",
    re.IGNORECASE,
)


class InterpretService:
    def execute(self, request: InterpretRequest) -> InterpretResponseEnvelope:
        text = request.text.strip()
        if not text:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Текст для интерпретации не должен быть пустым.",
                http_status = 400,
            )
        
        trace_id = str(uuid.uuid4())
        lowered = text.lower()
        candidates: list[InterpretationCandidate] = []
        assumptions: list[str] = []
        ambiguities: list[str] = []
        warnings: list[str] = []
        raw: dict[str, object] = {"input": text}
#CID
        cid_match = CID_PATTERN.search(text)

        if cid_match:
            cid = cid_match.group(1)
            candidates.append(
                self._candidate(
                    label=f"Найти соединение по CID {cid}",
                    rationale="В тексте найден явный идентификатор CID.",
                    confidence=0.96,
                    query=QueryRequest(input_mode = "cid", identifier = cid, operation = "property"),
                )
            )
            assumptions.append("Явно указанный CID считается самым надёжным идентификатором в запросе.")
#SMILES
        smiles_label_match = SMILES_LABEL_PATTERN.search(text)

        if smiles_label_match:
            smiles = smiles_label_match.group(1)
            candidates.append(
                self._candidate(
                    label="Найти соединение по SMILES",
                    rationale="В тексте найдена строка структуры с явной пометкой SMILES.",
                    confidence=0.93,
                    query = QueryRequest(input_mode="smiles", identifier=smiles, operation="property"),
                )
            )
            assumptions.append("Текст после пометки SMILES интерпретирован как строка структуры.")
#inchikey
        inchikey_match = INCHIKEY_PATTERN.search(text)

        if inchikey_match:
            inchikey = inchikey_match.group(0)
            candidates.append(
                self._candidate(
                    label="Найти соединение по InChIKey",
                    rationale="В тексте найден шаблон InChIKey.",
                    confidence=0.94,
                    query = QueryRequest(input_mode="inchikey", identifier=inchikey, operation="property"),
                )
            )
            assumptions.append("Найденный InChIKey считается основным химическим идентификатором.")

        if not candidates and FORMULA_PATTERN.fullmatch(text) and any(character.isdigit() for character in text):
            candidates.append(
                self._candidate(
                    label="Найти соединение по молекулярной формуле",
                    rationale="Текст похож на краткую запись молекулярной формулы.",
                    confidence=0.76,
                    query = QueryRequest(input_mode="formula", identifier=text, operation="property"),
                )
            )
            assumptions.append("Поиск по формуле может вернуть несколько соединений, поэтому результат стоит проверить вручную.")

        if not candidates and self._looks_like_smiles(text):
            candidates.append(
                self._candidate(
                    label="Найти соединение по SMILES",
                    rationale="Текст очень похож на компактную строку химической структуры.",
                    confidence=0.82,
                    query = QueryRequest(input_mode="smiles", identifier=text, operation="property"),
                )
            )
            assumptions.append("Весь запрос интерпретирован как строка SMILES.")

        if not candidates and not UNSUPPORTED_DESCRIPTOR_PATTERN.search(text):
            query_name = self._extract_name_candidate(text)
            if query_name:
                candidates.append(
                    self._candidate(
                        label=f"Найти соединение по названию: {query_name}",
                        rationale="Запрос похож на прямой поиск по названию соединения.",
                        confidence = 0.74,
                        query = QueryRequest(input_mode="name", identifier = query_name, operation = "property"),
                    )
                )
                assumptions.append("Запрос интерпретирован как название соединения, а не как описание свойств.")

        if not candidates:
            ambiguities.append("Запрос описывает свойства или намерение, которое нельзя надёжно перевести в текущий типизированный контракт.")
            warnings.append("В первой версии поддерживаются точные поиски по названию, CID, SMILES, InChIKey и формуле.")
            confidence = 0.28
            recommended_candidate_index = None

        else:
            confidence = max(candidate.confidence for candidate in candidates)
            recommended_candidate_index = 0
            if confidence < 0.7:
                warnings.append("Уверенность ниже рабочего порога. Перед запуском стоит проверить структурированный запрос.")

        if "pug view" in lowered or "safety" in lowered or "bioactivity" in lowered:
            ambiguities.append("Запрошенный тип данных относится к следующему этапу и пока не включён в текущую версию.")

        return InterpretResponseEnvelope(
            trace_id=trace_id,
            source="interpreter",
            status="success",
            raw=raw,
            normalized=InterpretationPayload(
                candidates=candidates,
                confidence=confidence,
                ambiguities=ambiguities,
                assumptions=assumptions,
                warnings=warnings,
                needs_confirmation=True,
                recommended_candidate_index=recommended_candidate_index,
            ),
            presentation_hints=PresentationHints(
                active_tab="interpretation",
                available_tabs=["interpretation", "json"],
            ),
            warnings=[
                WarningMessage(
                    code="SUPERVISED_EXECUTION",
                    message="Режим Agent только подготавливает кандидаты запросов. Сам запрос всё равно выполняет backend.",
                )
            ],
            error=None,
        )

    def _candidate(self, *, label: str, rationale: str, confidence: float, query: QueryRequest) -> InterpretationCandidate:
        return InterpretationCandidate(
            label=label,
            rationale=rationale,
            confidence=confidence,
            query=query,
        )

    def _looks_like_smiles(self, text: str) -> bool:
        if " " in text or len(text) < 4:
            return False
        if not re.fullmatch(r"[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]+", text):
            return False
        return any(character in text for character in "[]=()#")

    def _extract_name_candidate(self, text: str) -> str | None:
        stripped = text.strip()
        previous = None
        while stripped and stripped != previous:
            previous = stripped
            stripped = COMMAND_PREFIX_PATTERN.sub("", stripped).strip()

        stripped = stripped.strip("\"'«» ")
        stripped = re.sub(r"^[,.;:!?]+|[,.;:!?]+$", "", stripped).strip()
        if not stripped or len(stripped.split()) > 5:
            return None
        return stripped
