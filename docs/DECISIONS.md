# Architecture Decision Records

Decisions made during the design and build of the Job Application Coach.
Each entry covers context, options considered, the choice made, and the rationale.
Use this as a reference when discussing the project in interviews.

---

## ADR-019 — AnswerCoachAgent deployed as Amazon Bedrock AgentCore Runtime

**Date:** 2026-05-05

**Context:**
AnswerCoachAgent is inherently multi-turn — the user submits an answer, the coach responds, the user refines, and so on until the answer is strong. This interactive back-and-forth doesn't fit the async batch model used for InterviewPrepAgent (Lambda + polling). We needed a hosting pattern designed for stateful, multi-turn agent conversations.

**Options considered:**
- **Lambda function (stateless)** — caller manages conversation history, passes full history each turn; simple but loses state guarantees and doesn't align with how AgentCore is meant to be used
- **LangGraph node in runner Lambda** — fits the existing pipeline but runner is async batch, not interactive; would require polling for each coaching turn (poor UX)
- **Amazon Bedrock AgentCore Runtime** — managed serverless hosting for AI agents; each `runtimeSessionId` is pinned to a dedicated microVM that stays alive across turns, keeping conversation history in-process

**Decision:** AgentCore Runtime (Container build, ARM64, HTTP protocol)

**Rationale:**
- AgentCore is purpose-built for stateful multi-turn agents — session pinning to a microVM eliminates the need to serialize/deserialize conversation history on every turn
- `runtimeSessionId` scopes each coaching conversation (one per question per session); history lives in-process, no DynamoDB reads per turn
- UserMemory loaded once from DynamoDB on the first turn and cached in-process for the session — no repeated reads
- AgentCore is a portfolio differentiator: demonstrates knowledge of AWS-native agent infrastructure beyond Lambda
- Container build (ARM64 via CodeBuild) is the recommended production pattern; avoids native package compatibility issues
- Clean separation: the runner Lambda handles batch graph execution (InterviewPrep), AgentCore handles interactive coaching — each tool does what it's good at

**Build approach:** CodeBuild ARM64 build + ECR. CDK creates an S3 asset from `lambda/answer_coach/`, CodeBuild sources from it, builds the Docker image, and pushes to ECR. A custom resource Lambda triggers the CodeBuild build during `cdk deploy`.

---

## ADR-018 — Three-entity data model: User / Job / Session

**Date:** 2026-05-04

**Context:**
The initial data model stored resume text, job details, and session metadata all on a single Session record. This meant users had to re-upload their resume and re-enter the job description every time they started a new practice session.

**Options considered:**
- **Single session table** — resume + job + session all in one record; simple but forces repeated uploads
- **Session + separate resume storage (S3 only)** — resume stays in S3, re-parsed on each run; avoids re-upload but re-parses every time
- **Three entities: User, Job, Session** — User owns the resume (upload once), Jobs are reusable postings, Sessions are practice runs against a job

**Decision:** Three DynamoDB tables — `users`, `jobs`, `sessions`

**Rationale:**
- A user realistically has one resume but applies to many jobs; each job can have multiple practice sessions — the three-entity model matches real usage
- Resume text is extracted once on upload and stored on the User record — no re-parsing overhead per session
- Jobs are persisted independently — user can start a second practice session for the same job without re-entering anything
- `POST /sessions` only needs a `job_id`; the runner Lambda fetches resume + job description at run time
- Schema is multi-user ready: all tables use `user_id` as partition key — adding auth later doesn't require a migration

---

## ADR-017 — Runner Lambda bundles graph/ and agents/ via _RunnerLocalBundler

**Date:** 2026-05-04

**Context:**
The runner Lambda (`lambda/runner/handler.py`) imports from `graph/` and `agents/`, which live at the project root. Lambda only sees what's in its deployment package — bare `Code.from_asset("lambda/runner")` would copy just the handler file, leaving those imports unresolvable at runtime.

**Options considered:**
- **Copy graph/ and agents/ into lambda/runner/ by hand** — brittle, requires keeping duplicates in sync
- **Symlinks** — not supported reliably on Windows or in CDK asset zipping
- **Docker-based bundling** — always available but requires Docker running locally; slow on Windows
- **_RunnerLocalBundler (same pattern as _ApiLocalBundler)** — pip-installs deps + shutil.copytree for each package needed; runs without Docker

**Decision:** `_RunnerLocalBundler` in the CDK stack, mirroring the existing `_ApiLocalBundler` pattern

