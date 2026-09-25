import logging
import traceback
import uuid
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from polish_national_registry.status_service import ExtractionTaskStateService, TaskStatusEnum

log = logging.getLogger(__name__)

SOURCE_BASE_URL = "https://opendata.geoportal.gov.pl/InneDane/latest_exports/rcn_transakcje_ceny"
SOURCE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class DownloadError(Exception):
    """The file could not be downloaded."""


class DataDownloadService:
    @staticmethod
    def create_url(territory_code: str) -> str:
        """The address of one powiat's file."""
        return f"{SOURCE_BASE_URL}/GPKG/{territory_code}_transakcje_ceny.gpkg.zip"

    @staticmethod
    def client() -> httpx.AsyncClient:
        """A client with the browser User-Agent the portal insists on."""
        return httpx.AsyncClient(
            headers={"User-Agent": SOURCE_USER_AGENT},
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0),
            follow_redirects=True,
        )

    @staticmethod
    async def download_one(
        territory_code: str, target_dir: Path, client: httpx.AsyncClient
    ) -> Path | None:
        """Download one powiat into the given folder, return the path or None if not published."""
        url = DataDownloadService.create_url(territory_code)
        target = target_dir / f"{territory_code}_transakcje_ceny.gpkg.zip"
        part = target.with_name(f"{target.name}.{uuid.uuid4().hex}.part")

        log.info("download_started territory_code=%s url=%s", territory_code, url)

        try:
            async with client.stream("GET", url) as response:
                if response.status_code == httpx.codes.NOT_FOUND:
                    log.info("download_not_published territory_code=%s", territory_code)
                    return None
                if response.status_code != httpx.codes.OK:
                    await response.aread()
                    raise DownloadError(
                        f"{territory_code}: source answered {response.status_code}: "
                        f"{response.content!r}"
                    )

                expected = response.headers.get("content-length")
                written = 0

                with part.open("wb") as fh:
                    async for chunk in response.aiter_bytes(1_048_576):
                        fh.write(chunk)
                        written += len(chunk)

            if expected and expected.isdigit() and written != int(expected):
                raise DownloadError(f"{territory_code}: got {written} bytes, expected {expected}")

            part.replace(target)

        except httpx.HTTPError as exc:
            log.exception("download_http_error territory_code=%s url=%s", territory_code, url)
            raise DownloadError(f"{territory_code}: http error {exc!r}") from exc
        except OSError as exc:
            log.exception("download_save_error territory_code=%s path=%s", territory_code, part)
            raise DownloadError(f"{territory_code}: cannot save to {part}") from exc
        finally:
            part.unlink(missing_ok=True)

        log.info("download_ok territory_code=%s bytes=%d path=%s", territory_code, written, target)
        return target

    @staticmethod
    async def start_downloading(
        session: AsyncSession, task_id: int, territory_code: str, target_dir: Path
    ) -> Path | None:
        """Download one powiat and keep its task status up to date."""
        await ExtractionTaskStateService.change_task_status(
            session, task_id, TaskStatusEnum.downloading
        )
        try:
            async with DataDownloadService.client() as client:
                path = await DataDownloadService.download_one(territory_code, target_dir, client)
        except Exception:
            await session.rollback()
            await ExtractionTaskStateService.fail(
                session, task_id, error_trace=traceback.format_exc()
            )
            raise

        status = TaskStatusEnum.staged if path else TaskStatusEnum.not_published
        await ExtractionTaskStateService.change_task_status(session, task_id, status)
        return path
