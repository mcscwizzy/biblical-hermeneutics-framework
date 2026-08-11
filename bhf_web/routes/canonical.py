"""Canonical library browser route registration for the FastAPI app."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from bhf_agent.ckl import build_canonical_context, load_canonical_library
from bhf_agent.archaeology_service import ArchaeologyService
import bhf_agent.ckl as ckl_module
from framework.canonical_library.authoring import write_json_file
from framework.canonical_library.normalization import normalize_id
from framework.canonical_library.schema import CanonicalValidationError, validate_object


@lru_cache(maxsize=1)
def _canonical_library():
    return load_canonical_library()


def register_canonical_routes(app: FastAPI, *, study_db_path: str | None = None) -> None:
    archaeology = ArchaeologyService(study_db_path) if study_db_path else ArchaeologyService()

    @app.get("/api/canonical/entities-for-passage", response_class=JSONResponse)
    async def canonical_entities_for_passage(
        book: str,
        chapter: int,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        limit: int = 12,
    ) -> JSONResponse:
        """Return compact, deterministic entity availability without full CKL retrieval."""

        results = _entities_for_passage(
            _canonical_library(),
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            passage_text=passage_text,
            limit=max(1, min(int(limit), 25)),
        )
        return JSONResponse({
            "reference": _format_passage_reference(book, chapter, verse_start, verse_end),
            "results": results,
            "result_count": len(results),
        })

    @app.get("/api/canonical/search", response_class=JSONResponse)
    async def canonical_search(
        q: str | None = None,
        limit: int = 12,
        object_type: str | None = Query(default=None, alias="type"),
        review_status: str | None = None,
        content_status: str | None = None,
        include_placeholders: bool = True,
    ) -> JSONResponse:
        library = _canonical_library()
        normalized_query = str(q or "").strip()
        results: list[dict[str, Any]]
        metadata: dict[str, Any]

        if normalized_query:
            context = build_canonical_context(
                library,
                normalized_query,
                max_results=max(1, min(int(limit), 25)),
                include_placeholders=include_placeholders,
                answer_mode="study",
            )
            retrieved_topics = list(context.get("retrieved_topics") or []) if context else []
            results = [
                _with_related_archaeology(
                    _serialize_topic(topic, library, browse=False),
                    archaeology,
                    include_media=False,
                )
                for topic in retrieved_topics
                if _topic_matches_filters(topic, object_type, review_status, content_status)
            ]
            metadata = dict(context.get("metadata") or {}) if context else {}
        else:
            results = [
                _with_related_archaeology(result, archaeology, include_media=False)
                for result in _browse_topics(
                library,
                limit=max(1, min(int(limit), 25)),
                object_type=object_type,
                review_status=review_status,
                content_status=content_status,
                include_placeholders=include_placeholders,
            )]
            metadata = {
                "retrieval_method": "browse",
                "topic_count": len(results),
                "query": "",
                "max_results": limit,
                "include_placeholders": include_placeholders,
                "allowed_statuses": None,
            }

        if object_type or review_status or content_status:
            metadata["filters"] = {
                "type": object_type or "all",
                "review_status": review_status or "all",
                "content_status": content_status or "all",
            }

        return JSONResponse(
            {
                "query": normalized_query,
                "limit": limit,
                "filters": {
                    "type": object_type or "all",
                    "review_status": review_status or "all",
                    "content_status": content_status or "all",
                    "include_placeholders": include_placeholders,
                },
                "metadata": metadata,
                "results": results,
            }
        )

    @app.get("/api/canonical/objects/{object_id}", response_class=JSONResponse)
    async def canonical_object(object_id: str) -> JSONResponse:
        library = _canonical_library()
        normalized_id = normalize_id(object_id)
        obj = library.objects_by_id.get(normalized_id)
        if obj is None:
            return JSONResponse({"error": "canonical object not found"}, status_code=404)
        # Draft archaeology compatibility records remain directly inspectable
        # by the CKL editor until curation is complete. Completed records defer
        # to the authoritative archaeology domain.
        if obj.type == "archaeology" and obj.content_status != "placeholder":
            try:
                item = archaeology.get_item(normalized_id)
            except Exception:
                item = None
            if item is not None:
                return JSONResponse(
                    {
                        "id": normalized_id,
                        "type": "archaeology_compatibility",
                        "status": "deprecated",
                        "replacement": {"domain": "archaeology", "id": normalized_id},
                        "message": "This legacy CKL archaeology record is a compatibility link. Archaeology is authoritative.",
                        "archaeology": item,
                    }
                )
        return JSONResponse(_with_related_archaeology(_serialize_object_detail(obj, library), archaeology))


def register_canonical_editor_routes(app: FastAPI, *, templates: Any) -> None:
    @app.get("/canonical/editor", response_class=HTMLResponse)
    async def canonical_editor(
        request: Request,
        object_id: str | None = None,
        saved: str | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        library = _canonical_library()
        draft_objects = _editor_candidates(library)
        selected = _select_editor_object(library, draft_objects, object_id)
        if object_id and selected is None:
            return templates.TemplateResponse(
                request,
                "canonical_editor.html",
                {
                    "draft_objects": draft_objects,
                    "selected_object": None,
                    "selected_object_json": "",
                    "selected_object_path": "",
                    "saved": False,
                    "error": f"canonical object '{object_id}' was not found",
                },
                status_code=404,
            )
        selected_payload = selected.to_dict() if selected is not None else None
        selected_source_path = library.source_path_for(selected.id) if selected is not None else None
        return templates.TemplateResponse(
            request,
            "canonical_editor.html",
            {
                "draft_objects": draft_objects,
                "selected_object": selected_payload,
                "selected_object_json": _selected_object_json(selected_payload),
                "selected_object_path": str(selected_source_path) if selected_source_path is not None else "",
                "saved": bool(saved),
                "error": error,
            },
        )

    @app.post("/canonical/editor/{object_id}", response_class=HTMLResponse)
    async def save_canonical_editor_object(request: Request, object_id: str) -> Response:
        library = _canonical_library()
        source_path = library.source_path_for(object_id)
        if source_path is None:
            return templates.TemplateResponse(
                request,
                "canonical_editor.html",
                {
                    "draft_objects": _editor_candidates(library),
                    "selected_object": None,
                    "selected_object_json": "",
                    "selected_object_path": "",
                    "saved": False,
                    "error": f"canonical object '{object_id}' was not found",
                },
                status_code=404,
            )

        form = await request.form()
        raw_json = str(form.get("record_json") or "").strip()
        try:
            payload = json.loads(raw_json)
            if not isinstance(payload, dict):
                raise ValueError("canonical object JSON must be an object")
            validated = validate_object(payload, path=source_path)
        except (json.JSONDecodeError, CanonicalValidationError, ValueError) as exc:
            selected_payload = None
            try:
                selected_payload = json.loads(raw_json) if raw_json else None
            except Exception:  # noqa: BLE001 - preserve invalid JSON for the editor
                selected_payload = None
            return templates.TemplateResponse(
                request,
                "canonical_editor.html",
                {
                    "draft_objects": _editor_candidates(library),
                    "selected_object": selected_payload if isinstance(selected_payload, dict) else None,
                    "selected_object_json": raw_json,
                    "selected_object_path": str(source_path),
                    "saved": False,
                    "error": str(exc),
                },
                status_code=400,
            )

        write_json_file(source_path, validated.to_dict())
        _canonical_library.cache_clear()
        if hasattr(ckl_module, "_load_default_canonical_library"):
            try:
                ckl_module._load_default_canonical_library.cache_clear()
            except AttributeError:
                pass
        companion_context = getattr(request.app.state, "companion_context_service", None)
        invalidate_companion = getattr(companion_context, "invalidate_canonical_cache", None)
        if callable(invalidate_companion):
            invalidate_companion()
        return RedirectResponse(
            url=f"/canonical/editor?object_id={validated.id}&saved=1",
            status_code=303,
        )


def _browse_topics(
    library: Any,
    *,
    limit: int,
    object_type: str | None,
    review_status: str | None,
    content_status: str | None,
    include_placeholders: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for obj in sorted(
        library.objects_by_id.values(),
        key=lambda item: (-int(item.importance), item.type, item.title, item.id),
    ):
        if not _object_matches_filters(
            obj,
            object_type,
            review_status,
            content_status,
            include_placeholders=include_placeholders,
        ):
            continue
        results.append(_serialize_object_detail(obj, library, browse=True))
        if len(results) >= limit:
            break
    return results


def _editor_candidates(library: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for obj in sorted(
        library.objects_by_id.values(),
        key=lambda item: (
            _editor_content_status_rank(str(getattr(item, "content_status", ""))),
            _editor_review_status_rank(str(getattr(item, "review_status", ""))),
            item.type,
            item.title,
            item.id,
        ),
    ):
        if obj.content_status not in {"placeholder", "draft"} and obj.review_status == "approved":
            continue
        candidates.append(
            {
                "id": obj.id,
                "title": obj.title,
                "type": obj.type,
                "content_status": obj.content_status,
                "review_status": obj.review_status,
                "confidence": obj.confidence,
                "summary": obj.summary,
            }
        )
    return candidates


def _editor_content_status_rank(status: str) -> int:
    order = {"placeholder": 0, "draft": 1, "complete": 2}
    return order.get(status, 3)


def _editor_review_status_rank(status: str) -> int:
    order = {"unreviewed": 0, "in_review": 1, "approved": 2, "deprecated": 3}
    return order.get(status, 4)


def _select_editor_object(library: Any, candidates: list[dict[str, Any]], object_id: str | None) -> Any:
    normalized_id = normalize_id(object_id or "")
    if normalized_id:
        return library.objects_by_id.get(normalized_id)
    first_candidate = candidates[0]["id"] if candidates else ""
    return library.objects_by_id.get(first_candidate) if first_candidate else None


def _selected_object_json(selected_payload: dict[str, Any] | None) -> str:
    if selected_payload is None:
        return ""
    return json.dumps(selected_payload, indent=2, ensure_ascii=False) + "\n"


def _serialize_object_detail(obj: Any, library: Any, *, browse: bool = False) -> dict[str, Any]:
    payload = _serialize_object(obj)
    payload["reason"] = (
        f"Browse result ranked by importance {obj.importance}."
        if browse
        else "Direct object lookup."
    )
    payload["match_type"] = "browse" if browse else "id"
    payload["matched_terms"] = []
    payload["matched_fields"] = []
    payload["matched_alias"] = None
    payload["score"] = float(obj.importance) / 100 if browse else 1.0
    payload["source_count"] = len(payload["sources"])
    payload["scripture_reference_count"] = len(payload["scripture_references"])
    payload["related_object_count"] = len(payload["related_objects"])
    payload["related_object_links"] = _serialize_related_object_links(obj, library)
    payload["browse_url"] = f"/curation?collection={obj.type}"
    return payload


def _serialize_topic(topic: dict[str, Any], library: Any, *, browse: bool) -> dict[str, Any]:
    object_id = str(topic.get("id") or "").strip()
    obj = library.objects_by_id.get(object_id)
    if obj is None:
        return dict(topic)
    payload = _serialize_object(obj)
    payload.update(
        {
            "reason": _topic_reason(topic),
            "match_type": str(topic.get("match_type") or "keyword"),
            "matched_terms": list(topic.get("matched_terms") or []),
            "matched_fields": list(topic.get("matched_fields") or []),
            "matched_alias": topic.get("matched_alias"),
            "score": float(topic.get("score") or 0.0),
            "inclusion_type": topic.get("inclusion_type"),
            "included_from": topic.get("included_from"),
            "relationship": topic.get("relationship"),
            "relationship_weight": topic.get("relationship_weight"),
            "relationship_depth": topic.get("relationship_depth"),
            "estimated_tokens": topic.get("estimated_tokens"),
            "source_count": len(payload["sources"]),
            "scripture_reference_count": len(payload["scripture_references"]),
            "related_object_count": len(payload["related_objects"]),
            "related_object_links": _serialize_related_object_links(obj, library),
            "browse_url": f"/curation?collection={obj.type}",
        }
    )
    if browse:
        payload["reason"] = f"Browse result ranked by importance {obj.importance}."
        payload["match_type"] = "browse"
    return payload


def _entities_for_passage(
    library: Any,
    *,
    book: str,
    chapter: int,
    verse_start: int | None,
    verse_end: int | None,
    passage_text: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Rank direct entity mentions and Scripture anchors using compact local data."""

    normalized_text = " ".join(str(passage_text or "").casefold().split())
    indexed_lookup = getattr(library, "retrieve_by_scripture_reference", None)
    if callable(indexed_lookup):
        reference = _format_passage_reference(book, chapter, verse_start, verse_end)
        indexed_results = indexed_lookup(
            reference,
            limit=max(limit * 4, 50),
            include_placeholders=False,
        )
        ranked: dict[str, tuple[float, dict[str, Any]]] = {}
        for result in indexed_results:
            obj = result.object
            payload = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)
            object_type = str(payload.get("type") or getattr(obj, "type", "")).strip().casefold()
            if object_type not in {"person", "place", "theme"}:
                continue
            compact = _compact_passage_entity(payload, direct_reference=True, matched_name="")
            ranked[compact["id"]] = (6.0 + float(getattr(result, "score", 0.0) or 0.0), compact)

        if normalized_text:
            for object_id in _indexed_entity_ids_in_text(library, normalized_text):
                obj = library.objects_by_id.get(object_id)
                if obj is None:
                    continue
                payload = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)
                title = str(payload.get("title") or payload.get("name") or payload.get("id") or "").strip()
                aliases = [str(value).strip() for value in payload.get("aliases") or []]
                matched_name = next(
                    (name for name in [title, *aliases] if _entity_name_in_text(name, normalized_text)),
                    "",
                )
                if not matched_name:
                    continue
                direct = object_id in ranked
                compact = _compact_passage_entity(payload, direct_reference=direct, matched_name=matched_name)
                ranked[object_id] = ((6.0 if direct else 0.0) + 4.0, compact)
        ordered = sorted(ranked.values(), key=lambda item: (-item[0], item[1]["type"], item[1]["title"]))
        return [payload for _score, payload in ordered[:limit]]

    # Lightweight test doubles and old third-party library adapters may not
    # expose the indexed API yet. Keep the compatibility fallback isolated.
    candidates: list[tuple[float, dict[str, Any]]] = []
    for obj in library.objects_by_id.values():
        payload = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)
        object_type = str(payload.get("type") or getattr(obj, "type", "")).strip().casefold()
        if object_type not in {"person", "place", "theme"}:
            continue
        title = str(payload.get("title") or getattr(obj, "title", "") or payload.get("name") or payload.get("id") or "").strip()
        aliases = [str(alias).strip() for alias in payload.get("aliases") or [] if str(alias).strip()]
        references = [
            str(reference.get("reference") if isinstance(reference, dict) else reference).strip()
            for reference in payload.get("scripture_references") or []
        ]
        direct_reference = any(
            _reference_overlaps_passage(
                reference,
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
            )
            for reference in references
        )
        matched_name = next(
            (
                name for name in [title, *aliases]
                if normalized_text and _entity_name_in_text(name, normalized_text)
            ),
            "",
        )
        if not direct_reference and not matched_name:
            continue
        score = (6.0 if direct_reference else 0.0) + (4.0 if matched_name else 0.0)
        score += min(float(payload.get("importance") or 0) / 100.0, 1.0)
        candidates.append((score, {
            "id": str(payload.get("id") or "").strip(),
            "title": title,
            "type": object_type,
            "summary": str(payload.get("summary") or "").strip(),
            "relationship": "direct Scripture anchor" if direct_reference else "named in passage",
            "matched_name": matched_name,
            "score": round(score, 3),
        }))
    candidates.sort(key=lambda item: (-item[0], item[1]["type"], item[1]["title"]))
    return [payload for _score, payload in candidates[:limit]]


