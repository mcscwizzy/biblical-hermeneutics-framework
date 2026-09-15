"""BHF chapter commentary generation system."""

from .builder import CommentaryBuilder
from .generator import CommentaryGenerator
from .models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION,
    COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    CommentaryBlock,
    CommentaryGenerationRequest,
    CommentaryGenerationResult,
    CommentaryProgress,
    CommentarySectionKind,
    CommentaryStatus,
    ExternalCommentaryResponse,
)
from .storage import (
    delete_commentary,
    load_commentary,
    save_commentary,
)
from .validation import (
    CommentaryRejectionCode,
    validate_chapter_commentary,
)
from .evidence_applicability import (
    COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
    EvidenceApplicability,
    commentary_eligible_evidence,
    evaluate_evidence_applicability,
)
from .synthesis import (
    SYNTHESIS_COMPILER_VERSION,
    SYNTHESIS_SCHEMA_VERSION,
    CompiledChapterSynthesis,
    SynthesisUnit,
    compile_chapter_synthesis,
    validate_synthesis,
)

__all__ = [
    "COMMENTARY_PROMPT_VERSION",
    "COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION",
    "COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION",
    "COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION",
    "COMMENTARY_SCHEMA_VERSION",
    "ChapterCommentary",
    "CommentaryBlock",
    "CommentaryBuilder",
    "CommentaryGenerationRequest",
    "CommentaryGenerationResult",
    "CommentaryGenerator",
    "CommentaryProgress",
    "CommentarySectionKind",
    "CommentaryStatus",
    "ExternalCommentaryResponse",
    "CommentaryRejectionCode",
    "delete_commentary",
    "load_commentary",
    "save_commentary",
    "validate_chapter_commentary",
    "COMMENTARY_EVIDENCE_APPLICABILITY_VERSION",
    "EvidenceApplicability",
    "commentary_eligible_evidence",
    "evaluate_evidence_applicability",
    "SYNTHESIS_COMPILER_VERSION",
    "SYNTHESIS_SCHEMA_VERSION",
    "CompiledChapterSynthesis",
    "SynthesisUnit",
    "compile_chapter_synthesis",
    "validate_synthesis",
]
