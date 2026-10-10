# NEXORA AI — Stage 1: Masterpiece Foundation

**NEXORA AI** is a premium, scalable, universal AI assistant platform engineered to evolve through 100 structured development phases. Stage 1 establishes the production-grade foundation: responsive dark theme workspace, session/conversation state management, modular AI provider dispatcher with honest setup validation, content safety guardrails, and FastAPI backend architecture.

---

## 🌟 Stage 1 Core Deliverables

- **Sophisticated Dark Theme Workspace**: Midnight navy (`#0B0F19`), electric cyan (`#06B6D4`), and subtle violet gradients (`#8B5CF6`) built with React, Vite, TypeScript, and Tailwind CSS.
- **Collapsible Responsive Navigation**:
  - Auto-categorized conversation history (**Today**, **Yesterday**, **Previous 7 Days**, **Older**).
  - Search filter across all stored conversations.
  - Inline conversation renaming and modal-confirmed deletion.
  - Full mobile navigation drawer.
- **Genuine, Zero-Mock Provider Dispatcher**:
  - **No Fake AI Responses**: If no provider API key is configured on server or in client settings, the system displays an honest setup guide with 1-click configuration.
  - Ready for **Google Gemini** (`gemini-1.5-flash`, `gemini-1.5-pro`), **OpenAI** (`gpt-4o`, `gpt-4o-mini`), and **Anthropic** (`claude-3-5-sonnet`).
  - Supports passing client-side session keys directly via Settings without committing them to git.
- **Adult-Content Safety Guardrail**:
  - Dual-evaluator content safety filter that blocks sexually gratuitous erotica and pornography.
  - **Educational & Medical Exemption**: Deliberately permits legitimate anatomical, biological, reproductive health, and medical inquiries.
- **FastAPI Engine**:
  - Sliding-window in-memory rate limiter per IP.
  - Pydantic v2 data models with UTC timestamp serialization.
  - In-memory conversation persistence and REST CRUD endpoints.
  - Automated test suite verifying health, conversations CRUD, honest setup states, and safety filter rules.
- **100-Phase Progression Matrix**:
  - Complete master roadmap tracked in [`PHASE_STATUS.md`](./PHASE_STATUS.md). Stage 1 is marked `COMPLETE` upon automated verification; subsequent phases remain `NOT STARTED` awaiting sequential approval.

---

## 📁 Project Architecture

```
nexora-ai/
├── PHASE_STATUS.md            # 100-Phase Roadmap & Status Tracker
├── README.md                  # Comprehensive Documentation & Setup Guide
├── .gitignore                 # Strict secrets and build artifact exclusions
├── .env.example               # Environment variables template
├── backend/
│   ├── .env.example
│   ├── .env                   # Local development configuration
│   ├── requirements.txt       # FastAPI, Uvicorn, Pydantic, HTTPX, Pytest
│   ├── run.py                 # Backend launcher script
│   ├── app/
│   │   ├── config.py          # App configuration & provider key detection
│   │   ├── main.py            # FastAPI entry point & CORS configuration
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic request/response models
│   │   ├── core/
│   │   │   ├── rate_limiter.py# Sliding-window rate limiter (60 req/min)
│   │   │   └── safety.py      # Adult content guardrail with medical exemption
│   │   ├── services/
│   │   │   ├── ai_service.py  # Multi-provider dispatcher & honest fallback
│   │   │   ├── conversation_service.py # In-memory CRUD storage
│   │   │   └── tools_registry.py       # Modular tool execution framework
│   │   └── api/
│   │       └── v1/
│   │           ├── health.py  # Health and provider status endpoints
│   │           ├── chat.py    # Chat completions endpoint
│   │           └── conversations.py # Conversation REST endpoints
│   └── tests/
│       ├── test_health.py     # Health endpoint and provider introspection tests
│       ├── test_safety.py     # Explicit blocking vs medical exemption tests
│       └── test_conversations.py # CRUD and honest unconfigured state tests
└── frontend/
    ├── package.json           # React 18, TypeScript, Tailwind, Lucide Icons
    ├── vite.config.ts         # Vite bundler with /api proxy to FastAPI
    ├── tailwind.config.js     # Midnight/cyan/violet design system
    ├── tsconfig.json          # TypeScript strict configuration
    └── src/
        ├── App.tsx            # Main application layout
        ├── context/
        │   └── ChatContext.tsx# Reactive state management & storage sync
        ├── services/
        │   ├── api.ts         # Backend API client
        │   └── storage.ts     # LocalStorage persistence & backup import/export
        ├── components/
        │   ├── layout/
        │   │   ├── Header.tsx # Connectivity badge, status pill, settings
        │   │   └── Sidebar.tsx# Collapsible history with search & rename
        │   ├── chat/
        │   │   ├── ChatArea.tsx       # Message list with autoscroll
        │   │   ├── WelcomeScreen.tsx  # Hero branding & quick prompt cards
        │   │   ├── MessageItem.tsx    # Markdown renderer & action controls
        │   │   ├── MessageInput.tsx   # Textarea with Enter/Shift+Enter & counter
        │   │   └── MarkdownRenderer.tsx# Syntax highlighting & code blocks
        │   ├── modals/
        │   │   ├── SettingsModal.tsx  # API key, model selection, temperature
        │   │   ├── SetupGuideModal.tsx# Architecture guide & free key instructions
        │   │   └── DeleteConfirmModal.tsx # Safe deletion dialog
        │   └── ui/
        │       ├── CodeBlock.tsx      # Code preview with 1-click copy
        │       └── Toast.tsx          # Real-time user feedback notifications
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js** >= 18 (`v26.x` supported)
- **Python** >= 3.10 (`3.13.x` supported)

---

### Step 1: Start the Backend Server

```bash
cd backend

