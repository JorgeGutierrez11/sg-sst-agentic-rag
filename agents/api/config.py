"""HTTP configuration for the unified agent API."""

import os
from urllib.parse import urlsplit


def get_cors_allowed_origins() -> list[str]:
    """Return the browser origins allowed for cross-origin API requests.

    Reads the comma-separated ``CORS_ALLOWED_ORIGINS`` variable. Each entry must
    be an exact ``http(s)://host[:port]`` origin; ``*`` is rejected because the
    API enables CORS credentials.
    """
    raw_value = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if not origins:
        raise ValueError("CORS_ALLOWED_ORIGINS is not configured in the environment.")

    for origin in origins:
        parsed = urlsplit(origin)
        is_exact_origin = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
            and origin == f"{parsed.scheme}://{parsed.netloc}"
        )
        if not is_exact_origin:
            raise ValueError(
                f"CORS_ALLOWED_ORIGINS contains an invalid origin: {origin!r}. "
                "Use http(s)://host[:port] without path, trailing slash or '*'."
            )
    return origins
