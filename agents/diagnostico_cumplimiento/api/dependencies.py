# pyrefly: ignore [missing-import]
from fastapi import Request

from agents.diagnostico_cumplimiento.api.service import (
    DiagnosticService,
)


def get_diagnostic_service(
    request: Request,
) -> DiagnosticService:
    service = getattr(
        request.app.state,
        "diagnostic_service",
        None,
    )

    if not isinstance(service, DiagnosticService):
        raise RuntimeError(
            "Diagnostic service is not initialized."
        )

    return service
