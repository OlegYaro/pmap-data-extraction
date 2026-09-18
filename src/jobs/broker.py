from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from core import settings

broker = ListQueueBroker(settings.REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(settings.REDIS_URL)
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
