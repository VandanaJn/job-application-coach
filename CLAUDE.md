# Job Application Coach

Multi-agent AI: resume + JD → interview questions → answer coaching → feedback → memory update.
Portfolio project. See `docs/ARCHITECTURE.md` for full design detail.

## Stack
- **Backend**: Python 3.12+, LangChain 1.x, LangGraph 1.x, FastAPI, Pydantic v2
- **LLM**: `ChatBedrockConverse` (langchain-aws) — `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Infra**: AWS CDK v2 Python — API Gateway + Lambda + DynamoDB + S3
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS + React Query + React Router v6
- **CI/CD**: GitHub Actions — ruff + mypy + pytest on PR; deploy dev on merge to main

## Agent Pipeline (in order)
1. InterviewPrepAgent — questions from resume + JD (default 5, configurable per session)
2. AnswerCoachAgent — multi-turn coaching, STAR format, reads UserMemory
3. FeedbackAgent — scores answers, reads UserMemory for patterns
4. MemoryUpdateAgent — end of session; merges insights into UserMemory

GapAnalyzerAgent: deferred, slots in before InterviewPrepAgent when added.

## Coding Patterns (must follow)
- All agents: `from langchain.agents import create_agent` (LangChain 1.x) — no LCEL pipes, no `AgentExecutor`, no custom `create_agent` shims
- Structured outputs: `response_format=ToolStrategy(PydanticModel)` on `create_agent`; read via `result["structured_response"]` (do NOT use `model.with_structured_output()` directly inside agents)
- All LLM calls: `ChatBedrockConverse` — no direct boto3 Bedrock calls
- Each agent module exposes a `build_*_agent()` factory returning a callable that takes domain args and returns the Pydantic structured response
- LangGraph: `StateGraph` + `Annotated TypedDict` state; guardrails as dedicated nodes (not callbacks)
- Frontend: functional components + hooks only; all API calls via React Query; no raw fetch in components

## TDD
- Tests before implementation — pytest (backend), Vitest + RTL (frontend)
- Test structure mirrors source; agents tested with mocked LLM responses
- 80% coverage minimum enforced in CI

## Key Docs
- Architecture & design: `docs/ARCHITECTURE.md`
- Architecture decisions: `docs/DECISIONS.md` (ADR format)
- Env vars: `.env.example`

## Commands
```bash
python -m pytest                    # backend tests
python -m pytest --cov              # with coverage
cd frontend && npm run dev          # dev server
cd frontend && npm test             # frontend tests
cd infra && cdk deploy JobCoachDev
cd infra && cdk deploy JobCoachProd
```
