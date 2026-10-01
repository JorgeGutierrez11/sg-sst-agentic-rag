import logging
from time import perf_counter
from uuid import uuid4

# pyrefly: ignore [missing-import]
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)

from agents.diagnostico_cumplimiento.api.dependencies import (
    get_diagnostic_service,
)
from agents.diagnostico_cumplimiento.api.schemas import (
    CompleteDiagnosticResponse,
    CreateDiagnosticRequest,
    CreateDiagnosticResponse,
    HealthResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from agents.diagnostico_cumplimiento.api.service import (
    DiagnosticService,
)
from agents.diagnostico_cumplimiento.catalog.selector import (
    CatalogSelectionError,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/diagnostics",
    tags=["diagnostics"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post(
    "",
    response_model=CreateDiagnosticResponse,
    status_code=201,
)
def create_diagnostic(
    payload: CreateDiagnosticRequest,
    http_request: Request,
    service: DiagnosticService = Depends(
        get_diagnostic_service
    ),
) -> CreateDiagnosticResponse:
    request_id = str(uuid4())
    started_at = perf_counter()

    try:
        response = service.create_diagnostic(payload)

        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.info(
            "Diagnostic created | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=201 | "
            "duration_ms=%s",
            request_id,
            response.diagnosis_id,
            http_request.url.path,
            duration_ms,
        )

        return response

    except CatalogSelectionError as error:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.warning(
            "Diagnostic profile out of scope | "
            "request_id=%s | endpoint=%s | "
            "status_code=400 | duration_ms=%s | "
            "error=%s",
            request_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except ValueError as error:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.warning(
            "Diagnostic creation rejected | "
            "request_id=%s | endpoint=%s | "
            "status_code=400 | duration_ms=%s | "
            "error=%s",
            request_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.error(
            "Diagnostic creation failed | "
            "request_id=%s | endpoint=%s | "
            "status_code=503 | duration_ms=%s | "
            "error=%s",
            request_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The diagnostic service is temporarily "
                "unavailable."
            ),
        ) from error


@router.post(
    "/{diagnosis_id}/answers",
    response_model=SubmitAnswerResponse,
)
def submit_answer(
    diagnosis_id: str,
    payload: SubmitAnswerRequest,
    http_request: Request,
    service: DiagnosticService = Depends(
        get_diagnostic_service
    ),
) -> SubmitAnswerResponse:
    request_id = str(uuid4())
    started_at = perf_counter()

    try:
        response = service.submit_answer(
            diagnosis_id=diagnosis_id,
            payload=payload,
        )

        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.info(
            "Diagnostic answer submitted | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=200 | "
            "duration_ms=%s",
            request_id,
            diagnosis_id,
            http_request.url.path,
            duration_ms,
        )

        return response

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Diagnostic session not found.",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except Exception as error:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.error(
            "Diagnostic answer failed | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=503 | "
            "duration_ms=%s | error=%s",
            request_id,
            diagnosis_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The diagnostic service is temporarily "
                "unavailable."
            ),
        ) from error


@router.get(
    "/{diagnosis_id}/report",
)
def get_diagnostic_report(
    diagnosis_id: str,
    http_request: Request,
    service: DiagnosticService = Depends(
        get_diagnostic_service
    ),
) -> Response:
    """
    Genera y entrega el informe PDF de un diagnóstico
    completado.

    El documento se genera en memoria y la sesión temporal
    se elimina después de producir correctamente el PDF.
    """
    request_id = str(uuid4())
    started_at = perf_counter()

    try:
        pdf_bytes = service.generate_report_pdf(
            diagnosis_id=diagnosis_id,
        )

        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.info(
            "Diagnostic report generated | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=200 | "
            "duration_ms=%s",
            request_id,
            diagnosis_id,
            http_request.url.path,
            duration_ms,
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'inline; filename="diagnostico_sgsst.pdf"'
                ),
                "Cache-Control": (
                    "private, no-store, max-age=0"
                ),
                "Pragma": "no-cache",
            },
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Diagnostic session not found.",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except Exception as error:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.error(
            "Diagnostic report generation failed | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=503 | "
            "duration_ms=%s | error=%s",
            request_id,
            diagnosis_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The diagnostic report is temporarily "
                "unavailable."
            ),
        ) from error


@router.post(
    "/{diagnosis_id}/complete",
    response_model=CompleteDiagnosticResponse,
)
def complete_diagnostic(
    diagnosis_id: str,
    http_request: Request,
    service: DiagnosticService = Depends(
        get_diagnostic_service
    ),
) -> CompleteDiagnosticResponse:
    request_id = str(uuid4())
    started_at = perf_counter()

    try:
        response = service.complete_diagnostic(
            diagnosis_id=diagnosis_id,
        )

        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.info(
            "Diagnostic completed | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=200 | "
            "duration_ms=%s",
            request_id,
            diagnosis_id,
            http_request.url.path,
            duration_ms,
        )

        return response

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Diagnostic session not found.",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except Exception as error:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.error(
            "Diagnostic completion failed | "
            "request_id=%s | diagnosis_id=%s | "
            "endpoint=%s | status_code=503 | "
            "duration_ms=%s | error=%s",
            request_id,
            diagnosis_id,
            http_request.url.path,
            duration_ms,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The diagnostic service is temporarily "
                "unavailable."
            ),
        ) from error
