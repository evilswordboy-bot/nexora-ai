# NEXORA AI — Stage 12: Intelligent Model Routing Engine

**NEXORA AI** is a premium, scalable, universal AI assistant platform engineered to evolve through 100 structured development phases. **Stage 12** introduces the **Intelligent Model Routing & Cost Control Engine**: a capability-aware, budget-enforcing orchestration service that dynamically selects among verified AI providers (`gemini`, `openai`, `anthropic`) based on task classification (`coding`, `image_understanding`, `document_analysis`, `deep_research`, `translation`, `voice`, `reasoning`, `general_chat`), required capabilities, context window limits, latency, and cost preferences (`quality_first`, `balanced`, `speed_first`), with bounded fallback recovery and privacy-preserving observability.

---

## 🌟 Stage 12 Core Deliverables

- **Modular Provider & Model Registry (`ProviderModelRegistry`)**:
  - Registers model capabilities, context window limits (`128K` to `2M` tokens), quality tiers (`frontier`, `balanced`, `fast`), typical latency, timeouts, and published per-1K token pricing metadata.
  - Supports dynamically adding (`POST /api/v1/routing/models`) and removing (`DELETE /api/v1/routing/models/{model_id}`) models at runtime without rewriting application code.
  - Strictly protects credentials in backend environment variables and never exposes API keys in registry or telemetry payloads.
- **Capability-Aware Intelligent Routing (`IntelligentModelRouter`)**:
  - Classifies prompts into `general_chat`, `coding`, `deep_research`, `document_analysis`, `image_understanding`, `translation`, `voice`, and `reasoning`.
  - Verifies required capabilities before dispatch (e.g., excluding text-only models like `o3-mini` or `claude-3-5-haiku-20241022` when `image_understanding` is required).
  - Supports user-selectable `quality_first`, `balanced`, and `speed_first` routing modes.
- **Bounded Fallback & Reliability**:
  - Automatically recovers from provider rate limits (`HTTP 429`), timeouts, and upstream outages (`503`) by iterating through a bounded fallback chain (`max_fallbacks`) without infinite retry loops.
  - Honest unconfigured fallback: never pretends an unconfigured model is available.
- **Cost & Performance Controls + Security**:
  - Estimates prompt/completion tokens and USD cost with transparent disclaimers (`is_exact_cost: false`).
  - Enforces configurable `daily_spending_limit_usd` and `per_request_max_cost_usd` budgets (automatically downgrading to a lower-cost model or blocking over-budget requests).
  - Blocks prompt-injection attempts trying to override routing security rules or bypass budget limits (`prompt_injection_override_blocked: true`).
- **Model Router & Observability Studio UI**:
  - Accessible via the top navigation bar (**Model Router** tab) featuring 3-mode routing preference cards, budget controls, an interactive Route Simulator & Live Dispatch tester, model capability cards, and privacy-preserving usage telemetry.

---

## 🌟 Stage 11 Core Deliverables

- **Adaptive Problem Decomposition (`AdvancedReasoningEngine`)**:
  - Classifies incoming requests by complexity (`simple`, `moderate`, `complex`), required tools, uncertainty level, and risk level.
  - Answers simple questions directly without unnecessary planning overhead.
  - Decomposes multi-step tasks into structured `ReasoningSubtask` pipelines with explicit `depends_on` dependencies, `expected_output`, and `completion_criteria`.
  - Tracks live subtask and plan states (`PLANNED`, `IN PROGRESS`, `BLOCKED`, `REVIEWING`, `COMPLETE`, `CANCELLED`).
  - Supports full plan inspection, goal/parameter revision (`/revise`), and cancellation (`/cancel`).
- **Modular Tool-Assisted Execution (`ToolRegistry`)**:
  - Safe AST-based mathematical expression evaluator (`calculator`) supporting arithmetic, powers, roots, trigonometry, logarithms, and percentages without `eval()`.
  - Integrated real tool handlers for `web_search` (Stage 3), `document_retrieval` (Stage 4), `fact_check` (Stage 5), `translation` (Stage 6), `realtime_pulse` (Stage 8), and consequential tools (`delete_document`, `dispatch_external_message`).
  - Enforces parameter schema validation, execution timeouts, and `<untrusted_tool_output>` prompt-injection quarantine.
