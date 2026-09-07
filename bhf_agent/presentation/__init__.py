"""Exploration-first, evidence-grounded contextual presentation."""

from .cache import (
    MemoryPresentationCache,
    PresentationCache,
    SQLitePresentationCache,
    default_presentation_cache_path,
    presentation_cache_key,
    presentation_cache_key_for_versions,
)
from .bundles import (
    PRESENTATION_BUNDLE_FORMAT,
    PRESENTATION_BUNDLE_VERSION,
    PresentationBundleError,
    build_presentation_bundle,
    index_presentation_bundle,
    load_presentation_bundle,
)
from .bundle_export import (
    PresentationBundleExportError,
    PresentationBundleExportResult,
    export_cached_presentations,
)
from .bundle_inspection import (
    PresentationBundleInspection,
    inspect_presentation_bundle,
)
from .engine import PresentationEngine, PresentationResult
from .evidence import build_evidence_bundle
from .evaluation import evaluate_presentation_case
from .evaluation_models import (
    PresentationEvalCaseResult,
    PresentationEvalCheck,
    PresentationEvalSuiteResult,
)
from .evaluation_suite import (
    evaluate_presentation_fixtures,
    format_presentation_eval,
    load_presentation_fixtures,
)
from .fallback import deterministic_presentation
from .models import (
    EVIDENCE_BUNDLE_VERSION,
    EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    PRESENTATION_SCHEMA_VERSION,
    DigDeeperAction,
    EntityRef,
    EvidenceBundle,
    EvidenceItem,
    GeneratedFrom,
    PresentationCard,
    PresentationPacket,
)
from .providers import (
    AdapterPresentationProvider,
    PresentationProvider,
    PresentationResponseParseError,
    parse_presentation_json_response,
)
from .ranking import RankedEvidence, rank_evidence
from .validation import (
    GeneratedMetadataValidationResult,
    PresentationCardValidationResult,
    PresentationRejectionCode,
    PresentationValidationResult,
    validate_generated_metadata,
    validate_presentation_card,
    validate_presentation_packet,
)
from .walk_the_land import build_walk_the_land_card
from .why_it_matters import build_why_it_matters_card

__all__ = [
    "AdapterPresentationProvider",
    "DigDeeperAction",
    "EVIDENCE_BUNDLE_VERSION",
    "EVIDENCE_BUNDLE_CANDIDATE_VERSION",
    "EntityRef",
    "EvidenceBundle",
    "EvidenceItem",
    "GeneratedFrom",
    "MemoryPresentationCache",
    "PRESENTATION_SCHEMA_VERSION",
    "PRESENTATION_BUNDLE_FORMAT",
    "PRESENTATION_BUNDLE_VERSION",
    "PresentationCache",
    "PresentationBundleError",
    "PresentationBundleExportError",
    "PresentationBundleExportResult",
    "PresentationBundleInspection",
    "PresentationCardValidationResult",
    "PresentationCard",
    "PresentationEngine",
    "PresentationEvalCaseResult",
    "PresentationEvalCheck",
    "PresentationEvalSuiteResult",
    "PresentationPacket",
    "PresentationProvider",
    "PresentationRejectionCode",
    "PresentationResponseParseError",
    "PresentationResult",
    "PresentationValidationResult",
    "GeneratedMetadataValidationResult",
    "RankedEvidence",
    "SQLitePresentationCache",
    "build_evidence_bundle",
    "build_presentation_bundle",
    "build_walk_the_land_card",
    "build_why_it_matters_card",
    "deterministic_presentation",
    "default_presentation_cache_path",
    "evaluate_presentation_case",
    "evaluate_presentation_fixtures",
    "format_presentation_eval",
    "export_cached_presentations",
    "index_presentation_bundle",
    "inspect_presentation_bundle",
    "load_presentation_fixtures",
    "load_presentation_bundle",
    "presentation_cache_key",
    "presentation_cache_key_for_versions",
    "parse_presentation_json_response",
    "rank_evidence",
    "validate_presentation_packet",
    "validate_generated_metadata",
    "validate_presentation_card",
]
