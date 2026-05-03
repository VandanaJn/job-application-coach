# Architecture

## System Overview

The Job Application Coach is a multi-agent pipeline orchestrated by a LangGraph `StateGraph`. Each agent is a node in the graph. Guardrail nodes sit at the boundaries between agents to validate inputs and outputs. The entire graph is traced via LangSmith.

The backend runs as a FastAPI app on AWS Lambda, behind API Gateway. State is persisted in DynamoDB. PDFs are stored in S3. The frontend is a React SPA that runs locally and calls the API.

---

## Agent Pipeline

```
[User: PDF + JD]
      │
      ▼
┌─────────────────┐
│  input_guard    │  validates resume text length, detects prompt injection
└────────┬────────┘
         │
         ▼                       ┌─────────────┐
┌──────────────────────┐         │ UserMemory  │ ← loaded once at session start
│  interview_prep      │         └─────────────┘
│  (num_questions=5)   │
└──────────┬───────────┘
           │
           ▼
┌─────────────────┐
│  output_guard   │  validates QuestionList Pydantic model, checks non-empty
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│  answer_coach        │  multi-turn voice conversation, reads UserMemory for personalized tips
│  (loops per question)│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  feedback            │  score + suggestions, surfaces recurring patterns from UserMemory
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  memory_update       │  distills session insights → merges into UserMemory in DynamoDB
└──────────────────────┘
```

GapAnalyzerAgent is deferred. When added, it will slot in before interview_prep with an interrupt() checkpoint between them.

---

## LangGraph State

```python
class CoachState(TypedDict):
    session_id: str
    user_id: str
    # Job details
    resume_text: str
    job_title: str
    company: str
    job_description: str
    # Config
    num_questions: int          # default 5, configurable per session
    # Long-term memory (loaded at session start, written at session end)
    user_memory: UserMemory
    # Agent outputs
    interview_questions: Annotated[list[Question], ...]
    current_question_index: int
    conversation_history: Annotated[list[Message], ...]
    answers: Annotated[list[Answer], ...]
    feedback: Annotated[list[Feedback], ...]
    error: str | None
```

`gaps` and `confirmed_gaps` fields will be added when GapAnalyzerAgent is implemented.

State is immutable between nodes — each node returns a partial update. LangGraph merges updates using the Annotated reducers (append for lists, replace for scalars).

---

## Guardrails Middleware

Guardrails are implemented as dedicated LangGraph nodes rather than decorators or callbacks. This makes them:
- **Testable** in isolation
- **Observable** in LangSmith traces (appear as their own spans)
- **Replaceable** without touching agent logic

### Input Guard Node
- Checks resume text is between 100–50,000 characters
- Checks JD text is between 50–20,000 characters
- Passes both through **Amazon Bedrock Guardrails** for prompt injection detection and PII filtering
- On failure: routes to error node, returns structured error to API

### Output Guard Node
- Validates each agent output against its Pydantic model
- Checks for empty or degenerate outputs (e.g. zero gaps identified)
- On failure: retries once with a clarifying prompt, then routes to error node

### Amazon Bedrock Guardrails
- Applied at the LLM call level via `ChatBedrockConverse` guardrail config
- Configured for: content filtering, prompt injection protection, PII detection
- Guardrail ID stored in `BEDROCK_GUARDRAIL_ID` env var

---

## Session Persistence & Long-Term Memory

```
DynamoDB Table: job-coach-sessions
  PK: user_id
  SK: session_id (UUID)
  Attributes: created_at, updated_at, status, num_questions,
              resume_text, s3_pdf_key, job_title, company, job_description

DynamoDB Table: job-coach-checkpoints  (LangGraph checkpointer table)
  PK: thread_id (= session_id)
  SK: checkpoint_id
  Attributes: graph state blob

DynamoDB Table: job-coach-memory  (long-term user memory)
  PK: user_id
  SK: "MEMORY"
  Attributes: strengths (list), improvement_areas (list),
              communication_patterns (str), past_sessions_summary (list),
              updated_at
```

