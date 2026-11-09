import uuid
from datetime import UTC, datetime

from database.models.task_status import TaskStatusEnum
from jobs.tasks import orchestrate_run

from .factories import RUN_ID, TaskFactory, TransactionFactory

RUNS_URL = "/runs"


async def test_start_pipeline_queues_the_orchestrator(client, monkeypatch):
    queued = {}

    async def fake_kiq(**kwargs):
        queued.update(kwargs)

    monkeypatch.setattr(orchestrate_run, "kiq", fake_kiq)

    response = await client.post(RUNS_URL, params={"territory_code": "0201"})

    assert response.status_code == 202
    run_id = response.json()["run_id"]
    assert queued == {
        "run_id": run_id,
        "territory_code": "0201",
        "trigger": "manual",
    }


async def test_get_run_returns_counters(client, persist):
    await persist(
        TaskFactory(status=TaskStatusEnum.assigning),
        TaskFactory(status=TaskStatusEnum.failed, failed_stage="downloading", error_trace="boom"),
    )

    response = await client.get(f"{RUNS_URL}/{RUN_ID}")

    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["downloaded"], body["failed"]) == (2, 1, 1)
    assert body["failed_tasks"][0]["error_trace"] == "boom"


async def test_get_run_returns_404_for_unknown_run(client):
    response = await client.get(f"{RUNS_URL}/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_list_runs(client, persist):
    await persist(
        TaskFactory(status=TaskStatusEnum.done), TaskFactory(status=TaskStatusEnum.failed)
    )

    response = await client.get(RUNS_URL)

    assert response.status_code == 200
    run = response.json()[0]
    assert (run["run_id"], run["total"], run["done"], run["failed"]) == (str(RUN_ID), 2, 1, 1)


async def test_get_run_returns_quality_summary(client, persist):
    past = datetime(2025, 1, 1, tzinfo=UTC)
    # The summary reads the rows of the powiats of the run's tasks (powiat_code is indexed).
    await persist(
        TaskFactory(status=TaskStatusEnum.done, territory_code="1465"),
        TransactionFactory(run_id=RUN_ID, powiat_code="1465"),
        TransactionFactory(run_id=RUN_ID, powiat_code="1465", exclusion_reason="non_market"),
        TransactionFactory(run_id=RUN_ID, powiat_code="1465", created_at=past),
    )

    body = (await client.get(f"{RUNS_URL}/{RUN_ID}")).json()

    assert (body["inserted"], body["updated"], body["excluded"]) == (2, 1, {"non_market": 1})


async def test_summary_ignores_rows_of_powiats_outside_the_run(client, persist):
    await persist(
        TaskFactory(status=TaskStatusEnum.done, territory_code="1465"),
        TransactionFactory(run_id=RUN_ID, powiat_code="1465"),
        TransactionFactory(run_id=RUN_ID, powiat_code="0264", exclusion_reason="non_market"),
    )

    body = (await client.get(f"{RUNS_URL}/{RUN_ID}")).json()

    assert (body["inserted"], body["updated"], body["excluded"]) == (1, 0, {})
