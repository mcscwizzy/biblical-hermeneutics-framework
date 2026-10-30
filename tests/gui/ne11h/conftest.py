from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def enable_narrative_explorer_for_acceptance():
    previous = os.environ.get("BHF_NARRATIVE_EXPLORER_ENABLED")
    os.environ["BHF_NARRATIVE_EXPLORER_ENABLED"] = "1"
    yield
    if previous is None:
        os.environ.pop("BHF_NARRATIVE_EXPLORER_ENABLED", None)
    else:
        os.environ["BHF_NARRATIVE_EXPLORER_ENABLED"] = previous
