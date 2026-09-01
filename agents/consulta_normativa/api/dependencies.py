# pyrefly: ignore [missing-import]
from fastapi import Request

from agents.consulta_normativa.api.service import QueryService


def get_query_service(request: Request) -> QueryService:
    service = getattr(request.app.state, "query_service", None)
    if not isinstance(service, QueryService):
        raise RuntimeError("Query service is not initialized.")
    return service
