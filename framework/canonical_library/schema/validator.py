"""Deterministic base-schema validation for CKL objects."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from .legacy import CanonicalValidationError, DEFAULT_CANONICAL_METADATA
BASE_SCHEMA_PATH = Path(__file__).resolve().with_name("base.schema.json")


@lru_cache(maxsize=1)
def load_base_schema() -> dict[str, Any]:
    with BASE_SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_base_object(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a raw CKL mapping against the base schema.

    The validator applies the standard governance defaults first so the schema
    describes the canonical post-normalization shape rather than the optional
    authoring shape.
    """

    if not isinstance(data, Mapping):
        raise _error(
            f"expected mapping, received {_type_name(data)}",
            path=path,
        )

    normalized = _apply_defaults(data)
    object_id = normalized.get("id") if isinstance(normalized.get("id"), str) else None
    schema = load_base_schema()
    _validate_schema(
        schema,
        normalized,
        root_schema=schema,
        path=path,
        object_id=object_id,
        field_path=(),
    )
    return normalized


def _apply_defaults(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for field_name, default_value in DEFAULT_CANONICAL_METADATA.items():
        if field_name not in normalized:
            normalized[field_name] = list(default_value) if isinstance(default_value, list) else default_value
    return normalized


def _validate_schema(
    schema: Mapping[str, Any],
    value: Any,
    *,
    root_schema: Mapping[str, Any],
    path: str | Path | None,
    object_id: str | None,
    field_path: tuple[str, ...],
) -> None:
    schema = _resolve_schema(schema, root_schema)

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        for option in any_of:
            try:
                _validate_schema(
                    option,
                    value,
                    root_schema=root_schema,
                    path=path,
                    object_id=object_id,
                    field_path=field_path,
                )
                return
            except CanonicalValidationError:
                pass
        label = _field_label(field_path)
        raise _error(
            f'field "{label}" does not match any allowed schema',
            path=path,
            object_id=object_id,
        ) from None

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        matches = 0
        last_error: CanonicalValidationError | None = None
        for option in one_of:
            try:
                _validate_schema(
                    option,
                    value,
                    root_schema=root_schema,
                    path=path,
                    object_id=object_id,
                    field_path=field_path,
                )
                matches += 1
            except CanonicalValidationError as exc:
                last_error = exc
        if matches != 1:
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" does not match exactly one allowed schema',
                path=path,
                object_id=object_id,
            ) from last_error
        return

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(expected_type, value):
        label = _field_label(field_path)
        raise _error(
            f'field "{label}" expected {_describe_schema_type(expected_type)}, received {_type_name(value)}',
            path=path,
            object_id=object_id,
        )

    if "const" in schema and value != schema["const"]:
        label = _field_label(field_path)
        raise _error(
            f'field "{label}" must be {schema["const"]!r}',
            path=path,
            object_id=object_id,
        )

    if "enum" in schema and value not in schema["enum"]:
        label = _field_label(field_path)
        allowed = ", ".join(repr(item) for item in schema["enum"])
        raise _error(
            f'field "{label}" must be one of {allowed}',
            path=path,
            object_id=object_id,
        )

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must be at least {schema["minLength"]} characters long',
                path=path,
                object_id=object_id,
            )
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must be at most {schema["maxLength"]} characters long',
                path=path,
                object_id=object_id,
            )
        if "pattern" in schema and not re.fullmatch(str(schema["pattern"]), value):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must match {schema["pattern"]!r}',
                path=path,
                object_id=object_id,
            )
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                label = _field_label(field_path)
                raise _error(
                    f'field "{label}" must be a valid YYYY-MM-DD date',
                    path=path,
                    object_id=object_id,
                ) from exc

    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < int(schema["minimum"]):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must be greater than or equal to {schema["minimum"]}',
                path=path,
                object_id=object_id,
            )
        if "maximum" in schema and value > int(schema["maximum"]):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must be less than or equal to {schema["maximum"]}',
                path=path,
                object_id=object_id,
            )

    if expected_type == "object" or (isinstance(expected_type, list) and "object" in expected_type):
        assert isinstance(value, Mapping)
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [field_name for field_name in required if field_name not in value]
        if missing:
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" is missing required field(s): {", ".join(missing)}',
                path=path,
                object_id=object_id,
            )
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                label = _field_label(field_path)
                raise _error(
                    f'field "{label}" contains unknown field(s): {", ".join(unknown)}',
                    path=path,
                    object_id=object_id,
                )
        for field_name, field_schema in properties.items():
            if field_name not in value:
                continue
            _validate_schema(
                field_schema,
                value[field_name],
                root_schema=root_schema,
                path=path,
                object_id=object_id,
                field_path=field_path + (field_name,),
            )
        return

    if expected_type == "array" or (isinstance(expected_type, list) and "array" in expected_type):
        assert isinstance(value, list)
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must contain at least {schema["minItems"]} item(s)',
                path=path,
                object_id=object_id,
            )
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            label = _field_label(field_path)
            raise _error(
                f'field "{label}" must contain at most {schema["maxItems"]} item(s)',
                path=path,
                object_id=object_id,
            )
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                _validate_schema(
                    item_schema,
                    item,
                    root_schema=root_schema,
                    path=path,
                    object_id=object_id,
                    field_path=field_path + (f"[{index}]",),
                )


def _resolve_schema(schema: Mapping[str, Any], root_schema: Mapping[str, Any]) -> Mapping[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise CanonicalValidationError(f"unsupported schema reference: {ref!r}")
    target: Any = root_schema
    for part in ref[2:].split("/"):
        target = target[part]
    if not isinstance(target, Mapping):
        raise CanonicalValidationError(f"schema reference {ref!r} did not resolve to an object")
    return target


def _matches_type(expected: Any, value: Any) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(item, value) for item in expected)
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return False


def _describe_schema_type(expected: Any) -> str:
    if isinstance(expected, list):
        return " or ".join(_describe_schema_type(item) for item in expected)
    return str(expected)


def _field_label(field_path: tuple[str, ...]) -> str:
    if not field_path:
        return "value"
    parts: list[str] = []
    for part in field_path:
        if part.startswith("[") and parts:
            parts[-1] = f"{parts[-1]}{part}"
        else:
            parts.append(part)
    return ".".join(parts)


def _type_name(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "list"
        item_types = {type(item).__name__ for item in value}
        if item_types == {"str"}:
            return "list[str]"
        return f"list[{', '.join(sorted(item_types))}]"
    return type(value).__name__


def _path_text(path: str | Path | None) -> str:
    if path is None:
        return "<in-memory>"
    return str(path)


def _error(
    message: str,
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalValidationError:
    prefix = "Invalid canonical object"
    if path is not None:
        prefix = f"{prefix} in {_path_text(path)}"
    if object_id:
        prefix = f"{prefix} [id={object_id}]"
    return CanonicalValidationError(f"{prefix}: {message}")


__all__ = [
    "BASE_SCHEMA_PATH",
    "load_base_schema",
    "validate_base_object",
]