**Rationale:**
- Consistent with how the API Lambda is already bundled — one pattern to understand
- No duplicate source files — graph/ and agents/ are copied into the output directory at deploy time, not stored there
- Falls back to Docker automatically if local bundling fails — same safety net as the API bundler
- Tests for the bundler (`tests/infra/test_bundler.py`) verify the correct packages are copied

---

## ADR-015 — `langchain.agents.create_agent` (LangChain 1.x) for all agents

**Date:** 2026-05-03 (revised 2026-05-08)

**Context:**
LangChain 1.x ships a top-level `create_agent` API in `langchain.agents` that builds a compiled LangGraph agent in one call: model + tools + system prompt + structured-output strategy + middleware. It supersedes the legacy `AgentExecutor` and replaces hand-rolled LCEL pipe chains. The first revision of this ADR adopted a *custom* `create_agent(model, tools, system_prompt)` factory in our agent modules — same name, but it returned a plain Python closure around `model.with_structured_output()` and reused none of the framework. That was a mistake and has been replaced.

**Options considered:**
- **LCEL pipe syntax** (`prompt | llm | parser`) — composable but lower-level; chains are implicit and harder to read
- **Direct `model.with_structured_output().invoke()`** — simple for one-off calls; loses agent-level tracing, no middleware path, no future tool support
- **Custom `create_agent` factory** — what we had originally; shadows the real LangChain API with a name-alike that does much less, misleading anyone familiar with LangChain 1.x
- **`from langchain.agents import create_agent`** — the real LangChain 1.x API; gives a compiled LangGraph agent with built-in middleware (`SummarizationMiddleware`, `HumanInTheLoopMiddleware`, custom `@before_model` / `@wrap_model_call` hooks), agent-level LangSmith spans, and a clean tool-calling loop when tools are added

**Decision:** Use `langchain.agents.create_agent` directly. Each agent module exposes a `build_*_agent()` factory that constructs a `ChatBedrockConverse` model, calls `create_agent(model=..., tools=[], system_prompt=..., response_format=ToolStrategy(Schema))`, and returns a thin callable that builds the user message and unwraps `result["structured_response"]`.

**Rationale:**
- Real framework, not a name-alike — readers familiar with LangChain 1.x see what they expect
- `response_format=ToolStrategy(Pydantic)` replaces the old `model.with_structured_output()` call; structured response is accessed via `result["structured_response"]`
- `ToolStrategy` (rather than `ProviderStrategy` or a bare schema) is explicit about going through tool calling, which is the path that works reliably across Bedrock + Claude
- Future agents that need tools (`MemoryUpdateAgent`, anything searching prior sessions) drop tools straight into the same call site — no refactor
- Future-proof for middleware: long coaching conversations in AgentCore can plug in `SummarizationMiddleware` without restructuring the agent
- Agent-level spans appear in LangSmith automatically — a portfolio talking point that the original custom factory was silently giving up

**Notes for future maintainers:**
- Empty `tools=[]` is intentional and supported — agents that need only structured output don't need tools
- Tests mock `create_agent` (the import) to return a stub agent whose `.invoke()` yields the expected `structured_response` — this isolates our integration glue from LangChain's internals

---

## ADR-016 — Async Lambda invocation with frontend polling

**Date:** 2026-05-03

**Context:**
The LangGraph agent pipeline involves multiple sequential LLM calls (InterviewPrep → AnswerCoach → Feedback → MemoryUpdate). This can take 30–90 seconds. Running this synchronously in a single Lambda invocation would block the HTTP connection and risk timeouts on the client side.

**Options considered:**
- **Synchronous Lambda** — simple, but blocks the HTTP connection for 30–90s; poor UX and risks client timeout
- **Lambda + SQS + separate consumer** — decoupled but adds operational complexity (queue, consumer Lambda, DLQ)
- **Async Lambda invocation + polling** — API Lambda returns `session_id` immediately, background Lambda runs the graph, frontend polls `GET /sessions/{id}/status`

**Decision:** Async Lambda invocation with frontend polling

**Rationale:**
- API response is immediate — no client timeout risk regardless of graph execution time
- Frontend polling via React Query `refetchInterval` is already in the design — natural fit
- No extra infrastructure — just two Lambda invocations (API + background runner)
- Session status (`pending` → `running` → `completed` | `error`) stored in DynamoDB — polling endpoint is a simple read
- Simpler than SQS for a single-user personal project; SQS can be added later if fan-out is needed

---

## ADR-013 — Long-term memory across sessions

**Date:** 2026-05-03

