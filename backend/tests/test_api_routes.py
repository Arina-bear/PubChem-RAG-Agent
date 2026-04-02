from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.agent import AgentNormalizedPayload, AgentParsedQuery, AgentResponseEnvelope
from app.schemas.interpret import InterpretationPayload, InterpretResponseEnvelope
from app.schemas.query import ManualQuerySpec, QueryNormalizedPayload, QueryResponseEnvelope, ResolvedQuery


class FakeQueryService:
    async def execute(self, spec: ManualQuerySpec) -> QueryResponseEnvelope:
        return QueryResponseEnvelope(
            trace_id="query-trace",
            normalized=QueryNormalizedPayload(
                query=ResolvedQuery(
                    domain=spec.domain,
                    input_mode=spec.input_mode,
                    identifier=spec.identifier,
                    operation=spec.operation,
                ),
                matches=[],
                primary_result=None,
                synonyms=[],
            ),
            raw={"echo": spec.model_dump(mode="json")},
        )


class FakeInterpretService:
    def execute(self, payload) -> InterpretResponseEnvelope:
        return InterpretResponseEnvelope(
            trace_id="interpret-trace",
            normalized=InterpretationPayload(
                candidates=[],
                confidence=0.2,
                ambiguities=["unsupported"],
                assumptions=[],
                warnings=[],
                needs_confirmation=True,
                recommended_candidate_index=None,
            ),
            raw={"input": payload.text},
        )


class FakeAgentService:
    async def execute(self, payload) -> AgentResponseEnvelope:
        return AgentResponseEnvelope(
            trace_id="agent-trace",
            normalized=AgentNormalizedPayload(
                user_text=payload.text,
                answer="Aspirin is the best match.",
                provider="modal_glm",
                model="zai-org/GLM-5-FP8",
                parsed_query=AgentParsedQuery(
                    compound_name="aspirin",
                    confidence=0.8,
                    recommended_search_mode="name",
                    language="en",
                ),
                compounds=[],
                tool_calls=[],
            ),
            raw=None,
        )


@dataclass
class FakeContainer:
    settings: object
    query_service: object
    interpret_service: object
    agent_service: object

    async def close(self) -> None:
        return None


def test_query_route_returns_envelope() -> None:
    class SettingsStub:
        api_version = "0.1.0"
        environment = "test"
        pubchem_rest_base_url = "https://example.com/pug"
        pubchem_view_base_url = "https://example.com/view"

    app = create_app(
        container_override=FakeContainer(
            settings=SettingsStub(),
            query_service=FakeQueryService(),
            interpret_service=FakeInterpretService(),
            agent_service=FakeAgentService(),
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/query",
            json={
                "domain": "compound",
                "input_mode": "name",
                "identifier": "aspirin",
                "operation": "property",
                "include_raw": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized"]["query"]["identifier"] == "aspirin"


def test_interpret_route_returns_envelope() -> None:
    class SettingsStub:
        api_version = "0.1.0"
        environment = "test"
        pubchem_rest_base_url = "https://example.com/pug"
        pubchem_view_base_url = "https://example.com/view"

    app = create_app(
        container_override=FakeContainer(
            settings=SettingsStub(),
            query_service=FakeQueryService(),
            interpret_service=FakeInterpretService(),
            agent_service=FakeAgentService(),
        )
    )

    with TestClient(app) as client:
        response = client.post("/api/interpret", json={"text": "find aspirin"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized"]["needs_confirmation"] is True


def test_agent_route_returns_envelope() -> None:
    class SettingsStub:
        api_version = "0.1.0"
        environment = "test"
        pubchem_rest_base_url = "https://example.com/pug"
        pubchem_view_base_url = "https://example.com/view"

    app = create_app(
        container_override=FakeContainer(
            settings=SettingsStub(),
            query_service=FakeQueryService(),
            interpret_service=FakeInterpretService(),
            agent_service=FakeAgentService(),
        )
    )

    with TestClient(app) as client:
        response = client.post("/api/agent", json={"text": "find aspirin"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized"]["answer"] == "Aspirin is the best match."
    assert payload["normalized"]["parsed_query"]["recommended_search_mode"] == "name"
