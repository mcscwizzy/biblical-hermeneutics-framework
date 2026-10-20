"""Reviewed, exact-identity curation for selected Narrative Explorer edges.

This registry annotates CKL-authored relationships without rewriting CKL data.
Each entry is tied to its full authored identity and only applies to its stated
passage scope. Evidence-to-evidence entries also require an independently
eligible target in the current passage projection.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .references import references_overlap


_SCHOLARLY_SOURCE_DETAILS: Mapping[str, Mapping[str, Any]] = {
    "hundley-sacred-common-space": {
        "title": "Sacred Space and Common Space",
        "author": "Michael B. Hundley",
        "year": 2020,
    },
    "hundley-sacred-space": {
        "title": "Sacred Space and Common Space",
        "author": "Michael B. Hundley",
        "year": 2020,
    },
    "meyers-exodus-tabernacle": {
        "title": "Exodus",
        "author": "Carol Meyers",
        "year": 2005,
    },
    "smith-ugaritic-baal-cycle-1994": {
        "title": "The Ugaritic Baal Cycle, Volume I: Introduction with Text, Translation and Commentary of KTU 1.1-1.2",
        "author": "Mark S. Smith",
        "year": 1994,
    },
    "smith-origins-biblical-monotheism-2001": {
        "title": "The Origins of Biblical Monotheism: Israel's Polytheistic Background and the Ugaritic Texts",
        "author": "Mark S. Smith",
        "year": 2001,
    },
    "lewis-origin-character-god-2020": {
        "title": "The Origin and Character of God: Ancient Israelite Religion through the Lens of Divinity",
        "author": "Theodore J. Lewis",
        "year": 2020,
    },
}


def _source_reference(object_id: str, source_id: str) -> dict[str, Any]:
    return {
        "object_id": object_id,
        "source_id": source_id,
        **dict(_SCHOLARLY_SOURCE_DETAILS.get(source_id, {})),
    }


def _object_edge(
    source: str,
    target: str,
    label: str,
    notes: str,
    weight: int,
    classification: str,
    applicable_passages: Sequence[str],
    supporting_passages: Sequence[str],
    textual_observation: str,
    why: str,
    uncertainty: str,
    supporting_ckl_sources: Sequence[tuple[str, str]],
    *,
    certainty: str = "moderate",
) -> dict[str, Any]:
    source_records = [
        _source_reference(object_id, source_id)
        for object_id, source_id in supporting_ckl_sources
    ]
    return {
        "relationship_kind": "object",
        "source_id": f"ckl:{source}",
        "target_id": f"ckl:{target}",
        "original_relationship_type": label,
        "original_notes": notes,
        "original_weight": weight,
        "classification": classification,
        "applicable_passages": list(applicable_passages),
        "supporting_passages": list(supporting_passages),
        "supporting_records": [
            f"ckl:{record['object_id']}#source:{record['source_id']}"
            for record in source_records
        ],
        "supporting_ckl_sources": source_records,
        "textual_observation": textual_observation,
        "why": why,
        "uncertainty": uncertainty,
        "certainty": certainty,
        "review_status": "curated_for_explorer",
    }


def _evidence_edge(
    source_evidence: str,
    target_evidence: str,
    label: str,
    notes: str,
    weight: int,
    classification: str,
    applicable_passages: Sequence[str],
    supporting_passages: Sequence[str],
    textual_observation: str,
    why: str,
    uncertainty: str,
    source_ids: Sequence[str],
    *,
    certainty: str = "moderate",
) -> dict[str, Any]:
    parent = "ckl:ancient-divine-assembly-imagery"
    return {
        "relationship_kind": "evidence",
        "source_id": f"{parent}#evidence:{source_evidence}",
        "target_id": f"{parent}#evidence:{target_evidence}",
        "original_relationship_type": label,
        "original_notes": notes,
        "original_weight": weight,
        "classification": classification,
        "applicable_passages": list(applicable_passages),
        "supporting_passages": list(supporting_passages),
        "supporting_records": [
            f"{parent}#evidence:{source_evidence}",
            f"{parent}#evidence:{target_evidence}",
        ],
        "supporting_ckl_sources": [
            _source_reference("ancient-divine-assembly-imagery", source_id)
            for source_id in source_ids
        ],
        "textual_observation": textual_observation,
        "why": why,
        "uncertainty": uncertainty,
        "certainty": certainty,
        "review_status": "curated_for_explorer",
    }


# Deliberately edge-specific. Broad relationship labels never trigger these
# classifications by themselves.
CURATED_RELATIONSHIPS: tuple[Mapping[str, Any], ...] = (
    _object_edge(
        "creation", "new-creation-theme", "eschatological-fulfillment",
        "renewed creation", 9, "thematic_relationship",
        ["Genesis 1:1-31"], ["Genesis 1:1-31", "Revelation 21:1-5"],
        "Genesis 1 presents ordered creation; Revelation 21:1-5 depicts a new heaven and earth and says that all things are being made new.",
        "The edge gives readers a canonical route from the creation account to Revelation's new-creation vision.",
        "This is a thematic canonical relationship, not a quotation claim or proof that Revelation depends on Genesis alone. Revelation also draws on prophetic restoration language, especially Isaiah 65-66.",
        [("creation", "genesis-1-2"), ("creation", "revelation-21"), ("new-creation-theme", "revelation-21")],
        certainty="high",
    ),
    _object_edge(
        "creation", "the-fall", "narrative-contrast",
        "creation broken by sin", 8, "thematic_relationship",
        ["Genesis 2:4-25"], ["Genesis 2:4-25", "Genesis 3:1-24", "Romans 5:12-21"],
        "Genesis 2-3 places human vocation and garden life immediately before the disobedience and its consequences.",
        "This connection helps readers follow the movement from creation and vocation into the Genesis 3 disruption and later reflection on sin and death.",
        "The phrase 'creation broken by sin' is a theological synthesis; Genesis 3 itself narrates disobedience and expulsion. Romans 5 is a later canonical interpretation, not the original setting of Genesis.",
        [("creation", "genesis-1-2"), ("the-fall", "genesis-3"), ("the-fall", "romans-5")],
    ),
    _object_edge(
        "resurrection", "new-creation-theme", "eschatological-fulfillment",
        "firstfruits of new creation", 9, "interpretive_association",
        ["1 Corinthians 15:20-28"], ["1 Corinthians 15:20-28", "Romans 8:18-23", "Revelation 21:1-5"],
        "Paul calls the raised Christ the firstfruits in 1 Corinthians 15:20; Romans 8 pictures creation awaiting liberation, and Revelation 21 depicts renewed creation.",
        "The route links resurrection hope with the wider canonical hope for creation's renewal while keeping each passage's claim visible.",
        "In 1 Corinthians 15 'firstfruits' directly describes Christ's resurrection and the coming resurrection of the dead; the new-creation framing is a broader canonical synthesis. It should not be presented as Paul's explicit phrase in this passage.",
        [("resurrection", "1-corinthians-15"), ("resurrection", "romans-6"), ("new-creation-theme", "romans-8"), ("new-creation-theme", "revelation-21")],
    ),
    _object_edge(
        "new-jerusalem", "new-creation-theme", "canonical-fulfillment",
        "renewed heaven and earth", 10, "thematic_relationship",
        ["Revelation 21:1-5"], ["Revelation 21:1-5", "Isaiah 65:17-25"],
        "Revelation 21:1 introduces a new heaven and new earth; verses 2-5 describe the city, God's dwelling, and the making-new of all things.",
        "The two CKL subjects describe overlapping aspects of the same closing vision, making the city an entry point into the chapter's new-creation imagery.",
        "Revelation combines prophetic restoration traditions, including Isaiah 65-66, with its own apocalyptic vision. This classification does not settle how literally or symbolically the city should be read.",
        [("new-jerusalem", "revelation-21-22"), ("new-creation-theme", "revelation-21")],
        certainty="high",
    ),
    _object_edge(
        "new-jerusalem", "temple-theme", "presence-fulfillment",
        "no temple because God is present", 8, "thematic_relationship",
        ["Revelation 21:22-27"], ["Revelation 21:3", "Revelation 21:22-27", "Ezekiel 40:1-48:35"],
        "Revelation 21:22 says John sees no temple in the city because the Lord God and the Lamb are its temple; 21:3 has already announced God's dwelling with humanity.",
        "This connects the city's presence imagery with temple language and invites readers to compare the vision with earlier sanctuary traditions.",
        "The passage explicitly denies a temple building in the city, but interpreters differ on whether the city is itself temple-like, whether divine presence renders a building unnecessary, or how Revelation reworks Ezekiel's temple vision. No single model is encoded as fact.",
        [("new-jerusalem", "revelation-21-22"), ("temple-theme", "revelation-21"), ("temple-theme", "hebrews-9-10")],
    ),
    _object_edge(
        "temple", "new-jerusalem", "eschatological-fulfillment",
        "final dwelling without a temple", 8, "thematic_relationship",
        ["Revelation 21:22-27"], ["Revelation 21:3", "Revelation 21:22-27", "1 Kings 8:10-13"],
        "Revelation 21:22-27 depicts God's presence in the city without a separate sanctuary building; 1 Kings 8:10-13 narrates the cloud filling Solomon's temple.",
        "The connection lets readers compare temple-dedication presence language with Revelation's final city and its explicit no-temple statement.",
        "The texts belong to distinct literary and historical settings. Revelation's image may transform temple symbolism rather than predict the disappearance of every temple concept; Jewish and Christian readings vary.",
        [("temple", "1-kings-8"), ("temple", "revelation-21"), ("new-jerusalem", "revelation-21-22")],
    ),
    _object_edge(
        "sanctuary-theme", "tabernacle", "foundational-sanctuary-form",
        "Exodus, Leviticus, and Numbers ground the theme in dwelling, holiness, access, and mobility.",
        10, "thematic_relationship", ["Exodus 25:8-9"],
        ["Exodus 25:8-9", "Exodus 40:34-38"],
        "Exodus 25:8-9 commands a sanctuary so that God may dwell among Israel and gives a pattern for the tent; Exodus 40:34-38 narrates the cloud and glory filling it.",
        "The tabernacle is a concrete textual setting for the broader sanctuary theme and helps readers trace dwelling, access, and mobility in the wilderness narrative.",
        "The category summarizes recurring literary and theological themes; interpretations of the tabernacle's historical construction and ancient Near Eastern parallels remain distinct questions.",
        [("sanctuary-theme", "exodus-25-40"), ("sanctuary-theme", "hundley-sacred-common-space"), ("tabernacle", "meyers-exodus-tabernacle")],
        certainty="high",
    ),
    _object_edge(
        "tabernacle", "temple", "later-sanctuary-development",
        "The Jerusalem temple receives ark, cloud, glory, priestly, and spatial traditions while remaining a distinct permanent structure.",
        9, "thematic_relationship", ["1 Kings 8:1-13"],
        ["Exodus 40:34-38", "1 Kings 8:1-13"],
        "In 1 Kings 8:4 the tent of meeting and its holy vessels are brought up with the ark; in 8:10-13 the cloud fills the temple. The narrative connects the sanctuaries while distinguishing the permanent building from the tent.",
        "Readers can follow the narrative and cultic transition from the portable tabernacle to Jerusalem's temple without treating the structures as identical.",
        "The relationship is supported by the biblical narrative. Ancient Near Eastern tent and temple comparisons can illuminate context, but resemblance alone does not prove borrowing or settle the tabernacle's historicity.",
        [("tabernacle", "tabernacle-pentateuch-text"), ("tabernacle", "meyers-exodus-tabernacle"), ("tabernacle", "hundley-sacred-space"), ("temple", "1-kings-8")],
        certainty="high",
    ),
    _object_edge(
        "covenant-theme", "abraham", "covenant-founder", "initial promise line", 9,
        "thematic_relationship", ["Genesis 15:1-21"],
        ["Genesis 12:1-3", "Genesis 15:1-21", "Genesis 17:1-14"],
        "Genesis 12 gives Abram a promise of land, descendants, and blessing; Genesis 15 narrates a covenant-making scene, and Genesis 17 names covenant signs and obligations.",
        "This connection locates Abraham within the covenant theme's early narrative and gives readers a path to the promise traditions later texts reuse.",
        "The relationship among the ancestral promises, covenant language, and later covenant traditions is debated; the classification does not assume a single composition history or a simple linear system of covenants.",
        [("covenant-theme", "genesis-9-12-15-17"), ("abraham", "genesis-12-22")],
        certainty="high",
    ),
    _object_edge(
        "covenant-theme", "moses", "covenant-mediator", "Sinai mediator", 9,
        "thematic_relationship", ["Exodus 19:1-6"],
        ["Exodus 19:1-6", "Exodus 24:1-11"],
        "Exodus 19 frames Israel's arrival at Sinai and covenant vocation; Exodus 24 narrates covenant words, assent, and blood rite with Moses as mediator.",
        "This links the covenant theme to the Sinai narrative and helps readers navigate the mediator, people, and covenant ceremony together.",
        "The interpretation of Sinai's covenant form and its relation to ancestral promises and later covenants remains disputed. The link describes the narrative focus rather than resolving that debate.",
        [("covenant-theme", "exodus-19-24"), ("moses", "exodus-3-24")],
        certainty="high",
    ),
    _object_edge(
        "covenant-theme", "new-covenant", "fulfillment-anchor", "promised renewal", 9,
        "later_canonical_reception", ["Hebrews 8:6-13"],
        ["Jeremiah 31:31-34", "Hebrews 8:6-13"],
        "Hebrews 8:8-12 quotes Jeremiah 31:31-34 and applies its new-covenant promise to the argument about Jesus' priesthood and covenant.",
        "This route shows how a later biblical text receives Jeremiah's promise and makes the reception visible as reception rather than as Jeremiah's original setting.",
        "Christian interpretation of the new covenant's relation to Israel, the church, and the earlier covenant varies. The classification does not endorse supersessionism or claim that all traditions understand fulfillment alike.",
        [("covenant-theme", "jeremiah-31"), ("covenant-theme", "hebrews-8-10"), ("new-covenant", "jeremiah-31"), ("new-covenant", "hebrews-8-10")],
        certainty="high",
    ),
    _object_edge(
        "exile-theme", "new-covenant", "restoration-anchor", "promise of renewal", 8,
        "thematic_relationship", ["Ezekiel 36:24-28"],
        ["Ezekiel 36:24-28", "Jeremiah 31:31-34"],
        "Ezekiel 36:24-28 promises gathering from the nations, cleansing, a new heart, and the divine spirit; Jeremiah 31:31-34 separately names a new covenant.",
        "The passages connect exile-era restoration hopes with covenant renewal and let readers compare related prophetic promises without collapsing their wording.",
        "Ezekiel 36:24-28 does not use Jeremiah's 'new covenant' formula in these verses. This is a thematic association across prophetic texts, not an explicit quotation or a claim that their historical settings and promises are identical.",
        [("exile-theme", "ezekiel-36"), ("new-covenant", "ezekiel-36"), ("new-covenant", "jeremiah-31")],
    ),
    _object_edge(
        "covenant-theme", "messiah-theme", "covenant-fulfillment", "kingly promise and blessing", 7,
        "thematic_relationship", ["2 Samuel 7:8-16"],
        ["2 Samuel 7:8-16", "Psalm 2:1-12"],
        "Second Samuel 7 promises David a house and enduring rule; Psalm 2 portrays a king installed in Zion and called God's son.",
        "The route connects Davidic kingship and covenant promises with later royal and messianic interpretation.",
        "The immediate royal setting of these texts and their later messianic reception must be distinguished. Jewish and Christian interpreters differ about the identity and scope of the promised ruler.",
        [("covenant-theme", "2-samuel-7"), ("messiah-theme", "2-samuel-7"), ("messiah-theme", "psalm-2")],
    ),
    _object_edge(
        "messiah-theme", "covenant-theme", "promise-fulfillment", "covenant promise reaches fulfillment", 8,
        "thematic_relationship", ["2 Samuel 7:8-16"],
        ["2 Samuel 7:8-16", "Luke 24:25-27", "Acts 2:22-36"],
        "Second Samuel 7:8-16 is a Davidic dynastic promise; Luke 24 and Acts 2 show later Christian readings that relate Israel's Scriptures to Jesus.",
        "The existing reverse-directed CKL edge is retained as authored and gives a second route for comparing covenant and messianic themes.",
        "This is a separate authored direction, not an automatically created reverse edge. The New Testament's Christian reception does not establish that the original oracle had only a later messianic referent.",
        [("messiah-theme", "2-samuel-7"), ("messiah-theme", "luke-24"), ("covenant-theme", "2-samuel-7")],
    ),
    _object_edge(
        "messiah-theme", "kingdom-theme", "royal-context", "the king who reigns", 10,
        "thematic_relationship", ["Psalm 2:1-12"],
        ["Psalm 2:1-12", "Daniel 7:13-14", "Mark 1:14-15"],
        "Psalm 2 joins an anointed ruler in Zion with royal rule over the nations; Daniel 7 and Mark 1 offer distinct later kingdom settings.",
        "The connection helps readers explore the relationship between royal or messianic figures and the biblical kingdom theme.",
        "Psalm 2's original royal setting, its possible enthronement use, and its later Jewish and Christian messianic readings are distinct questions. Daniel 7's 'one like a son of man' is interpreted as collective, angelic, divine, or messianic in different scholarship.",
        [("messiah-theme", "psalm-2"), ("kingdom-theme", "psalm-2"), ("kingdom-theme", "daniel-2-7")],
    ),
    _object_edge(
        "kingdom-theme", "messiah-theme", "messianic-rule", "kingdom arrives through the anointed king", 9,
        "thematic_relationship", ["Psalm 2:1-12"],
        ["Psalm 2:1-12", "Daniel 7:13-14", "Mark 1:14-15"],
        "Psalm 2 supplies an anointed royal figure and rule over nations; Mark 1:14-15 announces God's kingdom without quoting Psalm 2 in these verses.",
        "The reverse-directed authored edge makes the kingdom-to-king relationship discoverable from the kingdom theme itself.",
        "This is not a fabricated reverse edge. The precise relation between Israel's kingship, the kingdom of God, and later messianic expectation is interpreted in more than one way.",
        [("kingdom-theme", "psalm-2"), ("kingdom-theme", "mark-1"), ("messiah-theme", "psalm-2")],
    ),
    _object_edge(
        "messiah-theme", "resurrection-theme", "vindication-pattern", "suffering leads to vindication", 8,
        "later_canonical_reception", ["Acts 2:22-36"],
        ["Psalm 16:8-11", "Psalm 110:1-7", "Acts 2:22-36"],
        "In Acts 2:22-36 Peter interprets Jesus' resurrection and exaltation through Psalm 16 and Psalm 110 and relates them to Davidic kingship.",
        "This makes an identifiable New Testament reception path between messianic kingship and resurrection hope visible to readers.",
        "Acts 2 is a later Christian interpretation of Israel's Scriptures. Its claims should not be projected back as the sole original meaning of Psalms 16 or 110, and traditions differ on the identity and scope of the messianic reading.",
        [("messiah-theme", "luke-24"), ("messiah-theme", "psalm-110"), ("resurrection-theme", "1-corinthians-15")],
    ),
    _object_edge(
        "resurrection-theme", "messiah-theme", "vindication-pattern", "the Messiah is vindicated", 9,
        "later_canonical_reception", ["Acts 2:22-36"],
        ["Psalm 16:8-11", "Psalm 110:1-7", "Acts 2:22-36"],
        "Acts 2:22-36 interprets Jesus' resurrection and exaltation through Psalm 16 and Psalm 110 and relates that reading to Davidic kingship.",
        "This separately authored reverse edge makes the resurrection-to-messianic-kingship route discoverable from the resurrection theme.",
        "The edge is present in CKL with its own note and weight; it is not generated by this registry. Acts 2 records a later Christian reception and does not settle the original referent of the Psalms for all interpreters.",
        [("resurrection-theme", "1-corinthians-15"), ("messiah-theme", "luke-24"), ("messiah-theme", "psalm-110")],
    ),
    _evidence_edge(
        "psalm-82-assembly-language", "ugaritic-council-comparison",
        "northwest-semitic-comparison",
        "The earlier comparison does not decide the referents in Psalm 82.", 7,
        "interpretive_association", ["Psalm 82:1-8"],
        ["Psalm 82:1-8", "KTU 1.1-1.2"],
        "Psalm 82 depicts God in an assembly and addresses plural elohim; Ugaritic texts portray divine council scenes. The CKL source explicitly says this comparison does not decide Psalm 82's referents.",
        "Readers can inspect the biblical language alongside an earlier Northwest Semitic comparison while seeing that the two evidence records remain distinct.",
        "Comparison establishes neither borrowing nor direct literary dependence. Psalm 82's figures are variously read as divine beings, human rulers or judges, national patrons, or rhetorically demoted gods; dating and reconstructed background remain contested.",
        ["smith-ugaritic-baal-cycle-1994", "smith-origins-biblical-monotheism-2001", "lewis-origin-character-god-2020"],
    ),
    _evidence_edge(
        "ugaritic-council-comparison", "psalm-82-assembly-language",
        "compared-with",
        "The biblical text and Ugaritic texts retain separate observations.", 7,
        "interpretive_association", ["Psalm 82:1-8"],
        ["Psalm 82:1-8", "KTU 1.1-1.2"],
        "The comparative evidence record anchors Ugaritic material as earlier-comparative and Psalm 82 as comparative; its note preserves the distinction between corpora.",
        "This authored direction exposes the same comparison from the comparative record without turning it into a reverse biblical claim.",
        "The evidence supports comparison of assembly imagery, not a claim that Psalm 82 borrows from a specific Ugaritic text or that its speakers have one settled identity.",
        ["smith-ugaritic-baal-cycle-1994", "smith-origins-biblical-monotheism-2001", "lewis-origin-character-god-2020"],
    ),
)


def _identity(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        entry["relationship_kind"],
        entry["source_id"],
        entry["target_id"],
        entry["original_relationship_type"],
        entry["original_notes"],
        entry["original_weight"],
    )


_CURATION_BY_IDENTITY = {_identity(entry): entry for entry in CURATED_RELATIONSHIPS}


def curate_connection(connection: Any, passage_reference: str) -> Any:
    """Return a passage-eligible connection with its reviewed annotation."""

    kind = "evidence" if connection.basis.get("kind") == "ckl_related_evidence" else "object"
    identity = (
        kind,
        connection.source_id,
        connection.target_id,
        connection.original_relationship_type,
        connection.basis.get("notes"),
        connection.basis.get("weight"),
    )
    entry = _CURATION_BY_IDENTITY.get(identity)
    if entry is None or not any(
        references_overlap(passage_reference, reference)
        for reference in entry["applicable_passages"]
    ):
        return connection
    if kind == "evidence" and connection.basis.get("target_resolution_status") != "eligible":
        return connection
    from dataclasses import replace

    return replace(
        connection,
        connection_type=entry["classification"],
        curation=dict(entry),
    )


def validate_curation(entry: Mapping[str, Any]) -> None:
    """Validate the small public curation payload before it enters a projection."""

    required_text = (
        "relationship_kind", "source_id", "target_id", "original_relationship_type",
        "original_notes", "classification", "textual_observation", "why",
        "uncertainty", "certainty", "review_status",
    )
    if any(not isinstance(entry.get(key), str) or not entry[key] for key in required_text):
        raise ValueError("curated relationship has missing explanatory metadata")
    if entry["relationship_kind"] not in {"object", "evidence"}:
        raise ValueError("curated relationship has an invalid relationship kind")
    if type(entry.get("original_weight")) is not int:
        raise ValueError("curated relationship has an invalid original weight")
    if entry["review_status"] != "curated_for_explorer":
        raise ValueError("curated relationship has an invalid review status")
    if not all(
        isinstance(entry.get(key), list)
        and entry[key]
        and all(isinstance(value, str) and value for value in entry[key])
        for key in ("applicable_passages", "supporting_passages", "supporting_records")
    ):
        raise ValueError("curated relationship has incomplete passage or record support")
    if not isinstance(entry.get("supporting_ckl_sources"), list) or not entry["supporting_ckl_sources"]:
        raise ValueError("curated relationship has no CKL source provenance")
    for source in entry["supporting_ckl_sources"]:
        if not isinstance(source, Mapping) or any(
            not isinstance(source.get(key), str) or not source[key]
            for key in ("object_id", "source_id")
        ):
            raise ValueError("curated relationship has invalid CKL source provenance")