def _compact_passage_entity(
    payload: dict[str, Any],
    *,
    direct_reference: bool,
    matched_name: str,
) -> dict[str, Any]:
    return {
        "id": str(payload.get("id") or "").strip(),
        "title": str(payload.get("title") or payload.get("name") or payload.get("id") or "").strip(),
        "type": str(payload.get("type") or "").strip().casefold(),
        "summary": str(payload.get("summary") or "").strip(),
        "relationship": "direct Scripture anchor" if direct_reference else "named in passage",
        "matched_name": matched_name,
        "score": round((6.0 if direct_reference else 0.0) + (4.0 if matched_name else 0.0), 3),
    }


def _indexed_entity_ids_in_text(library: Any, normalized_text: str) -> set[str]:
    """Resolve text mentions through the CKL's cached title/alias indexes."""

    matches: set[str] = set()
    for normalized_name, object_ids in getattr(library, "_title_index", {}).items():
        if _entity_name_in_text(normalized_name, normalized_text):
            matches.update(object_ids)
    for normalized_alias, entry in getattr(library, "_alias_index", {}).items():
        if _entity_name_in_text(normalized_alias, normalized_text):
            matches.add(str(entry[0]))
    return {
        object_id
        for object_id in matches
        if str(getattr(library.objects_by_id.get(object_id), "type", "")).casefold()
        in {"person", "place", "theme"}
    }


