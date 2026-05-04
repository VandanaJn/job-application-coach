# Job Application Coach — Multi-Agent System

## Project Overview
Multi-agent AI system that analyzes resumes against job descriptions,
prepares interview questions, coaches answers, and provides feedback.
Built as a production-ready portfolio project demonstrating LangGraph agent
orchestration, AWS integration, guardrails middleware, evals, TDD, and CI/CD.

## User Inputs
- Resume: PDF upload (parsed server-side with pypdf, text extracted and passed to agents)
- Job description: either a URL or plain text paste
  - If URL: backend fetches and parses structured fields — job_title, company, job_description — using requests + BeautifulSoup
  - If text: job_description populated directly; job_title and company left blank for user to fill in
  - UI displays parsed title + company for user to confirm/edit before proceeding
  - Graceful fallback: if URL scraping fails (JS-rendered sites, auth walls), return a clear error asking user to paste text instead
  - Note: LinkedIn, Indeed, Glassdoor block scraping — only plain text works for those

## Agent Pipeline (in order)
1. **InterviewPrepAgent** — generates `num_questions` interview questions from resume + job description (default: 5, configurable per session)
2. **AnswerCoachAgent** — interactive back-and-forth voice conversation to help craft STAR-format answers; reads UserMemory for personalized coaching
3. **FeedbackAgent** — scores each answer and gives specific improvement suggestions; reads UserMemory to highlight recurring patterns
4. **MemoryUpdateAgent** — runs at end of session; distills new insights from session feedback and merges into UserMemory

GapAnalyzerAgent deferred — will add later as an optional pre-step before InterviewPrepAgent

## Tech Stack
### Backend
- **Python 3.12+**
- **LangChain 1.x** (`langchain>=1.2`) — `create_agent` pattern for all agents, no legacy Chain classes
- **LangGraph 1.x** (`langgraph>=1.1`) — StateGraph with typed state, interrupt() for human-in-the-loop,
  Command for flow control, SqliteSaver for local dev / DynamoDB checkpointer for prod
- **LangSmith** — tracing + evals enabled from day one
- **langchain-aws 1.x** (`langchain-aws>=1.4`) — ChatBedrockConverse for all LLM calls
- **AWS Bedrock** — Claude Haiku 4.5 (`anthropic.claude-haiku-4-5-20251001-v1:0`) via ChatBedrockConverse
- **Amazon Bedrock Guardrails** — content safety and prompt injection protection
- **FastAPI** — REST API layer (Lambda handler)
- **pypdf** — PDF text extraction
- **Pydantic v2** — structured output validation at every agent boundary

### Frontend
- **React 18 + TypeScript**, bootstrapped with Vite
- **TailwindCSS** — all styling
- **React Query (TanStack Query)** — all API calls
- **React Router v6** — client-side routing
- **Web Speech API** — browser-native voice input for AnswerCoach (Chrome/Edge)
- Runs locally — no cloud hosting needed

### Infrastructure (AWS)
- **AWS CDK v2 Python** — all infrastructure as code
- **API Gateway + Lambda** — REST API
- **DynamoDB** — session persistence
- **S3** — PDF storage
- **AWS AgentCore** — agent runtime
- **IAM** — least-privilege roles per Lambda function
- **CloudWatch** — logging and monitoring
- Separate stacks for dev and prod

### CI/CD
- **GitHub Actions**
- On PR: lint (ruff), type check (mypy), run full test suite
- On merge to main: run tests → deploy to AWS (dev stack)
- Prod deploy: manual trigger (workflow_dispatch) to prod stack

## LangGraph Patterns
- StateGraph with Annotated TypedDict for state
- interrupt() for human-in-the-loop pause point after GapAnalyzerAgent
- Command to control flow between nodes
- SqliteSaver for local dev checkpointing, DynamoDB checkpointer for prod
- Agents as nodes in the graph — no separate chains

## LangChain Patterns
- ChatBedrockConverse from langchain-aws for all LLM calls
- Default model: anthropic.claude-haiku-4-5-20251001-v1:0
- `create_agent(model, tools, system_prompt)` used consistently across all agents (InterviewPrep, AnswerCoach, Feedback, MemoryUpdate)
- `with_structured_output()` for structured responses where needed
- No LCEL pipe syntax (prompt | llm | parser)
- No legacy AgentExecutor

## Guardrails & Middleware
- **Input validation node** (before GapAnalyzerAgent): checks resume text is non-empty, plausible length, not a prompt injection attempt
- **Amazon Bedrock Guardrails**: applied to all LLM calls — content filtering, PII detection, prompt injection protection
- **Output validation**: every agent output validated against a Pydantic model before passing to next node
- **Error recovery node**: catches agent failures, returns structured error state to API
- Guardrails implemented as dedicated LangGraph nodes — testable, observable, replaceable

## Evals (LangSmith)
- Eval suite for each agent using LangSmith's eval framework
- GapAnalyzerAgent: precision/recall of identified gaps against golden examples
- InterviewPrepAgent: relevance of questions to gaps (LLM-as-judge)
- FeedbackAgent: quality and specificity of feedback (LLM-as-judge + rubric)
- Golden dataset: small set of resume+JD pairs with human-labelled expected outputs
- Evals run in CI on merge to main, results visible in LangSmith dashboard