# 1. Install dependencies (if not already installed)
python -m pip install -r requirements.txt

# 2. Run automated backend test suite
python -m pytest tests

# 3. Launch the FastAPI server
python run.py
```
The FastAPI backend will start on **`http://127.0.0.1:8000`**.
Interactive API documentation will be available at **`http://127.0.0.1:8000/docs`**.

---

### Step 2: Start the Frontend Application

In a separate terminal:

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start the Vite development server
npm run dev
```
The React frontend will start on **`http://localhost:5173`**.

---

## 🔑 AI Provider Configuration

NEXORA AI operates on an **honest provider architecture**. You can configure providers via either method:

### Method A: Client Settings Modal (Recommended for local evaluation)
1. Open the web interface at `http://localhost:5173`.
2. Click the **Gear icon (Settings)** in the top-right header.
3. Paste your **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com)) or **OpenAI API Key**.
4. Click **Save Settings**. Your key is saved strictly in your local browser session.

### Method B: Backend `.env` File
Create or edit `backend/.env`:
```env
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_PROVIDER=gemini
DEFAULT_MODEL=gemini-1.5-flash
```
Restart `python run.py`. The backend will automatically recognize the configured providers.

---

## 🛡️ Content Safety & Policy Layer

The platform enforces an automated safety layer (`app/core/safety.py`):
- **Blocked**: Gratuitous pornography, sexually explicit erotica, CSAM, and non-consensual content.
- **Allowed with Educational Exemption**: Legitimate inquiries covering human reproductive anatomy, medical clinical diagnostics, pathology, endocrinology, and high-school or university biological science.

---

## 🧪 Verification & Testing

Run all backend unit and integration tests:
```bash
cd backend
python -m pytest tests -v
```

Expected output:
```
tests/test_conversations.py::test_conversations_crud PASSED
tests/test_conversations.py::test_honest_unconfigured_chat_response PASSED
tests/test_health.py::test_root_endpoint PASSED
tests/test_health.py::test_health_endpoint PASSED
tests/test_health.py::test_providers_status_honest_state PASSED
tests/test_safety.py::test_explicit_sexual_content_blocked PASSED
tests/test_safety.py::test_educational_medical_content_allowed PASSED
tests/test_safety.py::test_benign_coding_prompt_allowed PASSED
8 passed in ~0.9s
```

Frontend production build check:
```bash
cd frontend
npm run build
```
Builds cleanly with zero TypeScript or bundling errors.

---

## 📋 Stage 1 Completion Checklist

- [x] Responsive dark theme with midnight navy, electric cyan, and violet accents.
- [x] Collapsible sidebar with new chat, grouped conversation history, search filter, rename, and delete.
- [x] Main chat workspace with premium welcome screen and quick suggestion prompt cards.
- [x] Message input with Enter-to-send, Shift+Enter for new line, character/token estimation, and stage action previews.
- [x] Markdown renderer with syntax-highlighted code blocks and 1-click clipboard copy.
- [x] Honest setup indicator: No fake AI hallucinations; transparent setup guidance when unconfigured.
- [x] Modular multi-provider dispatcher supporting Gemini, OpenAI, Anthropic, and local diagnostic telemetry.
- [x] Adult content safety guardrail with legitimate medical/educational exemption.
- [x] Sliding-window rate limiting on FastAPI backend.
- [x] LocalStorage persistence with JSON backup export and import.
- [x] Comprehensive 100-Phase roadmap documented in `PHASE_STATUS.md`.
- [x] All 8 backend unit and integration tests passing.
- [x] Frontend TypeScript type check and production build verified.

---
*Stage 1 is complete. Do not proceed to Stage 2 until Stage 1 has been reviewed and approved.*
