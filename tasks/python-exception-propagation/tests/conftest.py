from collections.abc import Callable

import pytest

from batch_command import ItemSpec


@pytest.fixture
def make_item() -> Callable[[str, str], ItemSpec]:
    def factory(name: str, mode: str) -> ItemSpec:
        return ItemSpec(name=name, mode=mode)  # type: ignore[arg-type]

    return factory


@pytest.fixture
def deterministic_failure_set() -> tuple[ItemSpec, ...]:
    return (
        ItemSpec("alpha", "ok"),
        ItemSpec("bravo", "unmatched"),
        ItemSpec("charlie", "sibling"),
    )
