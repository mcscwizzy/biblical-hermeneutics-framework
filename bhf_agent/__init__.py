"""Reusable BHF AI Agent Core."""

from .config import AgentConfig
from .observability import ObservabilityConfig
from .map_tools import (
    build_map_tool_context,
    getArchaeologyForPassage,
    getArchaeologyForPlace,
    getHistoricalContextForPeriod,
    getPlaceDetails,
    getPlacesForPassage,
    getRelatedPassagesByPlace,
    getRoutesForPassage,
)


def __getattr__(name):
    """Load the runner lazily so standalone data services remain importable."""

    if name == "BHFAgent":
        from .runner import BHFAgent

        return BHFAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AgentConfig",
    "ObservabilityConfig",
    "BHFAgent",
    "build_map_tool_context",
    "getArchaeologyForPassage",
    "getArchaeologyForPlace",
    "getHistoricalContextForPeriod",
    "getPlaceDetails",
    "getPlacesForPassage",
    "getRelatedPassagesByPlace",
    "getRoutesForPassage",
]
