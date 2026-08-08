from __future__ import annotations

from bhf_agent.study_actions import StudyActionRouter, compact_fact_packet, format_fact_packet_for_prompt


def test_archaeology_fact_packet_preserves_citations_and_ai_guardrails() -> None:
    result = StudyActionRouter().execute(
        "archaeology",
        passage={
            "book": "John",
            "chapter": 9,
            "start_verse": 7,
            "end_verse": 11,
            "selected_text": "Then he sent him away to the pool of Siloam.",
        },
    )
    packet = compact_fact_packet(result)
    prompt = format_fact_packet_for_prompt(packet)

    assert packet["evidence_packet"]["archaeological_items"]
    assert "Distinguish archaeological evidence from biblical text" in prompt
    assert "Do not claim an excavation proves a biblical event" in prompt
    assert "John 9:7-11" in prompt
