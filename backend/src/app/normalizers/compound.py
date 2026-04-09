from typing import Any

from app.schemas.common import CompoundMatchCard, CompoundOverview

PROPERTY_KEYS = [
    "Title",
    "IUPACName",
    "MolecularFormula",
    "MolecularWeight",
    "ExactMass",
    "XLogP",
    "TPSA",
    "Complexity",
    "HBondDonorCount",
    "HBondAcceptorCount",
    "CanonicalSMILES",
    "ConnectivitySMILES",
    "SMILES",
    "InChIKey",
]


def extract_property_record(properties_payload: dict[str, Any]) -> dict[str, Any]:
    properties = properties_payload.get("PropertyTable", {}).get("Properties", [])
    return properties[0] if properties else {}


def extract_synonyms(synonyms_payload: dict[str, Any]) -> list[str]:
    information = synonyms_payload.get("InformationList", {}).get("Information", [])
    if not information:
        return []
    synonyms = information[0].get("Synonym", [])
    return [value for value in synonyms if isinstance(value, str)]


def extract_description_text(description_payload: dict[str, Any] | None) -> str | None:
    if not description_payload:
        return None
    information = description_payload.get("InformationList", {}).get("Information", [])
    if not information:
        return None
    description = information[0].get("Description") or information[0].get("Title")
    if not isinstance(description, str):
        return None
    cleaned = " ".join(description.split())
    return cleaned or None


def normalize_compound(
    *,
    cid: int,
    properties_payload: dict[str, Any],
    synonyms_payload: dict[str, Any] | None,
    image_data_url: str | None,
) -> CompoundOverview:
    record = extract_property_record(properties_payload)
    synonyms = extract_synonyms(synonyms_payload or {})

    return CompoundOverview(
        cid=cid,
        title=record.get("Title"),
        iupac_name=record.get("IUPACName"),
        molecular_formula=record.get("MolecularFormula"),
        molecular_weight=_to_float(record.get("MolecularWeight")),
        exact_mass=_to_float(record.get("ExactMass")),
        xlogp=_to_float(record.get("XLogP")),
        tpsa=_to_float(record.get("TPSA")),
        complexity=_to_float(record.get("Complexity")),
        hbond_donor_count=_to_int(record.get("HBondDonorCount")),
        hbond_acceptor_count=_to_int(record.get("HBondAcceptorCount")),
        canonical_smiles=record.get("CanonicalSMILES") or record.get("ConnectivitySMILES") or record.get("SMILES"),
        inchi_key=record.get("InChIKey"),
        image_data_url=image_data_url,
        synonyms_preview=synonyms[:12],
    )


def to_match_card(overview: CompoundOverview) -> CompoundMatchCard:
    return CompoundMatchCard(
        cid=overview.cid,
        title=overview.title,
        molecular_formula=overview.molecular_formula,
        molecular_weight=overview.molecular_weight,
        image_data_url=overview.image_data_url,
    )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