- **Verification, Retry Recovery & Safety Permissions**:
  - Evaluates each subtask result against completion criteria (`REVIEWING` -> `COMPLETE`) and retries recoverable failures within configurable limits.
  - Enforces least-privilege access: high-risk consequential actions automatically pause in `BLOCKED` state and require explicit user authorization (`/approve`) before execution.
- **Interactive Reasoning Studio UI**:
  - Accessible via the top navigation bar (**Reasoning** tab) with preset scenarios, live subtask status badges, tool execution telemetry logs, inline approval gates, plan revision controls, and expandable execution audit summaries.

---

## 🌟 Stage 10 Core Deliverables

- **Unified Conversation & Context Grounding**:
  - Combined conversation interface supporting simultaneous text prompt, multiple image attachments (PNG, JPG, WEBP), and active document vault attachments in a single query turn.
  - Context grounding seamlessly merges Lexical BM25 RAG chunks, OCR textual extracts, and web search evidence within strict prompt-injection security envelopes.
  - Conversation persistence preserves citations, document grounding badges, language directives, and model provenance across chat sessions.
- **Cross-Engine Safety Guardrail Consistency**:
  - Unified enforcement of the `AdultContentSafetyGuard` across text chat prompts, multilingual translations, voice text-to-speech audio synthesis,image OCR text, and reasoning plans.
  - Zero tolerance for severe harm patterns while preserving genuine medical, anatomical, and educational inquiries.
- **Centralized Subsystem Diagnostics & Health Architecture**:
  - Enhanced `/api/v1/health` providing real-time subsystem operational diagnostics across `chat`, `search_research`, `documents_vault`, `fact_checking`, `multilingual`, `voice`, `realtime_feed`, `vision_intelligence`, and `reasoning_engine`.
  - Comprehensive provider configuration transparency (`gemini`, `openai`, `anthropic`, `offline`).
- **Comprehensive Quality Assurance & Zero Regression**:
  - 67/67 automated backend Pytest tests passing cleanly across all 11 engine test suites.
  - Production TypeScript & Vite frontend build passing with 0 errors.
  - Elimination of broken navigation, duplicate components, or conflicting client states.

- **Multimodal Image Upload & Technical Verification**:
  - Drag-and-drop and file selection for PNG, JPG, JPEG, and WEBP formats up to 10MB per image.
  - Image thumbnails preview strip with individual deletion controls and upload progress indicators.
  - Technical container verification via Pillow (`width`, `height`, `format`, `color_mode`, simplified `aspect_ratio`).
  - Rejection of corrupted or unsupported image binaries without silent failure.
- **Multimodal Visual Reasoning & Analysis**:
  - End-to-end integration with configured vision-capable models (Google Gemini `gemini-1.5-flash`/`gemini-1.5-pro`, OpenAI `gpt-4o`/`gpt-4o-mini`, and Anthropic `claude-3-5-sonnet`).
  - Specialized visual analysis pipelines for:
    - **General Scene & Objects**: Comprehensive visual elements and context.
    - **UI Design & UX Hierarchy**: Layout, button states, typography, accessibility, and navigation trees.
    - **Charts, Trends & Data Points**: Axes, numerical values, legends, and trend insights.
    - **Technical Schematics & Circuits**: Wiring lines, pinouts, component designations, and logic diagrams.
    - **Equations & Deep Text**: Mathematical expressions, chemical formulas, and multilingual text.
- **Prompt-Injection Quarantined Optical Character Recognition (OCR)**:
  - Local text extraction via PyTesseract with automatic fallback.
  - Strict security defense: all extracted visual text is quarantined within `<untrusted_visual_content>` security boundaries with escaping against XML breakout attacks.
  - Pre-extracted OCR evidence automatically augments multimodal LLM prompts for maximum accuracy.