UserMemory is loaded once at the start of each session and injected into the graph state. At the end of the session, MemoryUpdateAgent generates a structured diff (new insights only) and merges it into the existing record — it does not overwrite, it accumulates.

LangGraph's DynamoDB checkpointer saves the full graph state after every node execution. If a session is interrupted (browser close, Lambda timeout), the user can resume from the last checkpoint.

Local dev uses `SqliteSaver` instead — zero config, same interface.

---

## AWS Architecture

```
Browser (local)
      │  HTTPS
      ▼
API Gateway (REST)
      │
      ├── POST /sessions               → Lambda (API): create session, store to DynamoDB
      ├── POST /sessions/{id}/resume   → Lambda (API): upload PDF to S3, parse job details
      ├── POST /sessions/{id}/run      → Lambda (API): validate input, invoke graph Lambda
      │                                               async (returns session_id immediately)
      │                                     └──────→ Lambda (Runner): runs LangGraph graph
      │                                                  writes status + results to DynamoDB
      ├── GET  /sessions/{id}/status   → Lambda (API): poll session status (pending/running/completed/error)
      ├── GET  /sessions/{id}          → Lambda (API): fetch full session state
      └── GET  /sessions               → Lambda (API): list sessions
            │
            ▼
        Lambda (FastAPI handler)
            │
            ├── S3        ← PDF storage
            ├── DynamoDB  ← session + checkpoint + status storage
            └── Bedrock   ← LLM calls (Claude Haiku 4.5) + Guardrails
                    │
                    └── LangSmith ← traces (async, via background thread)
```

**Async invocation pattern:** `POST /sessions/{id}/run` returns the `session_id` immediately after triggering the background Lambda. The frontend polls `GET /sessions/{id}/status` via React Query `refetchInterval` until status is `completed` or `error`.

Each Lambda function has its own least-privilege IAM role. Bedrock calls use the Lambda execution role — no API keys in environment variables.

---

## Evals

Evals are run via LangSmith's eval framework. A golden dataset lives in `evals/datasets/`.

| Agent | Eval type | Metric |
|---|---|---|
| GapAnalyzerAgent | Reference-based | Precision + recall of gaps vs. human-labelled examples |
| InterviewPrepAgent | LLM-as-judge | Relevance of questions to confirmed gaps |
| FeedbackAgent | LLM-as-judge + rubric | Specificity, actionability, accuracy of feedback |

Evals run in CI on merge to main. Results are posted to the LangSmith dashboard. A significant regression (>10% drop) blocks the deploy.

---

## Voice (AnswerCoach)

Voice input uses the browser-native **Web Speech API**:
- `SpeechRecognition` — transcribes spoken answer to text, sent to AnswerCoachAgent
- `SpeechSynthesis` — optionally reads coach responses aloud

Works in Chrome and Edge. The React component degrades gracefully — falls back to a text input if the browser doesn't support `SpeechRecognition`.

The back-and-forth coaching loop works as follows:
1. UI reads the interview question aloud (SpeechSynthesis)
2. User speaks their answer (SpeechRecognition → text)
3. Text sent to `POST /sessions/{id}/resume` with the transcribed answer
4. AnswerCoachAgent responds with a follow-up prompt or STAR coaching tip
5. Loop continues until user clicks "Submit Final Answer"

---

## CI/CD

```
PR opened/updated
  └── GitHub Actions: ci.yml
        ├── ruff (lint)
        ├── mypy (type check)
        ├── pytest (unit + integration)
        └── vitest (frontend tests)

Merge to main
  └── GitHub Actions: deploy-dev.yml
        ├── pytest + vitest
        └── cdk deploy JobCoachDev

Manual trigger (workflow_dispatch)
  └── GitHub Actions: deploy-prod.yml
        ├── pytest + vitest
        └── cdk deploy JobCoachProd
```
