# tasks.py
from taskiq import Context, TaskiqDepends, broker


@broker.task(task_name="sync_registry")
async def sync_registry_manual(teryt: str | None, context: Context = TaskiqDepends()):
    """Sync the registry for a manual call powiat or all powiats if teryt is None."""
    pass


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def sync_registry_all():
    """Sync the registry for all powiats."""
    pass
