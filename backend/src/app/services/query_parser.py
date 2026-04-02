import re

from app.schemas.agent import AgentParsedQuery


SMILES_LABEL_PATTERN = re.compile(r"\bsmiles[:\s]+([A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]+)", re.IGNORECASE)
SMILES_FREEFORM_PATTERN = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]{4,}$")
FORMULA_LABEL_PATTERN = re.compile(r"\b(?:formula|формула)[:\s]+([A-Za-z0-9]+)\b", re.IGNORECASE)
FORMULA_FREEFORM_PATTERN = re.compile(r"^(?:[A-Z][a-z]?\d*)+$")
MASS_RANGE_PATTERN = re.compile(
    r"(?:(?:mass|weight|mw|масс\w*|молекулярн\w*\s+масс\w*)\D*)?"
    r"(?P<min>\d+(?:\.\d+)?)\s*(?:-|to|до)\s*(?P<max>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
MASS_AROUND_PATTERN = re.compile(
    r"(?:mass|weight|mw|масс\w*|молекулярн\w*\s+масс\w*)\D*"
    r"(?:around|about|approximately|approx|около|примерно)\s*(?P<value>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
CID_PATTERN = re.compile(r"\bcid[:\s#-]*(\d+)\b", re.IGNORECASE)
NAME_PREFIX_PATTERN = re.compile(
    r"^\s*(?:please\s+|пожалуйста\s+)?"
    r"(?:(?:find|lookup|search|show|get|identify|resolve|найди|найти|найдите|поищи|ищи|покажи|показать|"
    r"получи|получить)\s+)+"
    r"(?:(?:compound|molecule|chemical|substance|structure|соединение|молекулу|молекула|"
    r"вещество|структуру)\s+)?",
    re.IGNORECASE,
)
DESCRIPTOR_TERMS = {
    "antibiotic",
    "analgesic",
    "antiviral",
    "anti-inflammatory",
    "антибиотик",
    "обезболивающее",
    "противовирусное",
    "противовоспалительное",
}


class QueryParserService:
    def parse(self, text: str) -> AgentParsedQuery:
        cleaned = text.strip()
        language = self._detect_language(cleaned)

        smiles = self._extract_smiles(cleaned)
        formula = self._extract_formula(cleaned)
        mass_range = self._extract_mass_range(cleaned)
        compound_name = self._extract_name(cleaned) if not any([smiles, formula, mass_range]) else None
        synonyms = self._extract_descriptors(cleaned)
        ambiguities: list[str] = []

        recommended_search_mode = "clarify"
        confidence = 0.25
        mass_type = "molecular_weight" if mass_range else None

        if CID_PATTERN.search(cleaned):
            ambiguities.append("В запросе указан CID. Для agent-mode его лучше отправлять в typed /api/query либо явно просить summary.")

        if smiles:
            recommended_search_mode = "smiles"
            confidence = 0.95
        elif formula:
            recommended_search_mode = "formula"
            confidence = 0.84
        elif compound_name:
            recommended_search_mode = "name"
            confidence = 0.76
        elif mass_range:
            recommended_search_mode = "mass_range"
            confidence = 0.6 if not synonyms else 0.48
        else:
            ambiguities.append("Не найден точный идентификатор: название, SMILES, формула или диапазон массы.")

        if synonyms and recommended_search_mode == "clarify":
            ambiguities.append("Обнаружены только смысловые дескрипторы. Для PubChem этого недостаточно без дополнительного признака.")

        return AgentParsedQuery(
            compound_name=compound_name,
            synonyms=synonyms,
            smiles=smiles,
            formula=formula,
            mass_range=mass_range,
            mass_type=mass_type,
            language=language,
            normalized_language="en",
            confidence=confidence,
            ambiguities=ambiguities,
            recommended_search_mode=recommended_search_mode,
        )

    def build_clarification_question(self, parsed_query: AgentParsedQuery) -> str:
        if parsed_query.synonyms and parsed_query.mass_range:
            return "Уточните точное название, формулу или SMILES. По описанию свойств и примерной массе PubChem вернёт слишком много кандидатов."
        if parsed_query.synonyms:
            return "Уточните, по какому точному признаку искать соединение: название, SMILES, формула или диапазон массы?"
        return "Уточните запрос: укажите название вещества, SMILES, формулу или примерный диапазон массы."

    def _detect_language(self, text: str) -> str:
        if re.search(r"[А-Яа-яЁё]", text):
            return "ru"
        if re.search(r"[A-Za-z]", text):
            return "en"
        return "unknown"

    def _extract_smiles(self, text: str) -> str | None:
        labeled = SMILES_LABEL_PATTERN.search(text)
        if labeled:
            return labeled.group(1).strip()
        if " " in text:
            return None
        if not SMILES_FREEFORM_PATTERN.fullmatch(text):
            return None
        if any(character in text for character in "[]=()#"):
            return text
        return None

    def _extract_formula(self, text: str) -> str | None:
        labeled = FORMULA_LABEL_PATTERN.search(text)
        if labeled:
            return labeled.group(1).strip()
        if FORMULA_FREEFORM_PATTERN.fullmatch(text) and any(character.isdigit() for character in text):
            return text
        return None

    def _extract_mass_range(self, text: str) -> tuple[float, float] | None:
        explicit_range = MASS_RANGE_PATTERN.search(text)
        if explicit_range:
            left = float(explicit_range.group("min"))
            right = float(explicit_range.group("max"))
            return (min(left, right), max(left, right))

        around_match = MASS_AROUND_PATTERN.search(text)
        if around_match:
            center = float(around_match.group("value"))
            return (max(center - 20.0, 0.0), center + 20.0)

        return None

    def _extract_name(self, text: str) -> str | None:
        stripped = text.strip()
        previous = None
        while stripped and stripped != previous:
            previous = stripped
            stripped = NAME_PREFIX_PATTERN.sub("", stripped).strip()

        stripped = stripped.strip("\"'«» ")
        stripped = re.sub(r"^[,.;:!?]+|[,.;:!?]+$", "", stripped).strip()
        if not stripped or len(stripped) > 120 or len(stripped.split()) > 6:
            return None
        lowered = stripped.lower()
        if any(term in lowered for term in DESCRIPTOR_TERMS):
            return None
        if MASS_RANGE_PATTERN.search(stripped) or MASS_AROUND_PATTERN.search(stripped):
            return None
        return stripped

    def _extract_descriptors(self, text: str) -> list[str]:
        lowered = text.lower()
        return [term for term in sorted(DESCRIPTOR_TERMS) if term in lowered]