**Context:**
Each coaching session is independent by default — the system has no memory of past runs. This means feedback is generic rather than personalized, and users have to re-establish context every session. Long-term memory lets the system accumulate a model of the user over time.

**Options considered:**
- **No cross-session memory** — simple, stateless, but coaching never improves
- **Vector store (e.g. Pinecone, OpenSearch)** — semantic search over past sessions, powerful but operationally heavy
- **Structured DynamoDB record** — one UserMemory document per user, updated at session end by MemoryUpdateAgent

**Decision:** Structured UserMemory document in DynamoDB, updated by a dedicated MemoryUpdateAgent node

**Rationale:**
- Structured fields (strengths, improvement_areas, communication_patterns) are directly injectable into agent system prompts — no retrieval step needed
- MemoryUpdateAgent is a first-class LangGraph node — visible in traces, testable, replaceable
- DynamoDB is already in the stack — no new infrastructure
- Accumulates incrementally — each session adds insights without overwriting prior ones
- Simple enough to implement well; vector store retrieval adds complexity not justified for a single user
- Strong portfolio talking point: demonstrates understanding of stateful AI systems and memory patterns

---

## ADR-014 — Configurable number of questions (default 5)

**Date:** 2026-05-03

**Context:**
The number of interview questions to generate needs to be decided. Too many overwhelms the user; too few limits prep value.

**Decision:** Configurable per session, default 5

**Rationale:**
- 5 is a practical default — enough to cover key areas without a session taking hours
- Stored as `num_questions` on Session and passed into graph state — InterviewPrepAgent respects it via the prompt
- User can adjust before starting a session (e.g. 3 for a quick practice, 8 for deep prep)
- No code changes needed to change the default — it's a config value

---

## ADR-012 — Job description input: URL scraping with text fallback

**Date:** 2026-05-03

**Context:**
Users needed to copy-paste the full job description text into the UI, which is tedious. Most job postings are already online — users should be able to paste a URL instead. The system should also extract structured metadata (title, company) so agents have richer context and the UI can display a confirmation.

**Options considered:**
- **Text paste only** — simple, but poor UX
- **requests + BeautifulSoup scraping** — lightweight, works for most direct company career pages, fails on JS-rendered sites
- **Playwright headless browser** — works everywhere including LinkedIn/Indeed, but heavy dependency (~100MB), slower, complex Lambda packaging
- **Third-party scraping API** — reliable but adds external dependency and cost

**Decision:** requests + BeautifulSoup, extracting job_title + company + job_description, with graceful fallback to text paste

**Rationale:**
- Structured fields (title, company, description) give agents better context than a raw text blob — InterviewPrepAgent can reference the role and company in generated questions
- UI shows parsed title + company for user to confirm/edit before proceeding — catches bad parses early
- Covers the common case (direct company career pages) with minimal complexity
- Failing gracefully with a clear error message is better UX than silently returning garbage from a blocked page
- LinkedIn, Indeed, and Glassdoor actively block scraping — even Playwright hits auth walls; users of those sites paste text anyway
- Keeps Lambda package size small — no headless browser needed
- Easy to upgrade: job fetching logic is isolated in one module, swappable for Playwright or a scraping API later
- The UI accepts both URL and text — backend detects which it received; text input leaves title/company blank for user to fill in

---

## ADR-011 — Defer GapAnalyzerAgent to a later iteration

**Date:** 2026-05-03

**Context:**
The original pipeline included a GapAnalyzerAgent that compared resume vs. JD to identify missing skills, followed by a human review step where the user confirmed gaps before interview questions were generated. This added complexity: an extra agent, an extra LLM call, and a human-in-the-loop interrupt() checkpoint.

**Options considered:**
- **Keep gap analysis** — full pipeline as originally designed
- **Defer gap analysis** — start with InterviewPrepAgent reading resume + JD directly, add gap step later

**Decision:** Defer GapAnalyzerAgent

**Rationale:**
- Faster path to a working end-to-end demo — three agents instead of four
- InterviewPrepAgent can generate good questions directly from resume + JD without an explicit gap list
- Gap analysis is a valuable feature but not required for the core coaching loop to work
- The LangGraph graph is designed so GapAnalyzerAgent slots in before InterviewPrepAgent with minimal restructuring when added
- Reduces scope for the initial build while keeping the architecture extensible

---

## ADR-001 — LangGraph for agent orchestration

**Date:** 2026-05-03

**Context:**
Multiple AI agents need to run in sequence with shared state, a human approval step in the middle, and the ability to resume interrupted sessions. We needed a framework to wire this together rather than building it manually.

