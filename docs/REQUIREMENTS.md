# Requirements

## 1. Functional Requirements

### 1.1 Resume Input
- FR-01: User can upload a resume as a PDF file
- FR-02: System extracts plain text from the PDF server-side (pypdf)
- FR-03: System rejects uploads that are not valid PDFs
- FR-04: System rejects PDFs where no text can be extracted (e.g. scanned image PDFs)

### 1.2 Job Description Input
- FR-05: User can provide a job posting URL or paste plain text
- FR-06: If a URL is provided, system fetches and extracts job_title, company, and job_description from the page
- FR-07: If plain text is provided, user manually enters job_title and company; job_description is the pasted text
- FR-08: After URL scraping, user can review and edit the extracted job_title, company, and job_description before proceeding
- FR-09: If URL scraping fails (JS-rendered page, auth wall, timeout), system returns a clear error and prompts user to paste text instead
- FR-10: System does not attempt to scrape LinkedIn, Indeed, or Glassdoor URLs — surfaces a clear message directing user to paste text

### 1.3 Interview Question Generation
- FR-11: System generates interview questions from the resume text and job description
- FR-12: Default number of questions is 5; user can configure this per session before starting
- FR-13: Questions are targeted to the specific role and company, not generic

### 1.4 Answer Coaching
- FR-14: User can answer each question using voice input (Web Speech API) or typed text
- FR-15: System engages in a back-and-forth coaching conversation to help the user refine their answer into STAR format (Situation, Task, Action, Result)
- FR-16: Coaching is personalised using the user's long-term memory (past strengths and improvement areas)
- FR-17: User can submit their final answer when satisfied to end the coaching loop for that question
- FR-18: Voice input degrades gracefully to text input if the browser does not support SpeechRecognition

### 1.5 Feedback
- FR-19: After submitting a final answer, system provides a score and specific improvement suggestions
- FR-20: Feedback references recurring patterns from the user's long-term memory where relevant
- FR-21: Score scale: TBD (to be confirmed by user)

### 1.6 Session Management
- FR-22: Each resume + job description combination is a session
- FR-23: Sessions are persisted — user can return to an in-progress or completed session
- FR-24: User can see a list of past sessions on the home page
- FR-25: User can resume an interrupted session from the last checkpoint

### 1.7 Long-Term Memory
- FR-26: System maintains a UserMemory record that persists across all sessions
- FR-27: UserMemory stores: strengths, improvement_areas, communication_patterns, past_sessions_summary
- FR-28: UserMemory is loaded at the start of each session and injected into coaching and feedback agents
- FR-29: At the end of each session, a MemoryUpdateAgent distills new insights and merges them into UserMemory (accumulates — does not overwrite)

---

## 2. Non-Functional Requirements

### 2.1 Quality & Testing
- NFR-01: Tests written before implementation (TDD)
- NFR-02: Minimum 80% test coverage enforced in CI
- NFR-03: Each agent tested in isolation with mocked LLM responses
- NFR-04: Integration tests run the full graph with a real (cheap) Bedrock call

### 2.2 Observability
- NFR-05: All LLM calls and agent executions traced in LangSmith
- NFR-06: Guardrail nodes appear as their own spans in LangSmith traces
- NFR-07: CloudWatch logging enabled for all Lambda functions

### 2.3 Evals
- NFR-08: Eval suite implemented for each agent using LangSmith eval framework
- NFR-09: A golden dataset of resume + JD pairs with expected outputs maintained in evals/datasets/
- NFR-10: Evals run in CI on merge to main; a >10% regression blocks the deploy

### 2.4 Safety & Guardrails
- NFR-11: Input guard node validates resume text length and detects prompt injection before any LLM call
- NFR-12: Amazon Bedrock Guardrails applied to all LLM calls for content filtering and PII detection
- NFR-13: Every agent output validated against a Pydantic model before passing to the next node
- NFR-14: All agent failures route to an error node that returns a structured error response to the API

### 2.5 CI/CD
- NFR-15: Every pull request runs lint (ruff), type check (mypy), and full test suite via GitHub Actions
- NFR-16: Merge to main auto-deploys to the dev AWS stack
- NFR-17: Production deploy is a manual trigger (workflow_dispatch) to prevent accidental releases

### 2.6 Infrastructure
- NFR-18: Backend runs on AWS (Lambda + API Gateway + DynamoDB + S3 + Bedrock)
- NFR-19: All infrastructure defined as code using AWS CDK v2 Python
- NFR-20: Separate dev and prod CDK stacks
- NFR-21: Lambda functions use least-privilege IAM roles
- NFR-22: No long-lived AWS credentials in environment variables — Bedrock called via Lambda execution role

### 2.7 Performance
- NFR-23: API responses for session CRUD complete within 2 seconds
- NFR-24: LangSmith traces sent asynchronously — tracing must not block LLM call latency

---

## 3. Entities

| Entity | Description |
|---|---|
| UserMemory | One per user, persists across all sessions. Stores strengths, improvement areas, communication patterns. |
| Session | One per coaching run. Contains resume, job details, config (num_questions), status. |
| Question | One per generated interview question. Belongs to a Session. |
| CoachingTurn | One message in the back-and-forth coaching conversation. Belongs to a Question. |
| Answer | The final submitted STAR answer for a question. Belongs to a Question. |
| Feedback | Score and improvement suggestions for an answer. Belongs to an Answer. |

---

## 4. Out of Scope (Current Iteration)

| Feature | Reason deferred |
|---|---|
| GapAnalyzerAgent | Simplifies initial pipeline; slots in before InterviewPrepAgent when added |
| Multi-user auth | Single user now; user_id in schema makes auth easy to add later |
| AWS Transcribe | Web Speech API sufficient for single-user; easy to swap via useSpeechInput hook |
| Frontend cloud hosting | UI runs locally; CloudFront/S3 added when multi-user is implemented |
| LinkedIn / Indeed scraping | These sites block scraping; text paste is the fallback |
| Human-in-the-loop checkpoint | No gap analysis step means no review checkpoint needed yet |

---

## 5. Open Questions

| # | Question | Impact |
|---|---|---|
| OQ-01 | What score scale for answer feedback? (1–10, 1–5, letter grade?) | Affects Feedback entity, FeedbackAgent prompt, and UI display |
