---
name: answer-case-question
description: Answer a planning-case question from the local corpus with source locators, confidence labels, contradictions, and an explicit acquisition plan.
---

# Answer a case question

1. Preserve the user's wording and identify hidden premises.
2. Query the local corpus using exact identifiers, phrases, synonyms, and
   relevant actors.
3. Read surrounding pages or transcript timestamps; do not answer from snippets
   alone.
4. Separate the current answer, verified facts, agency position, supported
   interpretation, conflicting evidence, unresolved facts, and practical
   implications.
5. Cite source ID plus page, section, or timestamp for every material claim.
6. Correct a false premise directly. For example, August 20 did not adopt twenty
   conditions; it continued the item.
7. State exactly which record would improve or decide the answer.
8. Save the question, findings, confidence, and missing evidence in
   `questions.yaml`, then rebuild the casebook.

An answer is complete only when a reader can follow each important claim back
to the record and see the remaining uncertainty.