- **Side-by-Side Visual Comparison & Diff**:
  - Compares design revisions, screenshots, or document scans (e.g. Design v1 vs Design v2).
  - Highlights shared design baseline, resolution variance, textual differences, and layout alterations.
- **Vision Intelligence Studio Workspace**:
  - Accessible via top navigation bar (**Chat & Search**, **Vision Studio**, **Documents Vault**, **Fact Check**, **Translate**, **Live Feed**).
  - 3 interactive panels:
    1. **Visual Analysis**: Multi-image inspector with customizable categories and inquiry prompts.
    2. **OCR Extraction**: Dedicated high-contrast text extractor with character/word metrics and copy controls.
    3. **Image Comparison**: Dual upload canvas for side-by-side visual difference synthesis.

- **Live Information Retrieval & Freshness Tracking**:
  - Reusable backend connector dispatching queries across web search and open data sources.
  - Returns timestamped source URLs, domains, and publication dates with freshness indicators (*"Retrieved just now"*, *"Retrieved 4m ago (Cached)"*).
  - Explicit provenance: distinguishes live retrieved information from base model weights.
  - Zero mock data: reports unavailable or unindexed queries honestly without fabricating metrics or dates.
- **Knowledge Refresh & Continuous Topic Surveillance**:
  - Save research topics or specific URLs with configurable surveillance intervals (15 to 1440 minutes).
  - **SHA-256 Content Fingerprinting**: Computes cryptographically stable hashes of fetched content to detect meaningful updates while ignoring minor layout noise.
  - Tracks `last_checked_at`, `next_check_at`, content hashes, change counts, and concise update summaries.
  - On-demand **Check Now** manual refresh triggers.
- **In-App Change Notifications & Alert History**:
  - Generates alert notifications when monitored topics undergo meaningful content alterations.
  - Full notifications lifecycle: list unread alerts, mark-all-read, and clear notification history.
  - Clickable source citations directly embedded into update alerts.
- **Dedicated Live Feed Workspace**:
  - Accessible via top navigation bar (**Chat & Search**, **Documents Vault**, **Fact Check**, **Translate**, **Live Feed**).
  - 3 intuitive views:
    1. **Live Retrieval**: Category filter (News, Tech, Research, Markets, Announcements) with instant web fetch & AI synthesis.
    2. **Monitored Feeds**: Card-based registry of active monitored topics, intervals, and change counters.
    3. **Alerts & History**: Unread badges and time-stamped diff digests.
- **Reliability, SSRF & Instruction Protection**:
  - Built-in SSRF protection rejecting private/loopback IP resolution (`localhost`, `10.0.0.0/8`, `192.168.0.0/16`, `169.254.0.0/16`).
  - Strict system prompt boundaries isolating live external text to prevent indirect prompt injection.
  - 5-minute memory cache with idempotent refresh execution.

---

## 📁 Architecture Overview

