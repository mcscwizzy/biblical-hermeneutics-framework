---
id: book.SLUG                  # e.g. book.genesis
title: TITLE (Book Module)
type: book
version: 0.1.0
status: draft
tokens: 0                      # update to ~chars/4 of the body
requires: [core.core-framework]   # add the primary genre module, e.g. genre.narrative
recommends: []                    # relevant context/language modules + secondary genres
tags: []
sources_required: true
maintainers: []
license: CC-BY-4.0
---

## Purpose

How this module helps the AI approach this book. A book module is a hermeneutic
profile, not a commentary: it teaches *how to approach* the book and assumes the
Core, Genre, Context, and Language layers are already loaded. Do not repeat them.

## When to apply

When interpreting any passage in this book, loaded on top of Core, the relevant
Genre module(s), and the Context modules named below.

## Genre signals

The dominant genre(s) and where each appears in the book; name the genre
module(s) to apply (`[[genre.SLUG]]`). Do not oversimplify a mixed book.

## Historical anchors

The historical and cultural worlds most relevant to this book, **referencing**
Context modules (e.g. [[context.ancient-near-east]]) rather than repeating them.
Label authorship/date/setting for confidence (see [[core.epistemic-humility]]).

## Literary features

What to look for (e.g. repeated words, narrative patterns, speeches, poetry,
symbolism, genealogy, chiasm, inclusio, irony, parallelism, quotations,
allusions). Teach the AI to look; do not claim every feature is present.

## Key interpretive questions

Questions an interpreter should ask of this book — to improve observation.
**Pose them; do not answer them.**

## Common misreadings

Frequent method mistakes, described neutrally (the mistake itself, not a
critique of any tradition).

## Handling uncertainty

Where scholarship is divided (authorship, dating, structure, literary
boundaries, historical reconstruction). Label uncertainty; do not feign
certainty (see [[core.epistemic-humility]]).

## Cross-references

- [[core.core-framework]]
