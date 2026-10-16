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