def _entity_name_in_text(name: str, normalized_text: str) -> bool:
    normalized_name = " ".join(str(name or "").casefold().split())
    if len(normalized_name) < 3:
        return False
    return re.search(rf"(?<![\w]){re.escape(normalized_name)}(?![\w])", normalized_text) is not None


def _reference_overlaps_passage(
    reference: str,
    *,
    book: str,
    chapter: int,
    verse_start: int | None,
    verse_end: int | None,
) -> bool:
    match = re.match(
        rf"^{re.escape(str(book).strip())}\s+{int(chapter)}(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?(?:\b|$)",
        str(reference or "").strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    if verse_start is None or match.group("start") is None:
        return True
    anchor_start = int(match.group("start"))
    anchor_end = int(match.group("end") or anchor_start)
    selected_end = int(verse_end or verse_start)
    return anchor_start <= selected_end and int(verse_start) <= anchor_end


def _format_passage_reference(
    book: str,
    chapter: int,
    verse_start: int | None,
    verse_end: int | None,
) -> str:
    reference = f"{book} {chapter}"
    if verse_start is None:
        return reference
    if verse_end and verse_end != verse_start:
        return f"{reference}:{verse_start}-{verse_end}"
    return f"{reference}:{verse_start}"


def _serialize_object(obj: Any) -> dict[str, Any]:
    payload = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)
    payload["aliases"] = list(payload.get("aliases") or [])
    payload["related_objects"] = [
        _serialize_relationship(relationship)
        for relationship in list(payload.get("related_objects") or [])
    ]
    payload["scripture_references"] = [
        _serialize_scripture_reference(reference)
        for reference in list(payload.get("scripture_references") or [])
    ]
    payload["sources"] = [
        _serialize_source(source)
        for source in list(payload.get("sources") or [])
    ]
    return payload


