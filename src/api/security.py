import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from core import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: Annotated[str | None, Security(api_key_header)]) -> None:
    """Let the request through only with the API key from the settings."""
    expected = settings.API_KEY.get_secret_value() if settings.API_KEY else ""
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API key is not configured")
    if api_key is None or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid X-API-Key header")