## Session Persistence
- Each run is a session stored in DynamoDB (session_id, user_id, timestamps, full state)
- LangGraph graph state checkpointed — user can resume an interrupted session
- Single hardcoded user for now — user_id field in schema ready for multi-user auth later
- Session list page in UI to return to previous runs

## Long-Term Memory
- UserMemory entity persists across all sessions in DynamoDB (one record per user)
- Fields: strengths, improvement_areas, communication_patterns, past_sessions_summary, updated_at
- Read at session start: injected into AnswerCoachAgent and FeedbackAgent system prompts for personalized coaching
- Written at session end: MemoryUpdateAgent distills new insights from session feedback and merges into UserMemory
- Memory accumulates over time — coaching improves with each session
- Implemented using LangGraph's long-term memory store pattern

## Human-in-the-Loop
- No checkpoint in current pipeline — gap analysis step is deferred
- interrupt() will be used when GapAnalyzerAgent is added later
- Graph is designed so a checkpoint node can be inserted between GapAnalyzer and InterviewPrep without restructuring

## TDD Approach
- Write tests before implementation for every agent, chain, and graph node
- pytest for all backend tests
- Vitest + React Testing Library for frontend
- Test structure mirrors source structure — tests/ directory mirrors agents/, graph/, etc.
- Each agent tested in isolation with mocked LLM responses
- Integration tests run the full graph with a real (but cheap) Bedrock call
- Minimum 80% coverage enforced in CI

## Frontend Architecture (in /frontend — runs locally)
- Pages: Home/SessionList, ResumeUpload (PDF + JD paste), GapAnalysis (review + confirm gaps),
  InterviewPrep (question list), AnswerCoach (voice conversation per question), Feedback (scores + suggestions)
- Resume uploaded as multipart/form-data to API Gateway
- React Query for all API calls — no raw fetch in components
- Web Speech API for voice input in AnswerCoach — SpeechRecognition for STT, SpeechSynthesis for optional TTS
- Real-time agent progress via polling (React Query refetchInterval)
- Human-in-the-loop gap review: editable gap list with confirm button
- VITE_API_URL env var for backend URL

## Frontend Patterns
- Functional components + hooks only
- TypeScript strict mode, explicit types everywhere
- Co-locate component tests (*.test.tsx)
- Custom hooks in hooks/ for all stateful logic and React Query calls

## Project Structure
```
job-application-coach/
├── agents/               ← one file per agent
│   ├── gap_analyzer.py
│   ├── interview_prep.py
│   ├── answer_coach.py
│   └── feedback.py
├── graph/                ← LangGraph StateGraph orchestration
│   ├── orchestrator.py   ← main graph definition
│   ├── state.py          ← TypedDict state definition
│   └── nodes/            ← guardrail nodes, routing logic
├── middleware/            ← input validators, guardrail wrappers
├── models/               ← Pydantic models (shared between agents and API)
├── api/                  ← FastAPI app, route handlers
├── evals/                ← LangSmith eval scripts and golden datasets
├── infra/                ← CDK stack (Python)
├── lambda/               ← Lambda handler entry points
├── tests/                ← pytest tests mirroring source structure
├── frontend/             ← React + TypeScript + Vite
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   ├── vite.config.ts
│   └── package.json
├── .github/workflows/    ← CI/CD pipelines
├── .env.example
├── requirements.txt
├── requirements-dev.txt  ← pytest, ruff, mypy, etc.
└── CLAUDE.md
```

## Environment Variables
### Backend
- LANGSMITH_API_KEY
- LANGSMITH_PROJECT
- AWS_REGION
- AWS_ACCOUNT_ID
- BEDROCK_MODEL_ID — default: anthropic.claude-haiku-4-5-20251001-v1:0
- BEDROCK_GUARDRAIL_ID — Bedrock Guardrail ARN
- DYNAMODB_TABLE_NAME — sessions table
- DYNAMODB_USERS_TABLE — user profiles + resume text
- DYNAMODB_JOBS_TABLE — saved job postings
- S3_BUCKET_NAME
- RUNNER_FUNCTION_NAME — Lambda function name for async graph execution (e.g. job-coach-dev-runner)
- ENVIRONMENT — dev | prod

### Frontend
- VITE_API_URL — API Gateway base URL

## Decision Records
When a new architectural or technology decision is made, add an entry to docs/DECISIONS.md.
Format: ADR number, date, context, options considered, decision, rationale.

## Commands
### Backend
- `pip install -r requirements.txt` — install runtime deps
- `pip install -r requirements-dev.txt` — install dev/test deps
- `python -m pytest` — run tests
- `python -m pytest --cov` — run tests with coverage
- `python graph/orchestrator.py` — run locally

### Frontend
- `cd frontend && npm install`
- `cd frontend && npm run dev` — start Vite dev server
- `cd frontend && npm run build`
- `cd frontend && npm test`

### Infrastructure
- `cd infra && cdk deploy JobCoachDev` — deploy dev stack
- `cd infra && cdk deploy JobCoachProd` — deploy prod stack
