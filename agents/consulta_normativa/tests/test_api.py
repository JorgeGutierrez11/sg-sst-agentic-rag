import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agents.consulta_normativa.api.dependencies import get_query_service
from agents.consulta_normativa.api.main import create_app
from agents.consulta_normativa.api.routes import router
from agents.consulta_normativa.api.schemas import QueryRequest, QueryResponse
from agents.consulta_normativa.api.service import QueryService


class ApiSchemaTests(unittest.TestCase):
    def test_query_request_rejects_blank_question(self) -> None:
        with self.assertRaises(ValidationError):
            QueryRequest(question="   ")

    def test_query_request_trims_question(self) -> None:
        request = QueryRequest(question="  ¿Qué es SG-SST?  ")

        self.assertEqual(request.question, "¿Qué es SG-SST?")

    def test_query_response_shape(self) -> None:
        response = QueryResponse(answer="Respuesta", references=["Referencia"], conversation_id="abc")

        self.assertEqual(response.answer, "Respuesta")
        self.assertEqual(response.references, ["Referencia"])
        self.assertEqual(response.conversation_id, "abc")


class FakeRuntime:
    def __init__(self) -> None:
        self.graph = object()
        self.questions: list[str] = []

    def answer_with_langgraph(self, question: str, graph: object) -> object:
        self.questions.append(question)
        return SimpleNamespace(answer="Respuesta", references=["Ref"], context="ctx", prompt="prompt")


class QueryServiceTests(unittest.TestCase):
    def test_ask_returns_response_with_given_conversation_id(self) -> None:
        service = QueryService(FakeRuntime())

        response = service.ask("¿Qué es el SG-SST?", conversation_id="abc")

        self.assertEqual(response.answer, "Respuesta")
        self.assertEqual(response.references, ["Ref"])
        self.assertEqual(response.conversation_id, "abc")

    def test_ask_generates_conversation_id_when_missing(self) -> None:
        service = QueryService(FakeRuntime())

        response = service.ask("¿Qué es el SG-SST?")

        self.assertTrue(response.conversation_id)


class ApiDependencyTests(unittest.TestCase):
    def test_get_query_service_fails_when_service_missing(self) -> None:
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

        with self.assertRaises(RuntimeError):
            get_query_service(request)


class FailingQueryService(QueryService):
    def __init__(self) -> None:
        super().__init__(FakeRuntime())

    def ask(self, question: str, conversation_id: str | None = None) -> QueryResponse:
        raise RuntimeError("secret details")


def create_test_app(service: QueryService) -> FastAPI:
    app = FastAPI()
    app.state.query_service = service
    app.include_router(router)
    return app


class ApiRouteTests(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        app = create_test_app(QueryService(FakeRuntime()))
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_query_returns_answer(self) -> None:
        app = create_test_app(QueryService(FakeRuntime()))
        client = TestClient(app)

        response = client.post(
            "/api/v1/query",
            json={"question": "¿Qué es SG-SST?", "conversation_id": "abc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Respuesta")
        self.assertEqual(response.json()["references"], ["Ref"])
        self.assertEqual(response.json()["conversation_id"], "abc")

    def test_query_rejects_blank_question(self) -> None:
        app = create_test_app(QueryService(FakeRuntime()))
        client = TestClient(app)

        response = client.post("/api/v1/query", json={"question": "   "})

        self.assertEqual(response.status_code, 422)

    def test_query_failure_returns_sanitized_error(self) -> None:
        app = create_test_app(FailingQueryService())
        client = TestClient(app)

        with self.assertLogs("agents.consulta_normativa.api.routes", level="ERROR"):
            response = client.post(
                "/api/v1/query",
                json={"question": "¿Qué es SG-SST?", "conversation_id": "abc"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "The normative consultation service is temporarily unavailable."})
        self.assertNotIn("secret details", response.text)


class ApiAppTests(unittest.TestCase):
    def test_app_lifespan_builds_query_service_once(self) -> None:
        calls = []

        def runtime_builder() -> FakeRuntime:
            calls.append("built")
            return FakeRuntime()

        app = create_app(runtime_builder=runtime_builder)

        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ["built"])


if __name__ == "__main__":
    unittest.main()
