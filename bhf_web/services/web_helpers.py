"""Route-adjacent helpers used by the FastAPI app."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from fastapi import Request

from bhf_agent.bible import BibleError, compare_translation_passages, build_selected_passage_context, geography_for_book, testament_for_book, timeline_for_book, verse_range_reference
from bhf_agent.curation import CURATION_COLLECTIONS, list_curation_records
from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileLoader
from bhf_agent.runner import BHFAgent
from bhf_agent.study_db import StudyDataError, record_study_action
from ..forms import validate_question, config_from_form, load_web_defaults


def timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def failed_stage(entry: Any) -> str | None:
    details = getattr(entry, "details", None)
    if not isinstance(details, dict):
        return None
    value = details.get("failed_stage")
    return str(value) if value else None


async def request_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            return payload
        raise StudyDataError("JSON body must be an object")
    form = await request.form()
    return dict(form)


def record_action(action_type: str, data: dict[str, Any], path: str | Path) -> None:
    try:
        record_study_action(action_type, data, path=path)
    except StudyDataError:
        return


def saved_study_payload_from_request(payload: dict[str, Any], job_store: Any = None) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "").strip()
    if job_id:
        job = job_store.get(job_id) if job_store else None
        if job is None:
            raise StudyDataError("job not found")
        if not job.done:
            raise StudyDataError("job is not complete")
        if job.error:
            raise StudyDataError("cannot save a failed study")
        if job.result is None:
            raise StudyDataError("job result is not available")
        if not job.study_context:
            raise StudyDataError("study context is not available")
        return {
            "title": payload.get("title"),
            "book": job.study_context["book"],
            "chapter": job.study_context["chapter"],
            "start_verse": job.study_context["start_verse"],
            "end_verse": job.study_context["end_verse"],
            "selected_text": job.study_context["selected_text"],
            "study_type": job.study_type or "question",
            "question": job.question or "",
            "answer": getattr(job.result, "answer_text", ""),
        }

    return {
        "title": payload.get("title"),
        "book": payload.get("book"),
        "chapter": payload.get("chapter"),
        "start_verse": payload.get("start_verse") or payload.get("verse_start"),
        "end_verse": payload.get("end_verse") or payload.get("verse_end"),
        "selected_text": payload.get("selected_text"),
        "study_type": payload.get("study_type") or payload.get("ask_mode"),
        "question": payload.get("question"),
        "answer": payload.get("answer") or payload.get("answer_html"),
    }


def map_study_payload_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    view_state = payload.get("map_view_state") or {}
    selected_layers = payload.get("selected_layers") or []
    if isinstance(selected_layers, str):
        try:
            selected_layers = json.loads(selected_layers)
        except json.JSONDecodeError:
            selected_layers = [selected_layers]
    if isinstance(view_state, str):
        try:
            view_state = json.loads(view_state)
        except json.JSONDecodeError:
            view_state = {}
    return {
        "book": payload.get("book"),
        "chapter": payload.get("chapter"),
        "start_verse": payload.get("start_verse") or payload.get("verse_start"),
        "end_verse": payload.get("end_verse") or payload.get("verse_end"),
        "passage_reference": payload.get("passage_reference"),
        "selected_place_id": payload.get("selected_place_id"),
        "selected_route_id": payload.get("selected_route_id"),
        "selected_layer_id": payload.get("selected_layer_id"),
        "selected_archaeology_id": payload.get("selected_archaeology_id"),
        "selected_layers": selected_layers,
        "map_view_state": view_state,
        "generated_summary": payload.get("generated_summary"),
        "user_notes": payload.get("user_notes"),
    }


def map_note_payload_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "book": payload.get("book"),
        "chapter": payload.get("chapter"),
        "start_verse": payload.get("start_verse") or payload.get("verse_start"),
        "end_verse": payload.get("end_verse") or payload.get("verse_end"),
        "passage_reference": payload.get("passage_reference"),
        "place_id": payload.get("place_id"),
        "route_id": payload.get("route_id"),
        "layer_id": payload.get("layer_id"),
        "archaeology_id": payload.get("archaeology_id"),
        "note_body": payload.get("note_body") or payload.get("body"),
    }


def job_error_message(job: Any) -> str:
    if getattr(job, "failed_stage", None):
        return f"{job.error} (failed during {str(job.failed_stage).replace('_', ' ')})"
    return getattr(job, "error", None) or "Request failed."


def result_metadata(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "model_metadata", {}) or {}
    validation = getattr(result, "validation_result", None)
    reference = getattr(result, "reference_context", None)
    genre = getattr(result, "genre_context", None)
    question = getattr(result, "question_context", None)

    return {
        "Profile used": getattr(result, "profile_used", "not available"),
        "Answer mode": metadata.get("answer_mode") or "not available",
        "Detected reference": format_reference(reference),
        "Detected genre": getattr(genre, "primary_genre", None) or "not detected",
        "Question type": format_question_type(question),
        "Local knowledge used": join_or_none(metadata.get("local_knowledge_keys") or []),
        "Validation warnings": join_or_none(getattr(validation, "warnings", [])),
        "Adapter errors": join_or_none(getattr(result, "errors", [])),
    }


def render_safe_markdown(text: str) -> str:
    if not text.strip():
        return "<p><em>No answer returned.</em></p>"

    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_list()
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            list_items.append(f"<li>{inline_markdown(bullet.group(1))}</li>")
            continue

        flush_list()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
        else:
            blocks.append(f"<p>{inline_markdown(stripped)}</p>")

    flush_list()
    return "\n".join(blocks)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text, quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def available_profiles(selected: str) -> list[str]:
    profiles = ProfileLoader().available_profiles()
    if selected and selected not in profiles:
        profiles.append(selected)
    return sorted(profiles)


def format_reference(reference: Any) -> str:
    if reference is None:
        return "not detected"
    if not getattr(reference, "is_reference_based", False):
        return f"topic-only ({getattr(reference, 'topic', None) or 'not detected'})"
    location = getattr(reference, "book", None) or "unknown"
    chapter = getattr(reference, "chapter", None)
    verse = getattr(reference, "verse", None)
    testament = getattr(reference, "testament", None)
    if chapter is not None:
        location += f" {chapter}"
    if verse is not None:
        location += f":{verse}"
    if testament:
        location += f" [{testament}]"
    return location


def format_question_type(question: Any) -> str:
    if question is None:
        return "not detected"
    value = getattr(question, "question_type", None) or "not detected"
    language = getattr(question, "target_language", None)
    if language:
        value += f" [{language}]"
    return value


def join_or_none(values: list[str]) -> str:
    return ", ".join(str(value) for value in values if value) or "none"


def curations_template_sections(path: str | Path) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for spec in CURATION_COLLECTIONS.values():
        records = list_curation_records(spec.key, path=path)
        sections.append(
            {
                "key": spec.key,
                "title": spec.title,
                "count": len(records),
                "summary_fields": spec.summary_fields,
                "records": [
                    {
                        "id": record.get("id", ""),
                        "summary": curation_record_summary(record, spec.summary_fields),
                        "source_summary": record.get("source_summary", "Missing source metadata"),
                        "missing_source": "Missing source metadata" in str(record.get("source_summary", "")),
                        "json": json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                    }
                    for record in records
                ],
                "new_record_json": json.dumps(
                    curation_blank_record(spec), indent=2, sort_keys=True, ensure_ascii=False
                ),
            }
        )
    return sections


def curation_record_summary(record: dict[str, Any], fields: tuple[str, ...]) -> str:
    values = [str(record.get(field) or "").strip() for field in fields]
    values = [value for value in values if value]
    if values:
        return " · ".join(values)
    if record.get("id"):
        return str(record["id"])
    return "Record"


def curation_blank_record(spec: Any) -> dict[str, Any]:
    blank: dict[str, Any] = {}
    for field in spec.fields:
        if field.name == "id":
            blank[field.name] = ""
        elif field.kind == "json_list":
            blank[field.name] = []
        elif field.kind == "json_object":
            blank[field.name] = {}
        elif field.kind == "int":
            blank[field.name] = 0
        elif field.kind == "float":
            blank[field.name] = None
        else:
            blank[field.name] = ""
    return blank


def build_ask_question(
    form: dict[str, Any] | Any,
    *,
    path: str | Path | None = None,
) -> tuple[str, str | None]:
    if not is_reader_submission(form):
        return validate_question(form), None

    ask_mode = str(form.get("ask_mode") or "").strip()
    context = reader_context_from_form(form)
    if context is None:
        return validate_question(form), None
    study_action = str(form.get("study_action") or "").strip()
    if study_action:
        if path is not None:
            record_action(study_action, context, path=path)
    if ask_mode == "ancient_context":
        return ancient_context_question(form, context), str(context["reference"])
    if ask_mode == "literary_context":
        return literary_context_question(form, context), str(context["reference"])
    if ask_mode == "cross_references":
        return cross_references_question(form, context), str(context["reference"])
    if ask_mode == "related_ot_themes":
        return related_ot_themes_question(form, context), str(context["reference"])
    if ask_mode == "fulfillment_nt":
        return fulfillment_nt_question(form, context), str(context["reference"])
    if ask_mode == "compare_translations":
        return compare_translations_question(form, context), str(context["reference"])
    if ask_mode == "timeline":
        return timeline_question(form, context), str(context["reference"])
    if ask_mode == "maps":
        return maps_question(form, context), str(context["reference"])
    if ask_mode == "word_study":
        return word_study_question(form, context), str(context["reference"])
    user_question = str(form.get("question") or "").strip()
    if not user_question:
        user_question = f"Explain {context['reference']} using BHF."
    lines = [
        f"Using BHF, explain ASV {context['reference']}.",
        f"User question: {user_question}",
        "",
        f"Selected text (ASV {context['reference']}):",
        context["selected_text"],
    ]
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Method reminder: observe the text before interpreting it, and apply only after observation and interpretation."])
    return "\n".join(lines), str(context["reference"])


def is_reader_submission(form: dict[str, Any] | Any) -> bool:
    return bool(str(form.get("reader_book") or "").strip()) and bool(str(form.get("reader_chapter") or "").strip())


def reader_context_from_form(form: dict[str, Any] | Any) -> dict[str, Any] | None:
    if not is_reader_submission(form):
        return None
    return build_selected_passage_context(
        str(form.get("reader_book") or ""),
        str(form.get("reader_chapter") or ""),
        optional_form_value(form, "reader_start_verse"),
        optional_form_value(form, "reader_end_verse"),
        optional_form_value(form, "reader_selected_text"),
        include_chapter_context=True,
    )


def study_type_from_form(form: dict[str, Any] | Any) -> str:
    ask_mode = str(form.get("ask_mode") or "").strip()
    if ask_mode:
        return ask_mode
    if is_reader_submission(form):
        return "question"
    return "general_question"


def optional_form_value(form: dict[str, Any] | Any, name: str) -> str | None:
    value = str(form.get(name) or "").strip()
    return value or None


def ancient_context_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    background = (
        "Ancient Near Eastern context, covenant setting, and Israel's original audience concerns"
        if testament == "Old Testament"
        else "Second Temple Jewish and Greco-Roman context where relevant, including the original audience's concerns"
    )
    lines = [f"Using BHF, explain the ancient context of ASV {context['reference']}.", f"Testament context: {testament}. Use {background}."]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", "Focus on the passage's ancient setting, original audience, cultural background, and covenant setting when relevant.", "Avoid modern assumptions and anachronistic readings.", "Clearly distinguish background that is certain from background that is probable or debated.", "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observe first, interpret with genre and original audience in view, and reserve application until after interpretation."])
    return "\n".join(lines)


def literary_context_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    lines = [f"Using BHF, explain the literary context of ASV {context['reference']}."]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", "Explain how the selected passage functions within the immediate paragraph, chapter, book, genre, and argument or narrative flow.", "Emphasize what comes before and after the selected passage.", "Avoid isolating the verse from the surrounding passage.", "Include genre awareness and explain how genre shapes interpretation.", "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observe the literary flow before interpreting, and apply only after interpretation."])
    return "\n".join(lines)


def cross_references_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    lines = [f"Using BHF, give cross references for ASV {context['reference']}.", f"Testament context: {testament}. Prioritize direct quotations, clear allusions, repeated phrases, canonical themes, and OT/NT connections when relevant."]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", "Separate strong references from possible references.", "Briefly explain why each reference matters.", "Do not dump a huge list.", "Avoid speculative links and label uncertainty clearly.", "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observation first, then interpretation, then application only if useful."])
    return "\n".join(lines)


def related_ot_themes_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    lines = [f"Using BHF, identify related Old Testament themes for ASV {context['reference']}.", f"Testament context: {testament}. Especially important for New Testament passages, but still note canonical patterns carefully."]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", "Include themes such as covenant, temple, exile/restoration, creation/new creation, wisdom, kingship, priesthood, sacrifice, Spirit, land, blessing/curse, and other earlier canonical patterns when they are genuinely relevant.", "Clearly mark strong versus possible thematic links.", "Avoid speculative connections.", "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observe the text, interpret within genre and audience, and distinguish strong links from possible ones."])
    return "\n".join(lines)


def fulfillment_nt_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    lines = [f"Using BHF, evaluate fulfillment in the NT for ASV {context['reference']}.", f"Testament context: {testament}. Do not force a fulfillment reading where the text does not support it."]
    if user_question:
        lines.append(f"User question: {user_question}")
    if testament == "Old Testament":
        lines.extend(["", "Assess whether the passage is quoted, echoed, developed, fulfilled, typologically reused, or thematically carried into the New Testament.", "Separate direct NT citation from strong allusion, typological pattern, thematic development, and speculative or weak connection.", "State clearly when the NT does not make or imply a connection."])
    else:
        lines.extend(["", "For a New Testament passage, explain how it may fulfill or develop earlier Old Testament themes instead of forcing a direct prophetic fulfillment.", "Separate direct OT citation from strong allusion, typological pattern, thematic development, and speculative or weak connection.", "State clearly when the passage is not directly tied to a specific Old Testament text."])
    lines.extend(["", "Avoid forcing Christological or prophetic readings where unsupported.", "Distinguish clear fulfillment from possible thematic resonance.", "Briefly explain why each link matters.", "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observe the text first, interpret in literary and canonical context, and keep uncertainty explicit."])
    return "\n".join(lines)


def compare_translations_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    comparison = compare_translation_passages(str(context["book"]), int(context["chapter"]), context.get("start_verse"), context.get("end_verse"))
    translation_names = ", ".join(f"{item['id']} ({item['name']})" for item in comparison["translations"])
    lines = [f"Using BHF, compare the local public-domain translations for ASV {comparison['reference']}.", f"Available translations: {translation_names}. Use only the bundled local texts.", "Explain wording differences and how they may affect interpretation.", "Do not rely on copyrighted Bible APIs.", "Do not overstate the significance of minor wording differences.", "Separate clear interpretive differences from stylistic variation."]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.append("")
    lines.append("Comparison data by verse:")
    for row in comparison["verse_rows"]:
        lines.append(f"Verse {row['verse']}:")
        for translation in comparison["translations"]:
            text = row["texts"].get(translation["id"], "")
            lines.append(f"- {translation['id']}: {text}")
        lines.append("")
    if context.get("chapter_context"):
        lines.extend([f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"]), ""])
    lines.extend([f"Selected text (ASV {context['reference']}):", context["selected_text"], "", "Use BHF method: observe the wording first, interpret in literary and canonical context, and keep uncertainty explicit."])
    return "\n".join(lines)


def timeline_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    guide = timeline_for_book(str(context["book"]))
    testament = testament_for_book(str(context["book"]))
    lines = [f"Using BHF, place ASV {context['reference']} on the biblical timeline.", f"Testament context: {testament}. Broad period: {guide['period']}."]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", "Show where the passage fits in biblical history, the major covenant period, and the relation to surrounding biblical events.", "Prefer broad historical placement over fake precision.", "If exact dating is uncertain, say so plainly.", guide["notes"], "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observe first, interpret in literary and canonical context, and keep chronological claims broad and careful."])
    return "\n".join(lines)


def maps_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    guide = geography_for_book(str(context["book"]))
    testament = testament_for_book(str(context["book"]))
    map_context = optional_map_context(form)
    lines = [f"Using BHF, give geography notes for ASV {context['reference']}.", f"Testament context: {testament}. Broad region: {guide['region']}."]
    if map_context:
        lines.extend(["", "Structured map context retrieved from the local map layer:", map_context])
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", "Identify places named or implied in the passage and keep the result text-based for now.", "Mention when a place's exact location is debated.", "Do not invent locations if uncertain.", "Keep this as a geography helper until real map data is added.", guide["notes"], "", f"Selected text (ASV {context['reference']}):", context["selected_text"]])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: observe the passage first, then note geography that is explicit, probable, or uncertain."])
    return "\n".join(lines)


def word_study_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    selected_text = context["selected_text"]
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    source_language = "Hebrew" if testament == "Old Testament" else "Greek"
    lines = [f"Using BHF, provide a cautious word study helper for ASV {context['reference']}.", f"The selected word or phrase is from the ASV English text: {selected_text}"]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(["", f"Testament context: {testament}. Discuss possible {source_language} terms only as possibilities.", "The selected word is from the ASV English text.", "Do not claim exact Hebrew/Greek alignment unless the app has source-language data.", "Do not invent Strong's numbers.", "Offer likely Hebrew or Greek terms only as possibilities, with uncertainty.", "Recommend checking an actual lexicon/interlinear for confirmation.", "Explain semantic range, usage, and context cautiously.", "", f"Selected text (ASV {context['reference']}):", selected_text])
    if context.get("chapter_context"):
        lines.extend(["", f"Full chapter context (ASV {context['book']} {context['chapter']}):", str(context["chapter_context"])])
    lines.extend(["", "Use BHF method: original audience, literary context, genre awareness, intertextuality when relevant, theological caution, and application only after interpretation."])
    return "\n".join(lines)


def optional_map_context(form: dict[str, Any] | Any) -> str | None:
    value = str(form.get("map_context") or "").strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    parts: list[str] = []
    for key in ("selected_place_name", "selected_route_name", "selected_layer_name", "passage_reference", "confidence", "modern_location", "ancient_region", "local_map_summary"):
        item = parsed.get(key)
        if item:
            parts.append(f"{key.replace('_', ' ').title()}: {item}")
    if not parts:
        return None
    return "\n".join(f"- {part}" for part in parts)
