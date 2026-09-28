from sqlalchemy import select

from database.models.staged_transaction import StagedTransaction
from database.models.task_status import TaskStatusEnum
from polish_national_registry.territory_assignment import AssignedTransactionDTO
from polish_national_registry.transaction_cleaning import TransactionCleaningService
from polish_national_registry.transaction_load import TransactionLoadService

from .factories import TaskFactory

SOURCE = {
    "fid": 2,
    "geometry": None,
    "gid": 5961702,
    "serwis_rcn": None,
    "teryt": "1465",
    "tran_przestrzen_nazw": "PL.PZGiK.5346.RCN",
    "tran_lokalny_id_iip": "4439eb7c-404f-4166-bae7-93df63f226be",
    "tran_wersja_id": "2018-01-10T07:21:42",
    "tran_rodzaj_trans": "wolnyRynek",
    "tran_rodzaj_rynku": "wtorny",
    "tran_sprzedajacy": "osobaFizyczna",
    "tran_kupujacy": "osobaFizyczna",
    "tran_cena_brutto": 600000.0,
    "tran_vat": None,
    "dok_data": "2017-04-26T22:00:00.000Z",
    "nier_rodzaj": "nieruchomoscLokalowa",
    "nier_prawo": "wlasnoscLokaluWrazZPrawemZwiazanym",
    "nier_udzial": "1/1",
    "nier_pow_gruntu": None,
    "nier_cena_brutto": 600000.0,
    "nier_vat": None,
    "lok_id_lokalu": "146519_8.0119.23.1_BUD.29_LOK",
    "lok_nr_lokalu": "29_LOK",
    "lok_funkcja": "mieszkalna",
    "lok_liczba_izb": 4,
    "lok_nr_kond": 3,
    "lok_pow_uzyt": 58.47,
    "lok_pow_przyn": None,
    "lok_cena_brutto": 600000.0,
    "lok_vat": None,
    "lok_adres": "MSC:Warszawa;UL:Aleja Wojska Polskiego;NR_PORZ:31",
}
TERRITORY = {
    "prefix_code": "146519_8",
    "province_code": "14",
    "province_name": "mazowieckie",
    "powiat_code": "1465",
    "powiat_name": "powiat Warszawa",
    "gmina_code": "1465011",
    "gmina_name": "Warszawa",
    "city_name": "Warszawa",
    "district_name": "Żoliborz",
}


def assigned(territory: dict | None = None, **source) -> AssignedTransactionDTO:
    return AssignedTransactionDTO(
        transaction={**SOURCE, **source}, **(TERRITORY if territory is None else territory)
    )


def clean(*items: AssignedTransactionDTO):
    return TransactionCleaningService.clean_all(list(items))


async def load(session, task, *items):
    await TransactionLoadService.start_loading(session, task.id, "1465", task.run_id, clean(*items))


def test_city_without_district_is_fine():
    assert clean(assigned({**TERRITORY, "district_name": None}))[0].exclusion_reason is None


def test_fractional_share():
    assert clean(assigned(nier_udzial="1/2"))[0].exclusion_reason == "fractional_share"
    assert clean(assigned(nier_udzial="2/2"))[0].exclusion_reason is None


def test_non_market():
    assert clean(assigned(tran_rodzaj_trans="przetarg"))[0].exclusion_reason == "non_market"


def test_missing_fields():
    assert clean(assigned(lok_pow_uzyt=None))[0].exclusion_reason == "missing_fields"
    assert clean(assigned(lok_cena_brutto=0.0))[0].exclusion_reason == "missing_fields"
    assert clean(assigned(dok_data=None))[0].exclusion_reason == "missing_fields"


async def test_loaded_powiat_is_staged_and_undelivered(session, persist):
    task = await persist(TaskFactory(status=TaskStatusEnum.cleaning))

    await load(session, task, assigned())

    await session.refresh(task)
    row = await session.scalar(select(StagedTransaction))
    assert task.status == TaskStatusEnum.done
    assert (row.run_id, row.delivered_at) == (task.run_id, None)


async def test_new_registry_version_updates_the_row(session, persist):
    task = await persist(TaskFactory(status=TaskStatusEnum.cleaning))

    await load(session, task, assigned())
    await load(session, task, assigned(tran_wersja_id="2019-01-01T00:00:00", lok_cena_brutto=1.0))

    row = await session.scalar(select(StagedTransaction))
    assert (row.source_version, float(row.price_premises)) == ("2019-01-01T00:00:00", 1.0)
