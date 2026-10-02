import asyncio
import logging
import sqlite3
import tempfile
import traceback
import zipfile
from contextlib import closing
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.property_transaction import StagedTransactionRepository
from polish_national_registry.status_service import ExtractionTaskStateService
from polish_national_registry.territory_assignment import (
    SourceTransactionDTO,
    TransactionVersionDTO,
)

log = logging.getLogger(__name__)


class TransactionFilterError(Exception):
    """The file has no layer with premises transactions."""


class TransactionFilterService:
    @staticmethod
    def read_transactions(archive: Path) -> list[SourceTransactionDTO]:
        """Open the powiat zip and return every row of its premises table as {column: value}."""
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as zf:
            name = next(n for n in zf.namelist() if n.endswith(".gpkg"))
            gpkg = Path(zf.extract(name, tmp))
            with closing(sqlite3.connect(gpkg)) as conn:
                conn.row_factory = sqlite3.Row
                tables = [r[0] for r in conn.execute("SELECT table_name FROM gpkg_contents")]
                for table in tables:
                    columns = [c[1] for c in conn.execute(f'PRAGMA table_info("{table}")')]
                    if "lok_id_lokalu" in columns:
                        rows = conn.execute(f'SELECT * FROM "{table}"')  # noqa: S608
                        return [SourceTransactionDTO.from_row(dict(row)) for row in rows]
        raise TransactionFilterError(f"{archive.name}: no layer with column {'lok_id_lokalu'}")

    @staticmethod
    def new_only(
        transactions: list[SourceTransactionDTO], known: set[TransactionVersionDTO]
    ) -> list[SourceTransactionDTO]:
        """Keep the transactions whose key and version are not in the database yet."""
        new_transactions = []
        for transaction in transactions:
            if transaction.version not in known:
                new_transactions.append(transaction)
        return new_transactions

    @staticmethod
    async def start_filtering(
        session: AsyncSession, task_id: int, territory_code: str, archive: Path
    ) -> list[SourceTransactionDTO]:
        """Read one powiat file and keep only the new and changed transactions."""
        try:
            transactions = await asyncio.to_thread(
                TransactionFilterService.read_transactions, archive
            )
            known = await StagedTransactionRepository.get_versions(session, territory_code)
            new_transactions = TransactionFilterService.new_only(transactions, known)
        except Exception:
            await session.rollback()
            await ExtractionTaskStateService.fail(
                session, task_id, error_trace=traceback.format_exc()
            )
            raise

        log.info(
            "filter_ok territory_code=%s total=%d new=%d",
            territory_code,
            len(transactions),
            len(new_transactions),
        )
        return new_transactions
