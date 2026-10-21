# LLM Usage Log: TACS 2026/27 QMDE, Group D3

Required by Section 8 of the assignment. One entry per *significant* use. Graded on critical
reflection, not length. **What was wrong and how you caught it** is the most important column.


| #   | Date                     | Who           | Tool &amp; model              | Part | Goal                                                                                       | Prompt (summary)                                                                                                                       | Accepted                                                                                                                                                           | Wrong / rejected, and how it was detected &amp; fixed                                                                                                                                                              |
| --- | ------------------------ | ------------- | ----------------------------- | ---- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | 2026-10-15               | Rui Martins   | Claude Code (Claude Opus 5.5) | 0/I  | Get an overview of the course material and project; produce planning guides                | Asked for an analysis of the course materials and support files (deadlines, deliverables) for our problem                              | Deadline/deliverable summary; D3 orientation guide; qubit-budget estimate from a brute-force script                                                                |                                                                                                                                                                                                                    |
| 2   | 2026-10-16 to 2026-10-18 | Rui Martins   | Claude Code (Claude Opus 5.5) | I    | Get a first version of the problem DSL and learn how to implement it in BESSER             | Asked for a starting metamodel for our chosen domain scope, plus an example model and an OCL test                                      | First drafts of the metamodel, example model, checker and test; explanations of B-UML, OCL and B-OCL                                                               | B-OCL can't evaluate several OCL constructs, so 5 constraints are checked in Python. The first example model was silently wrong (repeated links overwrote each other); caught by the broken-model tests and fixed. |
| 3   | 2026-10-19 to 2026-10-21 | Lucas Alfonsi | Codex (GPT-6 Astra)           | I    | Review Part I deliverables, get an initial solution DSL and learn to implement it          | Asked for an analysis on what was missing for Part I deliverable; help defining ILP concepts, BESSER implementation and diagram review | Solution DSL concept table, metamodel guidance, association corrections, OCL declarations                                                                          | Codex generated an example and tests for it that were rejected so we could make our own. Just like the problem DSL, some OCL constructs couldn't be evaluated through B-OCL, so they had to be checked in python   |
| 4    | 2026-10-21               | Lucas Alfonsi | Codex (GPT-6 Astra)           | I    | Prevent malformed DSL models from crashing validation and clarify the correct test command | Asked to prevent malformed conflicts and clarify the test command                                                                      | Structural validation before invariant evaluation, defensive checks for missing or multiple required links, eight malformed-model regression cases, README updates | Change to the test command was considered unnecessary. The existing run()-based script was retained and the correct module command was documented.                                                                 |
| 5 | 2026-10-21 | Margarida Fonseca | ChatGPT (GPT-6.1 Sol) | I | Understand the DSLs, test the Solution DSL and improve the report | Asked for explanations of the concepts, tests for valid and invalid models, and report feedback | DSL explanations, adapted test suite, design-rationale suggestions | Initial code used different class names and an example that did not match our model; comparison with the current files revealed the mismatch. Later checker changes left outdated test imports and expectations; local verification is still pending. |

---

## Entry template (for longer entries)

### Entry N: <short title>

- **Date / who:**
- **Tool &amp; model:**
- **Goal:**
- **Prompt summary:**
- **Accepted:**
- **Wrong or rejected:**
- **How detected:** (test, brute-force comparison, paper X section Y, OCL check failed, ...)
- **Fix:**