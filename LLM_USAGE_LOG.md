# LLM Usage Log: TACS 2026/27 QMDE, Group D3

Required by Section 8 of the assignment. One entry per *significant* use. Graded on critical
reflection, not length. **What was wrong and how you caught it** is the most important column.

| # | Date | Who | Tool & model | Part | Goal | Prompt (summary) | Accepted | Wrong / rejected, and how it was detected & fixed |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-15 | Rui Martins | Claude Code (Claude Opus 5.5) | 0/I | Get an overview of the course material and project; produce planning guides | Asked for an analysis of the course materials and support files (deadlines, deliverables) for our problem | Deadline/deliverable summary; D3 orientation guide; qubit-budget estimate from a brute-force script | |
| 2 | 2026-10-16 to 2026-10-18 | Rui Martins | Claude Code (Claude Opus 5.5) | I | Get a first version of the problem DSL and learn how to implement it in BESSER | Asked for a starting metamodel for our chosen domain scope, plus an example model and an OCL test | First drafts of the metamodel, example model, checker and test; explanations of B-UML, OCL and B-OCL | B-OCL can't evaluate several OCL constructs, so 5 constraints are checked in Python. The first example model was silently wrong (repeated links overwrote each other); caught by the broken-model tests and fixed. |

---

## Entry template (for longer entries)

### Entry N: <short title>
- **Date / who:**
- **Tool & model:**
- **Goal:**
- **Prompt summary:**
- **Accepted:**
- **Wrong or rejected:**
- **How detected:** (test, brute-force comparison, paper X section Y, OCL check failed, ...)
- **Fix:**
