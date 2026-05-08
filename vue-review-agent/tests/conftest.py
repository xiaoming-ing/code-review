import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def bad_vue_code() -> str:
    return (FIXTURES_DIR / "bad_component.vue").read_text()

@pytest.fixture
def good_vue_code() -> str:
    return (FIXTURES_DIR / "good_component.vue").read_text()