"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path
import shutil

# Test directories
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_OUTPUTS_DIR = Path(__file__).parent / "outputs"


@pytest.fixture(scope="session", autouse=True)
def setup_test_dirs():
    """Create test directories if they don't exist."""
    TEST_DATA_DIR.mkdir(exist_ok=True)
    TEST_OUTPUTS_DIR.mkdir(exist_ok=True)
    yield


@pytest.fixture
def test_data_dir():
    """Provide path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def test_outputs_dir():
    """Provide path to test outputs directory."""
    return TEST_OUTPUTS_DIR


@pytest.fixture(autouse=True)
def reset_test_outputs():
    """Clean test outputs before each test."""
    if TEST_OUTPUTS_DIR.exists():
        for item in TEST_OUTPUTS_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    yield
