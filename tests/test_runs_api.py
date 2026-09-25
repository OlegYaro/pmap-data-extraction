import uuid

from database.models.task_status import TaskStatusEnum
from jobs.tasks import orchestrate_run

from .factories import RUN_ID, TaskFactory

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
