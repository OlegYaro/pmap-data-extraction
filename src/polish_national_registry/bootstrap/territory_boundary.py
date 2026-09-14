from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.prefix_map import PrefixMapRepository
from polish_national_registry.bootstrap.dbf import read_dbf
from polish_national_registry.bootstrap.districts import (
    DISTRICT_GMINAS,
    STRIP_NUMBERS,
    clean_unit_name,
    strip_number,
)

LAYER_VOIVODESHIP = "A01_Granice_wojewodztw"
LAYER_POWIAT = "A02_Granice_powiatow"
LAYER_GMINA = "A03_Granice_gmin"
LAYER_UNIT = "A05_Granice_jednostek_ewidencyjnych"
LAYER_OBREB = "A06_Granice_obrebow_ewidencyjnych"
LAYERS = (LAYER_VOIVODESHIP, LAYER_POWIAT, LAYER_GMINA, LAYER_UNIT, LAYER_OBREB)

COL_CODE = "JPT_KOD_JE"
COL_NAME = "JPT_NAZWA_"

EMPTY_ROW: dict[str, str | None] = {
    "voivodeship_teryt": None,
    "voivodeship_name": None,
    "powiat_teryt": None,
    "powiat_name": None,
    "gmina_teryt": None,
    "gmina_name": None,
    "district_name": None,
}


def unit_gmina(unit: str) -> str:
    """Convert a cadastral unit code into the TERYT code of its gmina.

    Kinds 4 and 5 map to the urban-rural gmina (digit 3), kinds 8 and 9 to the city itself.
    """
    kind = unit[7]
    if kind in "89":
        return unit[:4] + "011"
    return unit[:6] + ("3" if kind in "45" else kind)


class TerritoryBoundary:
    """Territory boundaries from the National Boundary Registry, stored as prefix_map rows.

    Call the loader that matches the format of the incoming data.
    """

    @classmethod
    async def load_dbf(
        cls, session: AsyncSession, folder: Path, districts: set[str] = DISTRICT_GMINAS
    ) -> list[dict[str, str | None]]:
        """Replace prefix_map with territories read from National Boundary Registry .dbf layers.

        Fails before touching the database if any layer is missing. The caller commits.
        """
        rows = cls._rows_from_dbf(folder, districts)
        await PrefixMapRepository.replace_all(session, rows)
        return rows

    @classmethod
    def _rows_from_dbf(cls, folder: Path, districts: set[str]) -> list[dict[str, str | None]]:
        """Read the National Boundary Registry .dbf layers into a list of prefix_map rows."""

        rows: dict[str, dict[str, str | None]] = {}

        for code, name in cls._read_layer(folder, LAYER_VOIVODESHIP):
            rows[code] = EMPTY_ROW | {"voivodeship_teryt": code, "voivodeship_name": name}
        for code, name in cls._read_layer(folder, LAYER_POWIAT):
            rows[code] = rows[code[:2]] | {"powiat_teryt": code, "powiat_name": name}
        for code, name in cls._read_layer(folder, LAYER_GMINA):
            rows[code] = rows[code[:4]] | {"gmina_teryt": code, "gmina_name": name}

        for code, name in cls._read_layer(folder, LAYER_UNIT):
            gmina = rows[unit_gmina(code)]
            district = clean_unit_name(name, gmina["gmina_name"]) if code[7] in "89" else None
            rows[code] = gmina | {"district_name": district}

        for code, name in cls._read_layer(folder, LAYER_OBREB):
            unit = rows[code[:8]]
            if unit["gmina_teryt"] in districts:
                district = strip_number(name) if unit["gmina_teryt"] in STRIP_NUMBERS else name
                rows[code] = unit | {"district_name": district}

        return [{"prefix_code": code, **row} for code, row in rows.items()]

    @staticmethod
    def _read_layer(folder: Path, layer: str) -> list[tuple[str, str]]:
        return [(r[COL_CODE], r[COL_NAME]) for r in read_dbf(folder / f"{layer}.dbf")]
