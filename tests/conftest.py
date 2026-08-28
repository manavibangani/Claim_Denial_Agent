import socket
from urllib.parse import urlparse

import pytest

from claim_agent import OLLAMA_BASE_URL


def _ollama_is_reachable():
    parsed = urlparse(OLLAMA_BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 11434
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def _skip_if_ollama_down():
    if not _ollama_is_reachable():
        pytest.skip(
            f"Ollama is not reachable at {OLLAMA_BASE_URL} - these tests call the "
            "real llama3 model and require `ollama serve` running locally with "
            "llama3 pulled (`ollama pull llama3`)."
        )