```
nexora-ai/
├── PHASE_STATUS.md            # 100-Phase Roadmap (Phases 1 & 2 COMPLETE)
├── README.md                  # Comprehensive Documentation
├── .env.example               # Environment variables template
├── backend/
│   ├── .env.example
│   ├── .env                   # Local development configuration
│   ├── requirements.txt       # FastAPI, Uvicorn, Pydantic, HTTPX, Pytest
│   ├── run.py                 # Backend launcher script
│   ├── app/
│   │   ├── config.py          # App settings, timeouts & context limits
│   │   ├── main.py            # FastAPI entry point & CORS configuration
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic v2 models with size validation
│   │   ├── core/
│   │   │   ├── rate_limiter.py# Sliding-window rate limiter (60 req/min)
│   │   │   └── safety.py      # Adult content guardrail with medical exemption
│   │   ├── services/
│   │   │   ├── ai_service.py  # Unified multi-provider orchestrator
│   │   │   ├── providers/     # Modular provider implementations
│   │   │   │   ├── base.py              # BaseAIProvider abstract interface
│   │   │   │   ├── gemini_provider.py   # Gemini completions & SSE
│   │   │   │   ├── openai_provider.py   # OpenAI completions & SSE
│   │   │   │   ├── anthropic_provider.py# Anthropic completions & SSE
│   │   │   │   └── offline_provider.py  # Honest unconfigured guidance
│   │   │   ├── conversation_service.py # In-memory conversation persistence
│   │   │   └── tools_registry.py       # Extensible tools framework
│   │   └── api/
│   │       └── v1/
│   │           ├── health.py  # Health and provider status endpoints
│   │           ├── chat.py    # Standard, streaming, and titling endpoints
│   │           └── conversations.py # Conversation REST endpoints
│   └── tests/
│       ├── test_health.py     # Health endpoint tests
│       ├── test_safety.py     # Content safety & medical exemption tests
│       ├── test_conversations.py # CRUD and unconfigured state tests
│       └── test_stage2_engine.py # Streaming, titling, size validation tests
└── frontend/
    ├── package.json           # React 18, TypeScript, Tailwind, Lucide Icons
    ├── vite.config.ts         # Vite bundler with /api proxy to FastAPI
    ├── tailwind.config.js     # Midnight/cyan/violet design system
    ├── tsconfig.json          # TypeScript strict configuration
    └── src/
        ├── App.tsx            # Main application layout
        ├── context/
        │   └── ChatContext.tsx# Reactive state, SSE stream handler, AbortController
        ├── services/
        │   ├── api.ts         # Backend API client with SSE ReadableStream parser
        │   └── storage.ts     # LocalStorage persistence & backup import/export
        ├── components/
        │   ├── layout/
        │   │   ├── Header.tsx # Connectivity badge, status pill, settings
        │   │   └── Sidebar.tsx# Collapsible history with search & rename
        │   ├── chat/
        │   │   ├── ChatArea.tsx       # Message list with autoscroll
        │   │   ├── WelcomeScreen.tsx  # Stage 2 hero branding & quick prompt cards
        │   │   ├── MessageItem.tsx    # Markdown renderer, streaming cursor, actions
        │   │   ├── MessageInput.tsx   # Textarea with Send/Stop & token estimation
        │   │   └── MarkdownRenderer.tsx# Syntax highlighting & code blocks
        │   ├── modals/
        │   │   ├── SettingsModal.tsx  # API keys, model picker, temperature
        │   │   ├── SetupGuideModal.tsx# Stage 2 architecture guide
        │   │   └── DeleteConfirmModal.tsx # Safe deletion dialog
        │   └── ui/
        │       ├── CodeBlock.tsx      # Code preview with 1-click copy
        │       └── Toast.tsx          # Real-time user feedback notifications
```

---

## 🚀 Quick Start Guide

### Step 1: Start the Backend Server

```bash
cd backend

# Run automated test suite (30/30 passing)
python -m pytest tests -v

# Launch the FastAPI server
python run.py
```
Backend runs at `http://127.0.0.1:8000` (API documentation at `http://127.0.0.1:8000/docs`).

---

### Step 2: Start the Frontend Application

In a separate terminal:

```bash
cd frontend

# Build check
npm run build

# Start the Vite development server
npm run dev
```
Frontend runs at `http://localhost:5173`.

---

## 🔑 AI Provider & Search Engine Configuration

NEXORA AI operates on an **honest provider architecture**:
- **Web Search**: Works out of the box with DuckDuckGo (zero API key needed). You can also configure Tavily, Serper, or Brave.
- **AI Models**: Connect Google Gemini, OpenAI, or Anthropic Claude. If unconfigured, the UI clearly guides the user on obtaining credentials.

### Method A: Client Settings Modal (Instant)
1. Open the web interface at `http://localhost:5173`.
2. Click the **Gear icon (Settings)** in the top-right header.
3. In **AI Providers & Keys**, enter your Gemini, OpenAI, or Anthropic API key.
4. In **Search & Research**, select your preferred search engine (DuckDuckGo, Tavily, Serper, or Brave) and enter keys if applicable.
5. Click **Save Settings**. Your keys are saved strictly in your local browser session and utilized for real streaming queries.

