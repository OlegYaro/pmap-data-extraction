from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

ADMIN_PAGE = Path(__file__).parent.parent / "static" / "admin.html"

router = APIRouter(tags=["admin"])


@router.get("/admin", include_in_schema=False)
async def admin_page() -> FileResponse:
    """Admin page it calls the API itself with the X-API-Key the user enters."""
    return FileResponse(ADMIN_PAGE)
