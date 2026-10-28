"""Deduplicated skill and technology aggregation for generated resumes."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable


_SKILL_SEPARATOR = re.compile(r"\s*(?:[,;\n|•·])\s*")


def _skill_values(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        value = value.get("items") or value.get("skills") or value.get("name") or ""
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _skill_values(item)
        return
    if not isinstance(value, str):
        return
    for item in _SKILL_SEPARATOR.split(value):
        cleaned = re.sub(r"\s+", " ", item).strip(" \t.-")
        if cleaned:
            yield cleaned


def collect_project_technologies(*project_sources: Any) -> list[str]:
    """Collect stack values from every imported project record, preserving order."""
    values: list[str] = []
    seen: set[str] = set()
    for source in project_sources:
        if not isinstance(source, (list, tuple)):
            continue
        for project in source:
            if not isinstance(project, dict):
                continue
            tech = (
                project.get("tech")
                or project.get("technologies")
                or project.get("stack")
                or project.get("language")
                or project.get("languages")
                or ""
            )
            if isinstance(tech, str) and re.fullmatch(r"\s*(?:pesquisa|research)(?:\s*\([^)]*\))?\s*", tech, re.IGNORECASE):
                continue
            for item in _skill_values(tech):
                key = unicodedata.normalize("NFKC", item).casefold()
                if key not in seen:
                    seen.add(key)
                    values.append(item)
    return values


def merge_skill_groups(
    *skill_sources: Any,
    extra_items: Any = None,
    category: str = "Skills & Technologies",
) -> list[dict[str, str]]:
    """Merge skill groups into one readable list, deduplicated without case sensitivity."""
    values: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        for item in _skill_values(value):
            key = unicodedata.normalize("NFKC", item).casefold()
            if key not in seen:
                seen.add(key)
                values.append(item)

    for source in skill_sources:
        if isinstance(source, dict):
            add(source)
        elif isinstance(source, (list, tuple, set)):
            for group in source:
                add(group)
        else:
            add(source)
    add(extra_items)

    if not values:
        return []
    return [{"category": category, "items": ", ".join(values)}]
