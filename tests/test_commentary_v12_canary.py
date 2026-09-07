"""Safety gates for the bounded Commentary v1.2 canary matrix."""

import pytest

from bhf_agent.config import AgentConfig
from tools.commentary_v12_canary import CANARY_REFERENCES, _require_terra_medium


def test_canary_matrix_contains_every_required_torture_case_and_data_gap_control():
    required = {
        ("Genesis", 1), ("Leviticus", 16), ("Ruth", 3), ("Psalms", 1),
        ("1 Samuel", 21), ("1 Samuel", 28), ("2 Samuel", 6), ("2 Samuel", 24),
        ("1 Chronicles", 8), ("John", 1), ("Isaiah", 6), ("Revelation", 12),
        ("Numbers", 3),
    }
    assert required.issubset(set(CANARY_REFERENCES))


def test_canary_refuses_unsupported_model_substitution(monkeypatch):
    monkeypatch.delenv("BHF_COMMENTARY_MODEL_OWNER", raising=False)
    monkeypatch.delenv("BHF_COMMENTARY_MODEL_EFFORT", raising=False)
    with pytest.raises(RuntimeError, match="Terra Medium"):
        _require_terra_medium(AgentConfig(model="llama3.1:8b"))


def test_canary_accepts_explicit_terra_medium_identity(monkeypatch):
    monkeypatch.setenv("BHF_COMMENTARY_MODEL_OWNER", "terra")
    monkeypatch.setenv("BHF_COMMENTARY_MODEL_EFFORT", "medium")
    _require_terra_medium(AgentConfig(model="gpt-5.6-terra"))
