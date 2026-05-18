---
name: explain-architecture
description: >-
  Use when someone asks how a component of the Job Application Coach works,
  where something lives, why a design decision was made, or how a part was
  deployed (agents, AgentCore, CDK, DynamoDB, the LangGraph pipeline, the
  frontend). Grounds every answer in the project docs and verified source —
  never guesses.
---

# Explain Architecture

Answer questions about how the Job Application Coach is built, deployed, and
why — accurately, with references.

## Read these first, in order

1. `CLAUDE.md` — stack, agent pipeline, coding patterns (the intended design)
2. `docs/ARCHITECTURE.md` — full system design, AWS diagram, data model;
   note the **shipped vs planned** annotations — not everything described is built
3. `docs/DECISIONS.md` — ADRs explaining *why*; cite the ADR number when
   explaining a decision (e.g. "AgentCore was chosen — see ADR-019")

Then verify against actual source before answering — `infra/stacks/`,
`agents/`, `graph/`, `lambda/`, `frontend/src/`.

## Rules

- **Verify, don't assume.** ARCHITECTURE.md marks some components as planned
  (guards, feedback, memory_update, LangSmith tracing, GapAnalyzerAgent).
  Check whether code actually exists before describing it as shipped.
- **If something isn't in the project, say so plainly.** Do not invent a
  plausible answer. If asked about a tool/library/file the project doesn't
  use, state that it's not used and, where relevant, point to the ADR that
  explains the choice not to use it.
- **Cite sources.** Reference files as clickable links and ADRs by number so
  the answer is checkable.
- **Distinguish design from reality.** When CLAUDE.md's intended design and
  the shipped code differ, surface the gap rather than papering over it.

## Common ground truths (still verify against current code)

- Pipeline shipped: `interview_prep` (Lambda Runner) + `answer_coach`
  (AgentCore Runtime). Guards/feedback/memory_update are planned — ADR-020.
- AnswerCoachAgent runs on Bedrock AgentCore Runtime, not Lambda — ADR-019.
- Memory is a structured DynamoDB document, not a vector store — ADR-013.
  There are no embeddings and no Chroma in this project.
- LLM access is via `ChatBedrockConverse` on Bedrock — no direct Anthropic
  API, no boto3 Bedrock calls — ADR-002.
