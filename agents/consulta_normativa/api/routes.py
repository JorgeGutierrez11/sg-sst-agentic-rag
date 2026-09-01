import logging
from time import perf_counter
from uuid import uuid4

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Request

from agents.consulta_normativa.api.dependencies import get_query_service
from agents.consulta_normativa.api.schemas import HealthResponse, QueryRequest, QueryResponse
from agents.consulta_normativa.api.service import QueryService


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/api/v1/query", response_model=QueryResponse)
def query(
    payload: QueryRequest, # Es la solicitud que recibe
    http_request: Request, # Es la solicitud http
    service: QueryService = Depends(get_query_service), # Es la logica de negocio
) -> QueryResponse:
    request_id = str(uuid4())
    started_at = perf_counter()

    try:
        response = service.ask(payload.question, payload.conversation_id)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "API query completed | request_id=%s | conversation_id=%s | endpoint=%s | status_code=200 | duration_ms=%s",
            request_id,
            response.conversation_id,
            http_request.url.path,
            duration_ms,
        )
        return response
    except Exception as error:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.error(
            "API query failed | request_id=%s | conversation_id=%s | endpoint=%s | status_code=503 | duration_ms=%s | error=%s",
            request_id,
            payload.conversation_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="The normative consultation service is temporarily unavailable.",
        ) from error
