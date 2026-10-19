import uuid
from datetime import date

import factory

from database.models.prefix_map import PrefixMap
from database.models.property_transaction import PropertyTransaction
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


class TransactionFactory(factory.Factory):
    class Meta:
        model = PropertyTransaction

    external_transaction_identifier = factory.Sequence(lambda n: f"deed-{n}")
    external_building_id = factory.Sequence(lambda n: f"146519_8.0119.23.{n}_BUD.1_LOK")
    date_source_version = "2024-01-01T00:00:00"
    transaction_date = date(2024, 1, 15)
    price_premises = 600000
    area_usable = 60
    rooms = 3
    floor = 2
    market_type = "wtorny"
    function = "mieszkalna"
    address = "MSC:Warszawa;UL:Aleja Wojska Polskiego;NR_PORZ:31"
    powiat_code = "1465"
    gmina_code = "1465011"
    city_name = "Warszawa"
    district_name = "Żoliborz"
    attributes = factory.LazyFunction(dict)
