# Job Application Coach

A multi-agent AI system that helps you prepare for job interviews. Upload your resume and a job description — the system identifies skill gaps, generates targeted interview questions, coaches you through answers via voice, and scores your responses with actionable feedback.

Built as a production-ready portfolio project using LangGraph, AWS Bedrock, and React.

---

## Features

- **Flexible job input** — paste a job posting URL or plain text; URL scraping automatically extracts job title, company, and job description, with fallback to text paste for sites that block scraping (LinkedIn, Indeed)
- **Interview Question Generation** — generates targeted interview questions directly from your resume and the job description
- **Voice Answer Coaching** — back-and-forth voice conversation to help craft STAR-format answers (uses browser Web Speech API)
- **Answer Feedback** — scores each answer and gives specific improvement suggestions
- **Session Persistence** — save and resume sessions across browser visits

---

## Architecture

```
PDF Resume + Job Description
        │
        ▼
┌──────────────────────┐
│  InterviewPrepAgent  │  ← generates targeted interview questions
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  AnswerCoachAgent    │  ← voice back-and-forth coaching
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   FeedbackAgent      │  ← scores and suggests improvements
└──────────────────────┘
```

All agents orchestrated by a **LangGraph StateGraph** with guardrails middleware at every boundary. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph StateGraph |
| LLM | Claude Haiku 4.5 via AWS Bedrock |
| LLM framework | LangChain (LCEL) |
| Observability | LangSmith (tracing + evals) |
| Guardrails | Amazon Bedrock Guardrails + custom validators |
| API | FastAPI on AWS Lambda |
| Storage | DynamoDB (sessions) + S3 (PDFs) |
| Infrastructure | AWS CDK v2 Python |
| Frontend | React 18 + TypeScript + Vite + TailwindCSS |
| Voice | Web Speech API (browser-native) |
| CI/CD | GitHub Actions |

---

## Local Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- AWS CLI configured with credentials
- AWS Bedrock model access enabled for `anthropic.claude-haiku-4-5-20251001-v1:0`

### Backend

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your AWS region, LangSmith key, etc.

# Run tests
python -m pytest

# Run locally (without Lambda)
python graph/orchestrator.py
```

### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env.local
# Set VITE_API_URL to your API Gateway URL (or local dev server)

npm run dev
```

---

## Running Tests

```bash
# Backend — unit + integration tests
python -m pytest

# With coverage report
python -m pytest --cov

# Frontend
cd frontend && npm test
```

---

## Deployment

```bash
cd infra

# Deploy dev stack
cdk deploy JobCoachDev

# Deploy prod stack (manual)
cdk deploy JobCoachProd
```

The frontend runs locally and points to the deployed API Gateway URL via `VITE_API_URL`.

---

## CI/CD

- **Pull Request** — lint (ruff), type check (mypy), full test suite
- **Merge to main** — tests + auto-deploy to dev stack
- **Prod deploy** — manual trigger via GitHub Actions `workflow_dispatch`

---

## Project Structure

```
job-application-coach/
├── agents/          ← one file per agent
├── chains/          ← LCEL chains and prompt templates
├── graph/           ← LangGraph StateGraph and state definition
├── middleware/       ← input validators, guardrail wrappers
├── models/          ← Pydantic models
├── api/             ← FastAPI app and route handlers
├── evals/           ← LangSmith eval scripts and golden datasets
├── infra/           ← AWS CDK stack
├── lambda/          ← Lambda entry points
├── tests/           ← pytest tests (mirrors source structure)
├── frontend/        ← React + TypeScript app
├── docs/            ← Architecture and decision docs
└── .github/workflows/ ← CI/CD pipelines
```

---

## Docs

- [Requirements](docs/REQUIREMENTS.md) — functional and non-functional requirements, entities, open questions
- [Architecture](docs/ARCHITECTURE.md) — agent design, graph flow, guardrails, AWS stack
- [Decisions](docs/DECISIONS.md) — why we chose each technology and approach
