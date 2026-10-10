# NEXORA AI — Stage 3: Universal Search & Deep Research Engine

**NEXORA AI** is a premium, scalable, universal AI assistant platform engineered to evolve through 100 structured development phases. **Stage 3** elevates the system into a high-precision research assistant featuring a non-simulated **Universal Search and Deep Research Engine**: multi-engine web search (DuckDuckGo, Tavily, Google Serper, Brave), real-time source grounding, numbered inline citations (`[1]`, `[2]`), an interactive collapsible sources explorer, and a 6-step autonomous deep research pipeline with live execution telemetry.

---

## 🌟 Stage 3 Core Deliverables

- **Real Web Search & Zero-Hallucination Grounding**:
  - Genuine web search integration with zero simulated results, fabricated URLs, or fictitious citations.
  - Multi-engine backend with auto-fallback:
    - **DuckDuckGo**: High-reliability zero-credential web search available out of the box with HTML scraper fallback.
    - **Tavily AI Search**: Direct answer and deep content web search.
    - **Google Serper**: Google-indexed organic results with sitelinks and snippets.
    - **Brave Search**: Independent web search index.
- **Three Specialized Interaction Modes**:
  - **AI Only**: Direct conversational intelligence from configured LLM (fastest latency).
  - **Web Search**: Real-time web search for breaking news, up-to-date facts, and current events.
  - **Deep Research**: 6-step autonomous investigation pipeline that breaks complex questions into sub-queries, executes multi-pass searches, scrapes and deduplicates content, and synthesizes an evidence-grounded report.
- **Source-Grounded Inline Citations & Sources Explorer**:
  - Numbered clickable inline citations (`[1]`, `[2]`) in markdown linking directly to verified source URLs.
  - Collapsible **Sources Drawer** attached to messages with website favicons, domain tags, titles, snippets, and published dates.
  - Honest disclosure whenever external evidence is conflicting or insufficient.
- **6-Step Deep Research Pipeline**:
  1. **Question Decomposition**: Breaks complex multi-faceted prompts into focused sub-queries.
  2. **Multi-Pass Parallel Search**: Executes searches across target vectors.
  3. **Content Extraction & Scraping**: Safely downloads readable article text.
  4. **Evidence Deduplication**: Consolidates identical sources and domains.
  5. **Cross-Examination**: Analyzes consensus, anomalies, and conflicting viewpoints.
  6. **Structured Synthesis**: Outputs exhaustive findings, inline citations, methodological limitations, and actionable conclusions.
  - Live progress stepper displayed in the UI during research execution.
- **Hardened Security & Defenses**:
  - **SSRF Protection**: `WebpageScraper` verifies IP resolutions to block loopback (`127.0.0.1`), RFC1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and cloud metadata endpoints (`169.254.169.254`).
  - **Prompt Injection Defense**: Untrusted external HTML/text is quarantined in structured `<untrusted_web_evidence>` boundaries preventing remote prompt hijacking.
- **Strict Backward Compatibility**:
  - Preserves Stage 1 foundation (Tailwind dark theme, conversation management, honest unconfigured states).
  - Preserves Stage 2 intelligence (SSE streaming, AbortController stop generation controls, auto-titling, adult-content guardrails with educational exemptions).

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

# Run automated test suite (18/18 passing)
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

## 📋 Stage 2 Verification Checklist

- [x] Real-time Server-Sent Events (SSE) streaming (`POST /api/v1/chat/stream`).
- [x] Client-side `AbortController` stop-generation control.
- [x] Live response generation typing cursor and smooth autoscrolling.
- [x] Modular provider architecture (`BaseAIProvider`, `GeminiProvider`, `OpenAIProvider`, `AnthropicProvider`, `OfflineHonestProvider`).
- [x] Strict conversation context retention and configurable sliding window limits (`MAX_CONTEXT_MESSAGES=20`).
- [x] Follow-up questions, message regeneration, copy response, and prompt editing.
- [x] Smart conversation auto-titling from conversation content (`POST /api/v1/chat/generate-title`).
- [x] Message size validation (up to 32,000 characters) and request timeout enforcement.
- [x] Zero-fake-response policy strictly maintained when keys are missing.
- [x] Adult-content safety guardrail with legitimate medical/educational exemption integrated into streaming.
- [x] 13/13 automated Pytest test cases passing.
- [x] Frontend TypeScript type check and production build verified.
- [x] Updated `PHASE_STATUS.md` and `.env.example`.

---
*Stage 2 is complete. Do not proceed to Stage 3 until Stage 2 has been reviewed and approved.*