**Options considered:**
- **Custom orchestration** — plain Python, explicit state passing between agent functions
- **LangChain AgentExecutor** — LangChain's older agent loop abstraction
- **LangGraph StateGraph** — graph-based orchestration with typed state, built-in checkpointing, and interrupt() for human-in-the-loop

**Decision:** LangGraph StateGraph

**Rationale:**
- `interrupt()` gives us human-in-the-loop with zero custom logic — the graph pauses and resumes from the checkpoint
- Typed `TypedDict` state makes the data flowing between agents explicit and validated
- Built-in checkpointing (SqliteSaver / DynamoDB) means session persistence comes for free
- Each agent is a node — independently testable, replaceable, and visible in LangSmith traces
- LangChain AgentExecutor is legacy — LangGraph is the current recommended pattern

---

## ADR-002 — AWS Bedrock over direct Anthropic API

**Date:** 2026-05-03

**Context:**
The LLM calls need to be made from AWS Lambda. We needed to decide how to authenticate and call the model.

**Options considered:**
- **Anthropic API directly** — requires `ANTHROPIC_API_KEY`, billed separately, managed outside AWS
- **OpenAI API** — same trade-offs as Anthropic direct
- **AWS Bedrock** — access Claude and other models via AWS IAM, no separate API key, billing consolidated in AWS account

**Decision:** AWS Bedrock

**Rationale:**
- Lambda execution role already has AWS credentials — no secrets to manage for LLM calls
- Bedrock Guardrails integrates natively for content safety
- Consolidated AWS billing — no separate Anthropic account needed
- LangChain's `ChatBedrockConverse` is the up-to-date integration (uses the newer Converse API)
- Switching models (e.g. Haiku → Sonnet) is a single env var change

---

## ADR-003 — Claude Haiku 4.5 as default model

**Date:** 2026-05-03

**Context:**
We need a capable model for nuanced tasks (gap analysis, answer evaluation) but with low latency and cost, since multiple LLM calls happen per session.

**Options considered:**
- **Claude Sonnet / Opus via Bedrock** — strongest reasoning, higher cost and latency, access not available in our AWS account at project start
- **Amazon Nova Pro** — always available on Bedrock, moderate reasoning, weaker on nuanced analysis
- **Meta Llama 3.3 70B** — strong open model, always available, good instruction following
- **Claude Haiku 4.5 via Bedrock** — latest Haiku generation, significantly stronger than Haiku 3, fast, low cost, available in our account

