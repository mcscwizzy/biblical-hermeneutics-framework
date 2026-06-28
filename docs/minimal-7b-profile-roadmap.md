# Roadmap of the Minimal-7B Profile Instruction Set

The file [minimal-7b.md](file:///home/johnwalker/Documents/github/biblical-hermeneutics-framework/profiles/minimal-7b.md) is a simplified, lightweight version of the Biblical Hermeneutics Framework (~3,793 tokens, 342 lines). It contains **5 core modules** and is optimized for smaller language models (such as 7B-parameter models) that have limited context windows or reasoning capacities.

---

## Profile Structure

The Minimal-7B profile includes only the most critical modules necessary to prevent major interpretive errors.

```mermaid
graph TD
    Start[User Asks a Question] --> Core[1. Core Framework <br/><i>Slow down, locate book & context</i>]
    Core --> Genre[2. Genre Awareness <br/><i>Recognize style of writing</i>]
    Genre --> Observe[3. Observe-Interpret-Apply <br/><i>Keep observation and interpretation separate</i>]
    Observe --> Inter[4. Intertextuality <br/><i>Track quotes, citations, and allusions</i>]
    Inter --> Humility[5. Epistemic Humility <br/><i>Label confidence: Consensus, Majority, etc.</i>]
    Humility --> End[Deliver Response]
```

---

## Module Breakdown

1. **`core.core-framework` (Lines 11-73):** Sets the default posture for the system, forcing it to work from context toward meaning, separate the steps, and leave theological conclusions to the reader.
2. **`core.genre-awareness` (Lines 76-138):** Instructs the system to identify the style of text (poetry, letter, history, etc.) before explaining it.
3. **`core.observe-interpret-apply` (Lines 141-192):** Enforces a strict separation between observing what is written, interpreting what it meant originally, and applying it today.
4. **`core.intertextuality` (Lines 197-290):** Teaches the system to distinguish quotations, citations, strong allusions, typology, and canonical themes without forcing connections.
5. **`core.epistemic-humility` (Lines 293-342):** Dictates how the system labels its certainty about findings (Consensus, Majority, Minority, or Speculation).

---

## Sitemap & Index of `minimal-7b.md`

Use this index to navigate the file:

| Module ID | Title | Start Line | End Line |
| :--- | :--- | :--- | :--- |
| **`core.core-framework`** | [Core Hermeneutic Framework](file:///home/johnwalker/Documents/github/biblical-hermeneutics-framework/profiles/minimal-7b.md#L11-L73) | Line 11 | Line 73 |
| **`core.genre-awareness`** | [Genre Awareness](file:///home/johnwalker/Documents/github/biblical-hermeneutics-framework/profiles/minimal-7b.md#L76-L140) | Line 76 | Line 140 |
| **`core.observe-interpret-apply`** | [Observation, Interpretation, Application](file:///home/johnwalker/Documents/github/biblical-hermeneutics-framework/profiles/minimal-7b.md#L143-L194) | Line 143 | Line 194 |
| **`core.intertextuality`** | [Intertextuality and Scriptural Connections](file:///home/johnwalker/Documents/github/biblical-hermeneutics-framework/profiles/minimal-7b.md#L197-L290) | Line 197 | Line 290 |
| **`core.epistemic-humility`** | [Epistemic Humility and Confidence Labels](file:///home/johnwalker/Documents/github/biblical-hermeneutics-framework/profiles/minimal-7b.md#L293-L342) | Line 293 | Line 342 |
