from database.models.task_status import TaskStatusEnum
from database.repositories.property_transaction import StagedTransactionRepository
from polish_national_registry.territory_assignment import SourceTransactionDTO
from polish_national_registry.transaction_filter import TransactionFilterService
from polish_national_registry.transaction_load import TransactionLoadService

from .factories import TaskFactory
from .test_transaction_cleaning_and_load import SOURCE, assigned, clean

TRANSACTION = SourceTransactionDTO.from_row(SOURCE)


async def test_loaded_rows_are_known_on_the_next_run(session, persist):
    task = await persist(TaskFactory(status=TaskStatusEnum.staged))
    await TransactionLoadService.start_loading(
        session, task.id, "1465", task.run_id, clean(assigned())
    )

    known = await StagedTransactionRepository.get_versions(session, "1465")

    assert TransactionFilterService.new_only([TRANSACTION], known) == []