**Decision:** Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`)

**Rationale:**
- Haiku 4.5 is a major step up from Haiku 3 — handles nuanced reasoning required for gap analysis and STAR coaching well
- Fastest latency of the options — important for the interactive voice coaching loop
- Cost-efficient for a multi-agent pipeline with 4+ LLM calls per session
- Model ID is in `BEDROCK_MODEL_ID` env var — can upgrade to Sonnet/Opus without code changes
- Prefer Claude over Nova Pro for this domain — better instruction following and structured output reliability

---

## ADR-004 — Guardrails as LangGraph nodes (not decorators or callbacks)

**Date:** 2026-05-03

**Context:**
We need input validation, output validation, and content safety checks at agent boundaries. There are several ways to implement this in a LangGraph + LangChain system.

**Options considered:**
- **LangChain callbacks** — hook into LLM call lifecycle, but hard to test and tightly coupled to LangChain internals
- **Python decorators on agent functions** — simple, but invisible in traces and hard to replace
- **Dedicated LangGraph nodes** — guardrails are first-class nodes in the graph, routed to explicitly

**Decision:** Dedicated LangGraph nodes

**Rationale:**
- Appear as their own spans in LangSmith — you can see guardrail timing and outcomes in traces
- Independently unit-testable — input a state dict, assert the output
- Can route to an error node on failure — clean error handling without try/except everywhere
- Replaceable without touching agent logic — swap Bedrock Guardrails for a different provider by changing one node
- Makes the guardrail logic explicit in the graph definition, not hidden in callbacks

---

## ADR-005 — Browser Web Speech API over AWS Transcribe

**Date:** 2026-05-03

**Context:**
The AnswerCoach step requires voice input so users can practice speaking their answers aloud, not just typing.

**Options considered:**
- **AWS Transcribe** — high accuracy, cross-browser, streaming support, costs per minute of audio
- **Browser Web Speech API** — free, zero backend, Chrome/Edge only, accuracy depends on browser

**Decision:** Browser Web Speech API (for now)

**Rationale:**
- This is a single-user personal tool — Chrome/Edge-only limitation is acceptable
- Zero cost, zero backend complexity — no audio streaming infrastructure needed
- Fast to implement, can validate the UX before investing in a paid transcription service
- Easy to swap: the React component isolates the STT logic in a custom hook (`useSpeechInput`) — replacing the implementation with AWS Transcribe later is a one-file change
- Graceful degradation: falls back to text input if `SpeechRecognition` is unavailable

---

## ADR-006 — Single user now, multi-user ready schema

**Date:** 2026-05-03

**Context:**
Building auth is complex and not the learning focus of this project. But the data model should not need a rewrite to add users later.

**Options considered:**
- **Fully stateless** — no user concept at all, sessions not tied to a user
- **Hardcoded single user** — user_id = "default" baked into the logic
- **user_id in schema, no auth enforcement** — user_id field exists in all models, hardcoded to a constant for now

**Decision:** user_id in schema, no auth enforcement now

**Rationale:**
- Adding auth later only requires: an auth Lambda layer + a lookup to resolve user_id from a JWT token
- DynamoDB access patterns (PK = user_id, SK = session_id) are correct from day one
- No wasted migration work — the schema doesn't change when auth is added
- Keeps current scope tight — no Cognito, no token management, no login page to build

---

## ADR-007 — FastAPI over Flask or plain Lambda handlers

**Date:** 2026-05-03

**Context:**
We need a REST API layer in Lambda to handle session CRUD and graph invocation.

**Options considered:**
- **Plain Lambda handlers** — minimal, but routing and request parsing handled manually
- **Flask** — mature, simple, but no async support, less modern
- **FastAPI** — async, automatic OpenAPI docs, Pydantic integration, type-safe request/response models

**Decision:** FastAPI (via Mangum adapter for Lambda)

**Rationale:**
- Pydantic v2 models shared between FastAPI request/response schemas and LangGraph state — one source of truth
- Async support matches async LangGraph invocation (ainvoke, astream)
- Auto-generated OpenAPI docs useful for frontend development
- Mangum adapter makes FastAPI work seamlessly in Lambda with zero changes

---

## ADR-008 — SqliteSaver (dev) + DynamoDB checkpointer (prod)

**Date:** 2026-05-03

**Context:**
LangGraph requires a checkpointer to persist graph state between interrupt() pauses and to support session resumption.

**Options considered:**
- **MemorySaver** — in-memory, lost on Lambda cold start, useless for persistence
- **SqliteSaver** — file-based, perfect for local development, not suitable for Lambda (ephemeral filesystem)
- **DynamoDB checkpointer** — persistent, serverless, scales with Lambda

**Decision:** SqliteSaver for local dev, DynamoDB checkpointer for prod

**Rationale:**
- `ENVIRONMENT` env var switches between the two — same code, different checkpointer instantiation
- SqliteSaver needs zero AWS setup for local development
- DynamoDB is already in the stack for session storage — natural fit for checkpoint storage too
- LangGraph's checkpointer interface is the same for both — no agent code changes needed

---

## ADR-009 — LangSmith for evals (not a custom eval framework)

**Date:** 2026-05-03

**Context:**
We need to evaluate agent output quality — are the identified gaps accurate? Are the questions relevant? Is the feedback useful?

**Options considered:**
- **Custom eval scripts** — compare outputs against golden examples, flexible but lots of boilerplate
- **LangSmith evals** — built-in eval framework, LLM-as-judge support, dataset management, CI integration

**Decision:** LangSmith evals

**Rationale:**
- LangSmith is already in the stack for tracing — evals use the same SDK and dashboard
- LLM-as-judge evaluators are well-suited for subjective quality metrics (question relevance, feedback specificity)
- Dataset versioning built in — golden examples stored and versioned in LangSmith, not in the repo
- CI integration is straightforward — `langsmith eval run` command in GitHub Actions
- Less boilerplate than building a custom framework for the same outcome

---

## ADR-010 — GitHub Actions for CI/CD

**Date:** 2026-05-03

**Context:**
Need automated testing and deployment. The code lives on GitHub.

**Options considered:**
- **AWS CodePipeline** — native AWS, more complex setup, less portable
- **GitHub Actions** — lives alongside the code, large ecosystem of actions, free tier sufficient

**Decision:** GitHub Actions

**Rationale:**
- Code is on GitHub — keeping CI/CD in the same place reduces context switching
- OIDC integration with AWS means no long-lived AWS credentials stored in GitHub secrets
- Separate workflows for PR checks, dev deploy, and prod deploy gives clear promotion gates
- Free tier covers the build minutes needed for this project
