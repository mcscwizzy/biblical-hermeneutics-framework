from __future__ import annotations

from types import SimpleNamespace

from bhf_web.routes.canonical import _entities_for_passage


class _Object:
    def __init__(self, payload):
        self.payload = payload
        self.type = payload["type"]
        self.title = payload["title"]

    def to_dict(self):
        return dict(self.payload)


def test_companion_entities_rank_reference_and_text_matches():
    library = SimpleNamespace(objects_by_id={
        "paul": _Object({
            "id": "paul",
            "type": "person",
            "title": "Paul",
            "aliases": ["the apostle Paul"],
            "summary": "Apostle and letter writer.",
            "scripture_references": [{"reference": "1 Thessalonians 4:1-18"}],
            "importance": 95,
        }),
        "thessalonica": _Object({
            "id": "thessalonica",
            "type": "place",
            "title": "Thessalonica",
            "aliases": [],
            "summary": "A Macedonian city.",
            "scripture_references": [],
            "importance": 80,
        }),
        "unrelated": _Object({
            "id": "jericho",
            "type": "place",
            "title": "Jericho",
            "aliases": [],
            "summary": "A city in the Jordan Valley.",
            "scripture_references": [{"reference": "Joshua 6:1-27"}],
            "importance": 80,
        }),
    })

    results = _entities_for_passage(
        library,
        book="1 Thessalonians",
        chapter=4,
        verse_start=17,
        verse_end=17,
        passage_text="Paul writes to believers associated with Thessalonica.",
        limit=10,
    )

    assert [item["id"] for item in results] == ["paul", "thessalonica"]
    assert results[0]["relationship"] == "direct Scripture anchor"
    assert results[1]["relationship"] == "named in passage"


def test_companion_entities_respect_verse_ranges():
    library = SimpleNamespace(objects_by_id={
        "early": _Object({
            "id": "early",
            "type": "theme",
            "title": "Early Theme",
            "scripture_references": [{"reference": "John 1:1-5"}],
        }),
        "late": _Object({
            "id": "late",
            "type": "theme",
            "title": "Late Theme",
            "scripture_references": [{"reference": "John 1:20-24"}],
        }),
    })

    results = _entities_for_passage(
        library,
        book="John",
        chapter=1,
        verse_start=3,
        verse_end=4,
        passage_text="",
        limit=10,
    )

    assert [item["id"] for item in results] == ["early"]
