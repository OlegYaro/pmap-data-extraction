import asyncio
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from extraction.boundary_registry import territory_boundary
from extraction.db import SessionFactory

URL = "https://opendata.geoportal.gov.pl/prg/granice/00_jednostki_administracyjne.zip"
PRG_DIR = Path(__file__).resolve().parents[1] / "data" / "boundaries" / "National Boundary Registry"


def download() -> Path:
    """Download the PRG archive and extract its tables into a folder named by today's date.

    The dated folder is created as the last step, so an interrupted download never leaves one.
    """

    PRG_DIR.mkdir(parents=True, exist_ok=True)
    archive = PRG_DIR / "prg.zip"
    partial = PRG_DIR / "partial"
    urllib.request.urlretrieve(URL, archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(partial, [n for n in z.namelist() if n.endswith((".dbf", ".cpg"))])
    folder = partial.rename(PRG_DIR / datetime.now(UTC).date().isoformat())
    archive.unlink()
    return folder


async def load(folder: Path) -> None:
    """Load the registry from a National Boundary Registry folder into the database in one transaction."""

    async with SessionFactory.begin() as session:
        await territory_boundary.load_dbf(session, folder)


if __name__ == "__main__":
    downloaded = sorted(PRG_DIR.glob("????-??-??"))
    asyncio.run(load(downloaded[-1] if downloaded else download()))