### Method B: Backend `.env` File
Configure `backend/.env`:
```env
# AI Models
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Universal Search & Deep Research
DEFAULT_SEARCH_ENGINE=auto
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...
BRAVE_API_KEY=BSA...
```

DEFAULT_PROVIDER=auto
DEFAULT_MODEL=gemini-1.5-flash

MAX_CONTEXT_MESSAGES=20
MAX_MESSAGE_CHARS=32000
REQUEST_TIMEOUT_SECONDS=45.0
```
Restart `python run.py` to pick up server-side keys.

---

## 🧪 Verification & Automated Testing

Run the full Pytest test suite:
```bash
cd backend
python -m pytest tests -v
```

Expected output:
```text
tests/test_conversations.py::test_conversations_crud PASSED              [  7%]
tests/test_conversations.py::test_honest_unconfigured_chat_response PASSED [ 15%]
tests/test_health.py::test_root_endpoint PASSED                          [ 23%]
tests/test_health.py::test_health_endpoint PASSED                        [ 30%]
tests/test_health.py::test_providers_status_honest_state PASSED          [ 38%]
tests/test_safety.py::test_explicit_sexual_content_blocked PASSED        [ 46%]
tests/test_safety.py::test_educational_medical_content_allowed PASSED    [ 53%]
tests/test_safety.py::test_benign_coding_prompt_allowed PASSED           [ 61%]
tests/test_stage2_engine.py::test_streaming_chat_endpoint_unconfigured PASSED [ 69%]
tests/test_stage2_engine.py::test_title_generation_endpoint PASSED       [ 76%]
tests/test_stage2_engine.py::test_message_size_validation PASSED         [ 84%]
tests/test_stage2_engine.py::test_context_window_truncation PASSED       [ 92%]
tests/test_stage2_engine.py::test_streaming_safety_guardrail PASSED      [100%]
============================= 13 passed in 0.78s ==============================
```

Frontend production build check:
```bash
cd frontend
npm run build
```
Builds cleanly with zero TypeScript or bundling errors in under 4 seconds.

---

## 📋 Stage 13: Persistent Memory Engine & Privacy Checklist

- [x] **SQLite Persistent Storage (`data/memory/nexora_memory.db`)**: Schema migration tracking (`schema_migrations`), automatic fallback recovery to `:memory:` if disk path is unavailable, and portable JSON backup export (`GET /api/v1/memory/export`).
- [x] **Authenticated At-Rest Encryption (`enc:v1:...`)**: Standard-library `HMAC-SHA256` stream cipher encrypts and verifies integrity of saved memory facts on disk.
- [x] **Modular Memory Categories**: Separate storage and filtering for `preferences`, `profile`, `project_context`, `conversation_summaries`, and volatile `temporary_context` (RAM only, never written to disk).
- [x] **Full User Lifecycle Controls**: Create, view, search by relevance, edit, pin (`pinned`), delete individual memories, or clear all memories via `/api/v1/memory/*` and **Memory Center (`MemoryStudio.tsx`)**.
- [x] **Natural-Language Memory Commands**: Supports `"Remember this..."`, `"Forget this..."`, `"What do you remember about me?"`, and requires explicit user confirmation (`requires_confirmation: true`) when intent is ambiguous.
- [x] **Multi-User Isolation & Privacy Guard**: Strict `user_id` scoping prevents cross-user memory access; Sensitive PII/Secret Guard blocks API keys, passwords, SSNs, and payment card numbers from being stored; supports Temporary Chat mode (`temporary_chat: true`) and `<user_memory_context>` prompt-injection quarantine.
- [x] **82/82 Automated Pytest Tests Passing** across Stages 1–13 (`tests/test_stage13_memory.py`).
- [x] **Frontend TypeScript & Vite Production Build Verified** (`0 errors`).

---
*Stage 13 is complete. Do not proceed to Stage 14 until Stage 13 has been reviewed and approved.*
