"""Configuration des tests : base SQLite temporaire et isolée par session de test."""
import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolated_db():
    """Force une base et un journal jetables, et le mode 'none' (aucun appel IA réseau)."""
    tmp = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/test.db"
    os.environ["CONV_LOG_PATH"] = f"{tmp}/log.jsonl"
    os.environ["LLM_PROVIDER"] = "none"
    os.environ["CONVERSATION_LOG"] = "false"
    # (les modules lisent la config à l'import ; on la surcharge aussi en direct)
    import app.config as config
    config.DATABASE_URL = os.environ["DATABASE_URL"]
    config.CONV_LOG_PATH = os.environ["CONV_LOG_PATH"]
    config.LLM_PROVIDER = "none"
    config.CONVERSATION_LOG = False
    yield
