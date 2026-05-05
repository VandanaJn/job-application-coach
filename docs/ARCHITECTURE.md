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

Current implementation (`graph/state.py`):

```python
class InterviewQuestion(BaseModel):
    question: str
    category: str  # behavioral | technical | situational

class GraphState(TypedDict):
    session_id: str
    user_id: str
    job_id: str
    resume_text: str
    job_description: str
    num_questions: int          # default 5, configurable per session
    questions: Optional[list[InterviewQuestion]]
    coaching_sessions: Optional[dict[str, str]]  # question_index → AgentCore runtimeSessionId
    status: str                 # running | completed | error
    error: Optional[str]
```

Fields to be added as later agents are implemented:

```python
    # Long-term memory (loaded at session start, written at session end)
    user_memory: UserMemory
    # Feedback outputs
    answers: Annotated[list[Answer], ...]
    feedback: Annotated[list[Feedback], ...]
```

`gaps` and `confirmed_gaps` will be added when GapAnalyzerAgent is implemented.

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
DynamoDB Table: job-coach-users
  PK: user_id
  Attributes: resume_text, s3_pdf_key

DynamoDB Table: job-coach-jobs
  PK: user_id
  SK: job_id (UUID)
  Attributes: job_title, company, job_description, created_at

DynamoDB Table: job-coach-sessions
  PK: user_id
  SK: session_id (UUID)
  Attributes: job_id, status, created_at, questions (list), error

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
      ├── GET  /user                   → Lambda (API): get user profile (has_resume flag)
      ├── POST /user/resume            → Lambda (API): upload PDF to S3, extract + store resume text
      │
      ├── POST /jobs                   → Lambda (API): save job (URL scrape or text paste)
      ├── GET  /jobs                   → Lambda (API): list saved jobs
      ├── GET  /jobs/{job_id}          → Lambda (API): get job details
      │
      ├── POST /sessions               → Lambda (API): create session for a job_id
      ├── GET  /sessions               → Lambda (API): list sessions
      ├── GET  /sessions/{id}          → Lambda (API): get session
      ├── POST /sessions/{id}/run      → Lambda (API): invoke runner Lambda async, set status=running
      │                                     └──────→ Lambda (Runner): runs LangGraph graph
      │                                                  writes questions + status to DynamoDB
      ├── GET  /sessions/{id}/status   → Lambda (API): poll status (pending/running/completed/error)
      │                                                 returns questions when completed
      └── POST /sessions/{id}/coach    → Lambda (API): invoke AgentCore Runtime (AnswerCoachAgent)
                                              └──────→ AgentCore Runtime (ARM64 container, HTTP/8080)
                                                           multi-turn per runtimeSessionId
                                                           reads UserMemory from DynamoDB
            │
            ▼
        Lambda (FastAPI + Mangum)
            │
            ├── S3                  ← PDF storage
            ├── DynamoDB            ← user, jobs, sessions, checkpoints, memory
            ├── Bedrock             ← LLM calls (Claude Haiku 4.5) + Guardrails
            │       └── LangSmith  ← traces (async, via background thread)
            └── AgentCore Runtime   ← AnswerCoachAgent (invoke_agent_runtime)
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
1. UI displays the interview question
2. User types (or speaks via SpeechRecognition) their answer
3. Text sent to `POST /sessions/{id}/coach` with `question_index` and `user_message`
4. API Lambda invokes the AgentCore Runtime, passing the answer and (on first turn) the question
5. AgentCore returns a coaching response and `is_complete` flag
6. UI shows the response; user can refine their answer or move on
7. Subsequent turns reuse the same `runtime_session_id` — AgentCore maintains conversation history in-session (microVM stays alive for the session lifetime)

The `runtimeSessionId` is generated client-side on first turn and echoed back in every response, allowing the frontend to maintain the multi-turn session without storing state server-side.

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
