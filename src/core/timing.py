import logging
import time
from collections.abc import Generator
from contextlib import contextmanager

log = logging.getLogger(__name__)


@contextmanager
def timed(stage: str, **context: object) -> Generator[None]:
    """Log how long the block took, also when it raises."""

    started = time.perf_counter()
    ok = False
    try:
        yield
        ok = True
    finally:
        fields = "".join(f" {key}={value}" for key, value in context.items())
        log.info(
            "Stage for territory_code done stage=%s duration_s=%.3f ok=%s%s",
            stage,
            time.perf_counter() - started,
            "true" if ok else "false",
            fields,
        )
