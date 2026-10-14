from sqlalchemy import select

from database.models.property_transaction import PropertyTransaction
from database.models.task_status import TaskStatusEnum

from .factories import TaskFactory
from .test_transaction_cleaning_and_load import assigned, load

NEW_VERSION = "2019-01-01T00:00:00"


async def test_post_adds_a_manual_transaction(client):
    response = await client.post("/transactions", json={"powiat_code": "1465", "rooms": 2})

    assert response.status_code == 201
    body = response.json()
    assert body["external_transaction_identifier"].startswith("manual-")
    assert body["attributes"] == {"source": "manual"}


async def test_registry_does_not_overwrite_a_correction(client, session, persist):
    task = await persist(TaskFactory(status=TaskStatusEnum.cleaning))
    await load(session, task, assigned())
    row = await session.scalar(select(PropertyTransaction))

    response = await client.patch(f"/transactions/{row.id}", json={"price_premises": 500000})
    assert (response.status_code, response.json()["price_premises"]) == (200, 500000.0)

    await load(session, task, assigned(tran_wersja_id=NEW_VERSION, lok_cena_brutto=1.0))
    await session.refresh(row)
    assert (float(row.price_premises), row.attributes["source"]) == (500000.0, "manual")

    await client.patch(f"/transactions/{row.id}", json={"accept_registry": True})
    await load(session, task, assigned(tran_wersja_id=NEW_VERSION, lok_cena_brutto=1.0))
    await session.refresh(row)
    assert (float(row.price_premises), "source" in row.attributes) == (1.0, False)


async def test_patch_unknown_transaction(client):
    assert (await client.patch("/transactions/1000000", json={"rooms": 1})).status_code == 404
