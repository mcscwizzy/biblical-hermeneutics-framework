"""Shared pipeline status metadata for the BHF runner."""

from __future__ import annotations


PIPELINE_STEPS: tuple[tuple[str, str], ...] = (
    ("queued", "Queued"),
    ("preparing_request", "Preparing request"),
    ("detecting_reference", "Detecting biblical reference"),
    ("classifying_genre", "Classifying genre"),
    ("classifying_question_type", "Classifying question type"),
    ("loading_profile", "Loading BHF profile"),
    ("checking_local_knowledge", "Checking local knowledge"),
    ("loading_session_memory", "Loading session memory"),
    ("building_prompt", "Building BHF prompt"),
    ("contacting_model_backend", "Contacting model backend"),
    ("waiting_for_model_response", "Waiting for model response"),
    ("model_response_received", "Model response received"),
    ("cleaning_output", "Cleaning model output"),
    ("validating_response", "Validating response"),
    ("formatting_answer", "Finalizing answer"),
    ("complete", "Complete"),
)

STEP_MESSAGES = dict(PIPELINE_STEPS)
STEP_INDEX = {stage: index + 1 for index, (stage, _message) in enumerate(PIPELINE_STEPS)}
TOTAL_STEPS = len(PIPELINE_STEPS)

STAGE_TO_STEP = {
    "initialize_context": "preparing_request",
    "detect_reference": "detecting_reference",
    "classify_genre": "classifying_genre",
    "classify_question_type": "classifying_question_type",
    "load_profile": "loading_profile",
    "lookup_local_knowledge": "checking_local_knowledge",
    "load_session_memory": "loading_session_memory",
    "build_prompts": "building_prompt",
    "call_model_start": "contacting_model_backend",
    "waiting_for_model": "waiting_for_model_response",
    "call_model_complete": "model_response_received",
    "clean_output": "cleaning_output",
    "validate_response": "validating_response",
    "repair_response": "validating_response",
    "finalize_result": "formatting_answer",
    "save_session_turn": "formatting_answer",
    "complete": "complete",
    "error": "error",
}
