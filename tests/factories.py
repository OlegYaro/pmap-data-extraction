import uuid

import factory

from database.models.prefix_map import PrefixMap
from database.models.task_status import DataExtractionTask, TaskStatusEnum, TaskTriggerEnum

RUN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class TaskFactory(factory.Factory):
    class Meta:
        model = DataExtractionTask

    run_id = RUN_ID
    territory_code = factory.Sequence(lambda n: f"02{n:02d}")
    status = TaskStatusEnum.queued
    trigger = TaskTriggerEnum.manual


class PrefixMapFactory(factory.Factory):
    class Meta:
        model = PrefixMap

    prefix_code = factory.Sequence(lambda n: f"02230{n}_2")
    voivodeship_teryt = "02"
    voivodeship_name = "dolnoslaskie"
    powiat_teryt = factory.Sequence(lambda n: f"02{n:02d}")
    powiat_name = factory.Sequence(lambda n: f"powiat {n}")
