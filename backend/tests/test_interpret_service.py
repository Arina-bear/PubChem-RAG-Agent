from src.app.schemas.interpret import InterpretRequest
from src.app.services.interpret_service import InterpretService


def test_interpret_service_detects_cid() -> None:
    service = InterpretService()
    response = service.execute(InterpretRequest(text="show CID 2244"))

    assert response.normalized is not None
    assert response.normalized.recommended_candidate_index == 0
    assert response.normalized.candidates[0].query.input_mode == "cid"
    assert response.normalized.candidates[0].query.identifier == "2244"


def test_interpret_service_flags_low_confidence_property_description() -> None:
    service = InterpretService()
    response = service.execute(InterpretRequest(text="antibiotic with benzene ring and mass around 350"))

    assert response.normalized is not None
    assert response.normalized.confidence < 0.7
    assert response.normalized.candidates == []
    assert response.normalized.needs_confirmation is True


def test_interpret_service_strips_command_prefix_from_name_query() -> None:
    service = InterpretService()
    response = service.execute(InterpretRequest(text="найди aspirin"))

    assert response.normalized is not None
    assert response.normalized.candidates[0].query.input_mode == "name"
    assert response.normalized.candidates[0].query.identifier == "aspirin"


def test_interpret_service_flags_russian_property_description() -> None:
    service = InterpretService()
    response = service.execute(InterpretRequest(text="антибиотик с бензольным кольцом и массой около 350"))

    assert response.normalized is not None
    assert response.normalized.confidence < 0.7
    assert response.normalized.candidates == []