def _with_related_archaeology(
    payload: dict[str, Any],
    archaeology: ArchaeologyService,
    *,
    include_media: bool = True,
) -> dict[str, Any]:
    """Attach compact archaeology cards without making CKL own their media."""

    result = dict(payload)
    try:
        result["related_archaeology"] = archaeology.related_to_ckl(
            str(result.get("id") or ""),
            include_media=include_media,
        )
    except Exception:  # noqa: BLE001 - an optional evidence domain must not break CKL
        result["related_archaeology"] = []
    return result


def _serialize_source(source: Any) -> dict[str, Any]:
    payload = source.to_dict() if hasattr(source, "to_dict") else dict(source)
    return {
        "title": str(payload.get("title") or "").strip(),
        "author": str(payload.get("author") or "").strip(),
        "publisher": str(payload.get("publisher") or "").strip(),
        "year": payload.get("year"),
        "locator": str(payload.get("locator") or "").strip(),
        "url": str(payload.get("url") or "").strip(),
        "source_type": str(payload.get("source_type") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }


def _serialize_scripture_reference(reference: Any) -> dict[str, Any]:
    payload = reference.to_dict() if hasattr(reference, "to_dict") else dict(reference)
    return {
        "reference": str(payload.get("reference") or "").strip(),
        "relationship": str(payload.get("relationship") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }


def _serialize_relationship(relationship: Any) -> dict[str, Any]:
    payload = relationship.to_dict() if hasattr(relationship, "to_dict") else dict(relationship)
    return {
        "id": normalize_id(str(payload.get("id") or "").strip()),
        "relationship": str(payload.get("relationship") or "").strip(),
        "weight": int(payload.get("weight") or 1),
        "notes": str(payload.get("notes") or "").strip(),
    }


def _serialize_related_object_links(obj: Any, library: Any) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for relationship in getattr(obj, "related_objects", []) or []:
        normalized = _serialize_relationship(relationship)
        target = library.objects_by_id.get(normalized["id"])
        links.append(
            {
                **normalized,
                "title": target.title if target is not None else normalized["id"],
                "type": target.type if target is not None else None,
                "review_status": target.review_status if target is not None else None,
                "content_status": target.content_status if target is not None else None,
                "confidence": target.confidence if target is not None else None,
                "summary": target.summary if target is not None else "",
            }
        )
    return links


def _topic_reason(topic: dict[str, Any]) -> str:
    inclusion_type = str(topic.get("inclusion_type") or "primary")
    match_type = str(topic.get("match_type") or "keyword")
    matched_fields = ", ".join(str(field) for field in topic.get("matched_fields") or [])
    matched_terms = ", ".join(str(term) for term in topic.get("matched_terms") or [])
    relationship = str(topic.get("relationship") or "").strip()
    included_from = str(topic.get("included_from") or "").strip()
    if inclusion_type == "relationship":
        relation_text = relationship or "related"
        source_text = f" from {included_from}" if included_from else ""
        return f"Included{source_text} via {relation_text}."
    if match_type == "scripture":
        return "Matched by Scripture reference."
    if match_type == "alias":
        return f"Matched alias {topic.get('matched_alias') or 'unknown'}."
    if match_type == "id":
        return "Matched by exact object ID."
    if match_type == "title":
        return "Matched by title."
    if match_type == "phrase":
        return f"Matched phrase terms: {matched_terms or 'none'}."
    if match_type == "fuzzy_alias":
        return f"Matched a fuzzy alias across {matched_fields or 'search fields'}."
    return f"Matched search fields: {matched_fields or 'none'}."


def _topic_matches_filters(
    topic: dict[str, Any],
    object_type: str | None,
    review_status: str | None,
    content_status: str | None,
) -> bool:
    if str(topic.get("type") or "") == "archaeology":
        return False
    if object_type and object_type.lower() != "all" and str(topic.get("type") or "") != object_type:
        return False
    if review_status and review_status.lower() != "all" and str(topic.get("review_status") or "") != review_status:
        return False
    if content_status and content_status.lower() != "all" and str(topic.get("content_status") or "") != content_status:
        return False
    return True


def _object_matches_filters(
    obj: Any,
    object_type: str | None,
    review_status: str | None,
    content_status: str | None,
    *,
    include_placeholders: bool,
) -> bool:
    if getattr(obj, "type", "") == "archaeology":
        return False
    if not include_placeholders and str(getattr(obj, "content_status", "")) == "placeholder":
        return False
    if object_type and object_type.lower() != "all" and getattr(obj, "type", None) != object_type:
        return False
    if review_status and review_status.lower() != "all" and getattr(obj, "review_status", None) != review_status:
        return False
    if content_status and content_status.lower() != "all" and getattr(obj, "content_status", None) != content_status:
        return False
    return True
