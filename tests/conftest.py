from pathlib import Path

import pytest

from stores.vector_store import reset_vector_stores

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TXT = ROOT / "data" / "sample_contracts" / "sample_contract.txt"


@pytest.fixture(autouse=True)
def _clean_stores() -> None:
    reset_vector_stores()
    yield
    reset_vector_stores()


@pytest.fixture
def sample_txt() -> Path:
    return SAMPLE_TXT
