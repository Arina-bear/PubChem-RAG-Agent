from app.config import Settings
from app.schemas.query import ManualQuerySpec
from app.services.query_service import QueryService


class FakeAdapter:
    async def resolve_cids(self, input_mode: str, identifier: str, *, limit: int) -> list[int]:
        if input_mode == "cid":
            return [2244]
        if input_mode == "name":
            return [2244, 3672]
        if input_mode == "formula":
            return [2244, 1983]
        if input_mode == "inchikey":
            return [2244]
        return [2244]

    async def fetch_compound_snapshot(self, cid: int) -> dict:
        return {
            "cid": cid,
            "properties": {
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": cid,
                            "Title": "Aspirin" if cid == 2244 else "Example",
                            "IUPACName": "2-acetyloxybenzoic acid",
                            "MolecularFormula": "C9H8O4",
                            "MolecularWeight": 180.16,
                            "ExactMass": 180.0423,
                            "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                            "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                        }
                    ]
                }
            },
            "synonyms": {
                "InformationList": {
                    "Information": [
                        {
                            "CID": cid,
                            "Synonym": ["Aspirin", "Acetylsalicylic acid", "2-Acetoxybenzoic acid"],
                        }
                    ]
                }
            },
            "image_data_url": "data:image/png;base64,ZmFrZQ==",
        }


async def test_query_service_resolves_name_to_primary_result() -> None:
    service = QueryService(Settings(), FakeAdapter())  # type: ignore[arg-type]
    response = await service.execute(ManualQuerySpec(input_mode="name", identifier="aspirin", operation="property"))

    assert response.normalized is not None
    assert response.normalized.primary_result is not None
    assert response.normalized.primary_result.cid == 2244
    assert response.normalized.synonyms[0] == "Aspirin"
    assert len(response.normalized.matches) == 2


async def test_query_service_uses_synonyms_tab_hint_for_synonym_operation() -> None:
    service = QueryService(Settings(), FakeAdapter())  # type: ignore[arg-type]
    response = await service.execute(ManualQuerySpec(input_mode="cid", identifier="2244", operation="synonyms"))

    assert response.presentation_hints.active_tab == "synonyms"


async def test_query_service_accepts_formula_queries_in_typed_backend() -> None:
    service = QueryService(Settings(), FakeAdapter())  # type: ignore[arg-type]
    response = await service.execute(ManualQuerySpec(input_mode="formula", identifier="C9H8O4", operation="property"))

    assert response.normalized is not None
    assert response.normalized.primary_result is not None
    assert response.normalized.primary_result.cid == 2244
