from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from extraction.boundary_registry.dbf import read_dbf
from extraction.boundary_registry.districts import (
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


def _read_layer(folder: Path, layer: str) -> list[tuple[str, str]]:
    return [(r[COL_CODE], r[COL_NAME]) for r in read_dbf(folder / f"{layer}.dbf")]


def build_rows(folder: Path, districts: set[str] = DISTRICT_GMINAS) -> list[dict[str, str | None]]:
    """Build every prefix_map row from the PRG layers.

    Levels are built top-down: each row is a copy of its parent plus its own columns.
    """

    rows: dict[str, dict[str, str | None]] = {}

    for code, name in _read_layer(folder, LAYER_VOIVODESHIP):
        rows[code] = EMPTY_ROW | {"voivodeship_teryt": code, "voivodeship_name": name}
    for code, name in _read_layer(folder, LAYER_POWIAT):
        rows[code] = rows[code[:2]] | {"powiat_teryt": code, "powiat_name": name}
    for code, name in _read_layer(folder, LAYER_GMINA):
        rows[code] = rows[code[:4]] | {"gmina_teryt": code, "gmina_name": name}

    for code, name in _read_layer(folder, LAYER_UNIT):
        gmina = rows[unit_gmina(code)]
        district = clean_unit_name(name, gmina["gmina_name"]) if code[7] in "89" else None
        rows[code] = gmina | {"district_name": district}

    for code, name in _read_layer(folder, LAYER_OBREB):
        unit = rows[code[:8]]
        if unit["gmina_teryt"] in districts:
            district = strip_number(name) if unit["gmina_teryt"] in STRIP_NUMBERS else name
            rows[code] = unit | {"district_name": district}

    return [{"prefix_code": code, **row} for code, row in rows.items()]


async def load_dbf(
    session: AsyncSession, folder: Path, districts: set[str] = DISTRICT_GMINAS
) -> list[dict[str, str | None]]:
    """Replace prefix_map with the registry built from PRG and return the inserted rows.

    The caller commits the transaction.
    """

    rows = build_rows(folder, districts)
    await session.execute(text("TRUNCATE prefix_map"))
    await session.execute(
        text(
            """
            INSERT INTO prefix_map (prefix_code, voivodeship_teryt, voivodeship_name,
                                    powiat_teryt, powiat_name, gmina_teryt, gmina_name,
                                    district_name)
            VALUES (:prefix_code, :voivodeship_teryt, :voivodeship_name,
                    :powiat_teryt, :powiat_name, :gmina_teryt, :gmina_name,
                    :district_name)
            """
        ),
        rows,
    )
    return rows
