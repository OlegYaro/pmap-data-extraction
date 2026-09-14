import re

UNIT_SUFFIX_RE = re.compile(r" - (dzielnica|delegatura)$")
NAME_WITH_NUMBER_RE = re.compile(r"^\s*(?:\d+\w?\s+)?(.*?)(?:\s+(?:nr\s*)?\d+\w?)?\s*$", re.I)

DISTRICT_GMINAS: set[str] = {
    "0264011",
    "2466011",
    "0262011",
    "2061011",
    "1805011",
    "1661011",
    "1863011",
    "2262011",
    "2465011",
    "2473011",
    "3062011",
    "0203011",
    "1462011",
    "2610011",
    "0861011",
    "2462011",
    "0608011",
    "0208021",
    "2469011",
    "0607011",
    "2467011",
    "0606011",
    "2416021",
    "1864011",
    "1402011",
    "1428011",
    "2472011",
    "2411011",
    "2413041",
    "2470011",
    "0663011",
    "3064011",
    "1463011",
    "3061011",
    "2461011",
    "0265011",
    "2471011",
    "3262011",
}

STRIP_NUMBERS: set[str] = {
    "1463011",
    "3061011",
    "2461011",
    "0265011",
    "2471011",
    "3262011",
}


def clean_unit_name(name: str, gmina_name: str) -> str:
    """Turn a cadastral unit name into a district name: 'Łódź-Bałuty - delegatura' -> 'Bałuty'."""

    return UNIT_SUFFIX_RE.sub("", name).removeprefix(f"{gmina_name}-")


def strip_number(name: str) -> str:
    """Strip the obreb number from a name: 'Dąbie 806' -> 'Dąbie', '060 Rajsków' -> 'Rajsków'."""

    return NAME_WITH_NUMBER_RE.match(name).group(1)
