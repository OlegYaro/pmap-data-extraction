from datetime import date

from database.repositories.property_transaction import _prefix_end

from .factories import TransactionFactory

URL = "/transactions"


async def ids(client, **params) -> list[int]:
    response = await client.get(URL, params=params)
    assert response.status_code == 200
    return [row["id"] for row in response.json()]


async def test_filters(client, persist):
    clean, non_market, other = await persist(
        TransactionFactory(),
        TransactionFactory(exclusion_reason="non_market", address="MSC:Kraków;UL:Długa"),
        TransactionFactory(powiat_code="1261", exclusion_reason="package_deal"),
    )

    assert await ids(client) == [clean.id, non_market.id, other.id]
    assert await ids(client, exclusion_reason="clean") == [clean.id]
    assert await ids(client, exclusion_reason=["clean", "non_market"]) == [clean.id, non_market.id]
    assert await ids(client, voivodeship_code="12") == [other.id]
    assert await ids(client, address="długa") == [non_market.id]


async def test_voivodeship_is_a_prefix_of_the_powiat_code(client, persist):
    rows = await persist(
        *[TransactionFactory(powiat_code=code) for code in ("0264", "1401", "1465", "1499", "1500")]
    )
    by_code = {row.powiat_code: row.id for row in rows}

    assert await ids(client, voivodeship_code="14") == [
        by_code[c] for c in ("1401", "1465", "1499")
    ]
    assert await ids(client, voivodeship_code="1465") == [by_code["1465"]]
    assert await ids(client, voivodeship_code="1") == [
        by_code[c] for c in ("1401", "1465", "1499", "1500")
    ]
    assert await ids(client, voivodeship_code="99") == []


def test_prefix_end_is_the_first_string_after_the_prefix():
    assert _prefix_end("14") == "15"
    assert _prefix_end("1465") == "1466"
    assert _prefix_end("19") == "1:"  # still above "199..." and below "2"


async def test_sorts_keep_empty_values_last_in_both_directions(client, persist):
    old, new, undated = await persist(
        TransactionFactory(transaction_date=date(2020, 1, 1)),
        TransactionFactory(transaction_date=date(2024, 1, 1)),
        TransactionFactory(transaction_date=None),
    )

    assert await ids(client, sort="transaction_date", order="desc") == [new.id, old.id, undated.id]
    assert await ids(client, sort="transaction_date", order="asc") == [old.id, new.id, undated.id]


async def test_ties_are_broken_by_id_in_the_sort_direction(client, persist):
    first, second, third = await persist(*[TransactionFactory() for _ in range(3)])

    assert await ids(client, sort="transaction_date", order="desc") == [
        third.id,
        second.id,
        first.id,
    ]
    assert await ids(client, sort="id", order="desc") == [third.id, second.id, first.id]
    assert await ids(client, sort="id", order="asc") == [first.id, second.id, third.id]


async def test_pages_cover_every_row_once(client, persist):
    rows = await persist(
        *[TransactionFactory(price_premises=price) for price in (500, 400, 400, 400, 300)],
        TransactionFactory(rooms=None),
        TransactionFactory(rooms=None),
    )
    for sort in ("price_premises", "rooms", "id"):
        for order in ("asc", "desc"):
            seen, params = [], {"sort": sort, "order": order, "limit": 2}
            while page := (await client.get(URL, params=params)).json():
                seen += [row["id"] for row in page]
                last = page[-1]
                params |= {"after_id": last["id"]}
                if last[sort] is None:
                    params.pop("after_value", None)
                else:
                    params["after_value"] = str(last[sort])
            assert sorted(seen) == sorted(row.id for row in rows), (sort, order)


async def test_card(client, persist):
    row = await persist(TransactionFactory(attributes={"tran_cena_brutto": 600000.0}))

    response = await client.get(f"{URL}/{row.id}")
    assert response.status_code == 200
    assert response.json()["attributes"] == {"tran_cena_brutto": 600000.0}

    assert (await client.get(f"{URL}/{row.id + 1000}")).status_code == 404
