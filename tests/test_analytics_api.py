from datetime import date

from .factories import PrefixMapFactory, TransactionFactory


async def test_stats_count_quartiles_of_clean_transactions(client, persist):
    await persist(
        *[TransactionFactory(price_premises=price * 10, area_usable=10) for price in (1, 2, 3, 4)],
        TransactionFactory(price_premises=10**6, area_usable=10, exclusion_reason="non_market"),
    )

    response = await client.get("/analytics/stats")

    assert response.status_code == 200
    assert response.json() == [{"group": None, "count": 4, "p25": 1.75, "median": 2.5, "p75": 3.25}]


async def test_stats_by_month_with_filters(client, persist):
    await persist(
        TransactionFactory(transaction_date=date(2024, 1, 5), rooms=2),
        TransactionFactory(transaction_date=date(2024, 3, 5), rooms=2),
        TransactionFactory(transaction_date=date(2024, 3, 9), rooms=3),
    )

    response = await client.get("/analytics/stats", params={"group_by": "month", "rooms": [2]})

    assert [(row["group"], row["count"]) for row in response.json()] == [
        ("2024-01", 1),
        ("2024-03", 1),
    ]


async def test_territories(client, persist):
    await persist(PrefixMapFactory(gmina_teryt="0201011", gmina_name="Bolesławiec"))

    response = await client.get("/territories")

    assert response.status_code == 200
    assert response.json()[0]["gmina_name"] == "Bolesławiec"
