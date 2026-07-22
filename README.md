# Biblical Hermeneutics Framework (BHF)

> **Teaching AI—and helping people—how to read the Bible carefully.**

**Biblical Hermeneutics Framework (BHF)** is an open-source biblical study framework that teaches **how to interpret Scripture responsibly** rather than **what to believe**.

Unlike most AI Bible tools that ask a language model to answer directly from memory, BHF first gathers the relevant evidence—Scripture, historical background, literary context, lexical information, and curated study resources—before asking an AI model to explain it.

The result is a study experience designed to be more transparent, more grounded, and more educational.

---

# Our Mission

The mission of BHF has remained the same from the beginning:

> **Teach AI models how to interpret Scripture responsibly without teaching them what conclusions they must reach.**

BHF intentionally avoids becoming a theological authority.

Instead, it teaches a method.

That method encourages AI—and the people using it—to:

- Observe before interpreting.
- Read passages in context.
- Understand the original audience.
- Respect literary genre.
- Examine historical and cultural background.
- Distinguish evidence from speculation.
- Admit uncertainty where appropriate.
- Apply Scripture only after understanding what it originally meant.

BHF does not replace careful Bible study.

It teaches it.

---

# Explain It Like I'm Five

Imagine walking into a library.

You ask,

> "What does this Bible verse mean?"

A librarian does **not** immediately answer your question.

Instead, the librarian walks through the library collecting the right books.

They gather:

- The Bible passage
- Historical information
- Hebrew or Greek word studies
- Cultural background
- Related passages
- Maps
- Timelines
- Study notes

Once everything is on the table, a teacher explains it in plain English.

That is exactly how BHF works.

The **BHF Agent** is the librarian.

The **AI model** is the teacher.

The librarian gathers the facts.

The teacher explains them.

---

# Why BHF Is Different

Most AI Bible applications look like this:

```text
Question
      │
      ▼
Large Language Model
      │
      ▼
Answer
```

The model is expected to remember everything it has learned.

BHF works differently.

```text
Question
      │
      ▼
Determine the type of question
      │
      ▼
Gather relevant evidence
      │
      ▼
Organize the evidence
      │
      ▼
AI explains the evidence
      │
      ▼
Answer
```

Instead of depending on the AI model to remember everything, BHF retrieves the information the model needs before it begins writing.

The model's primary job becomes explaining—not inventing—the answer.

---

# How BHF Works

Depending on the question, the agent gathers information from local deterministic resources before sending anything to the language model.

These resources may include:

- Scripture
- Original Hebrew and Greek lexical databases
- Canonical Knowledge Library (CKL)
- Historical context
- Literary context
- Cross references
- Maps
- Timeline information
- Translation comparisons
- User study notes
- Optional local session memory

Once the evidence is gathered, BHF constructs a focused request for the selected language model.

Even very small local models can produce high-quality study responses because they are explaining structured evidence instead of trying to reconstruct biblical scholarship from memory.

---

# BHF Architecture

```text
                    Biblical Hermeneutics Framework

                              User Question
                                    │
                                    ▼
                     Determine What Is Being Asked
                                    │
          ┌───────────────┬───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
      Scripture        Lexicon          CKL       Historical Data
          │               │               │               │
          └───────────────┴───────────────┴───────────────┘
                                    │
                                    ▼
                     Build Focused Evidence Packet
                                    │
                                    ▼
             ChatGPT • Claude • Gemini • Ollama • Local Models
                                    │
                                    ▼
                      Grounded Biblical Explanation
```

The important idea is simple:

> **The BHF Agent gathers the evidence. The AI model explains the evidence.**

---

# Prompt Profiles

BHF can be used entirely without the local agent.

Prompt profiles teach any compatible AI model the BHF interpretation method.

| Profile      | Purpose                                           |
| ------------ | ------------------------------------------------- |
| **Minimal**  | Small local models with limited context           |
| **Standard** | Balanced study profile                            |
| **Scholar**  | Full-depth study profile for large-context models |

These profiles work with:

- ChatGPT
- Claude
- Gemini
- Ollama
- LM Studio
- Open WebUI
- Any compatible system prompt

---

# The BHF Agent

The optional Python agent expands BHF beyond prompt engineering.

Rather than sending every question directly to an AI model, the agent first determines what kind of study is being requested.

Examples include:

- Word Study
- Historical Context
- Literary Context
- Passage Study
- Book Overview
- Topic Study

The agent then:

1. Detects Scripture references.
2. Determines the question type.
3. Retrieves relevant local evidence.
4. Builds a focused prompt.
5. Applies guardrails.
6. Calls the selected language model.
7. Validates the response.

This architecture reduces unnecessary token usage while improving consistency and allowing much smaller local models to perform well.

---

# Learning the Bible, Not Replacing It

Every feature in BHF exists for one purpose:

> **Help people become better readers of Scripture.**

The goal is not simply to answer Bible questions.

The goal is to teach people how to study the Bible for themselves.

Whether someone uses ChatGPT, a local model running entirely offline, or no AI at all, the same study method applies.

BHF encourages users to:

- Observe carefully.
- Read slowly.
- Compare Scripture with Scripture.
- Consider historical context.
- Think critically.
- Recognize uncertainty.
- Continue studying.

---

# Features

Current capabilities include:

- Offline Bible reader
- Local translation management
- Greek and Hebrew lexical databases
- Word Study
- Cross References
- Ancient Context
- Literary Context
- Related Old Testament Themes
- New Testament Fulfillment
- Timeline studies
- Maps
- Translation comparison
- Highlights
- Study notes
- Saved studies
- Canonical Knowledge Library (CKL)
- Optional local session memory
- Docker deployment
- Selenium regression testing
- Model-agnostic architecture

---

# Why BHF Can Use Small AI Models

BHF is designed so the surrounding software performs much of the work that larger language models normally perform internally.

The agent identifies the question, retrieves relevant evidence, and organizes the information before calling the language model.

As a result, even lightweight local models—such as **Qwen2.5:0.5B**—can provide useful study responses because they are primarily explaining evidence rather than generating it from memory.

This makes BHF:

- Faster
- More transparent
- More consistent
- More efficient
- Better suited for local and offline study

---

# Open Source

BHF is completely open source.

The framework continues to grow through contributions from developers, biblical scholars, historians, linguists, educators, and the open-source community.

Our long-term vision is simple:

> **Build one of the world's best open-source biblical study frameworks—available to everyone, online or offline, regardless of the AI model they choose.**
