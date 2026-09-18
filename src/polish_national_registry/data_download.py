import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from database.repositories.prefix_map import PrefixMapRepository
from polish_national_registry.status_service import ExtractionTaskStateService, TaskStatusEnum

log = logging.getLogger(__name__)


class DownloadError(Exception):
    """The file could not be downloaded."""


class DataDownloadService:
    @staticmethod
    def create_url(territory_code: str) -> str:
        """The address of one powiat's file."""
        return f"{settings.SOURCE_BASE_URL}/GPKG/{territory_code}_transakcje_ceny.gpkg.zip"

    @staticmethod
    def client() -> httpx.AsyncClient:
        """A client with the browser User-Agent the portal insists on."""
        return httpx.AsyncClient(
            headers={"User-Agent": settings.SOURCE_USER_AGENT},
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0),
            follow_redirects=True,
        )

    @staticmethod
    async def download_one(
        territory_code: str, dir: Path, client: httpx.AsyncClient, is_admin: bool = False
    ) -> Path | None:
        """Download one powiat into the given folder, return the path or None if not published."""
        url = DataDownloadService.create_url(territory_code)
        target = dir / f"{territory_code}_transakcje_ceny.gpkg.zip"

        if target.exists() and not is_admin:
            log.info(
                "download_skipped territory_code=%s reason=already_on_disk path=%s",
                territory_code,
                target,
            )
            return target

        log.info("download_started territory_code=%s url=%s", territory_code, url)

        try:
            async with client.stream("GET", url) as response:
                if response.status_code == httpx.codes.NOT_FOUND:
                    log.info("download_not_published territory_code=%s", territory_code)
                    return None
                if response.status_code != httpx.codes.OK:
                    raise DownloadError(f"{territory_code}: source answered {response.status_code}")

                expected = response.headers.get("content-length")
                written = 0

                with target.open("wb") as fh:
                    async for chunk in response.aiter_bytes(1_048_576):
                        fh.write(chunk)
                        written += len(chunk)

            if expected and expected.isdigit() and written != int(expected):
                raise DownloadError(f"{territory_code}: got {written} bytes, expected {expected}")

            log.info(
                "download_ok territory_code=%s bytes=%d path=%s", territory_code, written, target
            )
            return target

        except Exception:
            target.unlink(missing_ok=True)
            log.exception("download_failed territory_code=%s url=%s", territory_code, url)
            raise

    @staticmethod
    async def download_all(
        territory_codes: list[str], concurrency: int | None = None, is_admin: bool = False
    ) -> dict[str, Path | None]:
        """Start downloading all powiats concurrently"""

        current_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        dir = settings.DOWNLOAD_DIR / current_date
        dir.mkdir(parents=True, exist_ok=True)

        limit = asyncio.Semaphore(concurrency or settings.DOWNLOAD_CONCURRENCY)
        results = {}

        log.info("download_all_started count=%d dir=%s", len(territory_codes), dir)

        async with DataDownloadService.client() as client:

            async def worker(territory_code: str) -> None:
                async with limit:
                    try:
                        results[territory_code] = await DataDownloadService.download_one(
                            territory_code=territory_code, client=client, is_admin=is_admin, dir=dir
                        )
                    except Exception:
                        results[territory_code] = None

            await asyncio.gather(*[worker(territory_code) for territory_code in territory_codes])

        downloaded = sum(1 for path in results.values() if path is not None)
        log.info(
            "download_all_finished total=%d downloaded=%d missing_or_failed=%d",
            len(territory_codes),
            downloaded,
            len(territory_codes) - downloaded,
        )
        return results

    @staticmethod
    async def start_downloading(
        session: AsyncSession,
        task_id: int,
        territory_code: str | None = None,
        is_admin: bool = False,
    ) -> dict[str, Path | None]:
        """One powiat when a territory_code is given every powiat there is when it is not."""
        territory_codes = (
            [territory_code]
            if territory_code
            else await PrefixMapRepository.list_powiats(session=session)
        )
        await ExtractionTaskStateService.change_task_status(
            session, task_id, TaskStatusEnum.downloading
        )
        try:
            if not territory_codes:
                raise DownloadError("prefix_map is empty - load PRG first")

            results = await DataDownloadService.download_all(
                territory_codes=territory_codes, is_admin=is_admin
            )

            return results
        except Exception:
            await ExtractionTaskStateService.fail(
                session=session,
                task_id=task_id,
                status=TaskStatusEnum.failed,
                stage=TaskStatusEnum.downloading,
            )
            raise
