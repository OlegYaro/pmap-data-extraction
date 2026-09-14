from sqlalchemy import Row


def resolve(identifier: str | None, lookup: dict[str, Row]) -> Row | None:
    """Find the territory of a transaction by its cadastral identifier.

    Tries "unit.obreb" first, which gives the district, then "unit", which gives the gmina.
    """
    if not identifier:
        return None
    unit, _, rest = identifier.partition(".")
    obreb = rest.partition(".")[0]
    return lookup.get(f"{unit}.{obreb}") or lookup.get(unit)
