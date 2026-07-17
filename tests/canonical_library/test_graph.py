from __future__ import annotations

import unittest

from framework.canonical_library import (
    CanonicalObject,
    CanonicalRelationship,
    graph_audit,
    missing_reverse_relationships,
    relationship_edges,
    with_bidirectional_relationships,
)


def obj(
    object_id: str,
    title: str,
    *,
    related_objects: list[CanonicalRelationship] | None = None,
) -> CanonicalObject:
    return CanonicalObject(
        id=object_id,
        type="theme",
        title=title,
        aliases=[title],
        related_objects=list(related_objects or []),
    )


class CKLGraphTests(unittest.TestCase):
    def test_graph_audit_reports_missing_reverse_edges(self) -> None:
        david = obj(
            "david",
            "David",
            related_objects=[
                CanonicalRelationship(
                    id="jerusalem",
                    relationship="related-place",
                    weight=7,
                    notes="David makes Jerusalem the royal city.",
                )
            ],
        )
        jerusalem = obj("jerusalem", "Jerusalem")

        suggestions = missing_reverse_relationships([david, jerusalem])

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].source_id, "david")
        self.assertEqual(suggestions[0].target_id, "jerusalem")
        self.assertEqual(suggestions[0].suggested_relationship, "related-place")

    def test_with_bidirectional_relationships_adds_reverse_edges_in_memory(self) -> None:
        kingdom = obj(
            "kingdom-theme",
            "Kingdom",
            related_objects=[
                CanonicalRelationship(
                    id="messiah-theme",
                    relationship="related-theme",
                    weight=8,
                    notes="Kingdom expectation is tied to messianic hope.",
                )
            ],
        )
        messiah = obj("messiah-theme", "Messiah")

        updated = with_bidirectional_relationships([kingdom, messiah])
        updated_by_id = {item.id: item for item in updated}

        self.assertEqual(len(updated_by_id["messiah-theme"].related_objects), 1)
        self.assertEqual(updated_by_id["messiah-theme"].related_objects[0].id, "kingdom-theme")
        self.assertEqual(updated_by_id["messiah-theme"].related_objects[0].relationship, "related-theme")

    def test_graph_audit_reports_orphaned_objects_and_unknown_targets(self) -> None:
        connected = obj(
            "temple-theme",
            "Temple",
            related_objects=[
                CanonicalRelationship(
                    id="presence-theme",
                    relationship="related-theme",
                    weight=8,
                    notes="The temple is associated with divine presence.",
                ),
                CanonicalRelationship(
                    id="missing-node",
                    relationship="related",
                    weight=1,
                    notes="Broken edge.",
                ),
            ],
        )
        presence = obj("presence-theme", "Presence")
        orphan = obj("unlinked-symbol", "Unlinked Symbol")

        audit = graph_audit([connected, presence, orphan])
        edges = relationship_edges([connected, presence, orphan])

        self.assertEqual(len(edges), 2)
        self.assertEqual(audit.orphaned_object_ids, ["unlinked-symbol"])
        self.assertEqual(len(audit.unknown_target_edges), 1)
        self.assertEqual(audit.unknown_target_edges[0].target_id, "missing-node")


if __name__ == "__main__":
    unittest.main()
