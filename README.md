# NEXORA AI — Stage 23: IoT Project Builder & Embedded Firmware Studio

**NEXORA AI** is a premium, scalable, universal AI assistant platform engineered to evolve through 100 structured development phases. **Stage 23** introduces the **IoT Project Builder Engine (`IoTProjectBuilderEngine`)**: an interactive embedded-systems and electronics engineering workspace where users can design IoT inventions from natural language, select hardware board profiles (`ESP32`, `Arduino Uno R3`, `STM32 Nucleo-F401RE`, `Raspberry Pi Pico W`, `Raspberry Pi 4B`), browse a datasheet-grounded component library, build and validate pin-to-pin wiring schematics, generate editable firmware with honest host toolchain/syntax checks, run deterministic virtual sensor simulations (`is_physical_hardware_execution=False`), audit electrical safety and power budgets, and export versioned prototype bundles (`IoTProjectBuilderStudio.tsx`).

---

## 🌟 Stage 23 Core Deliverables

- **Project Designer & Configurable Board Profiles (`IoTProjectBuilderEngine`)**:
  - Transforms natural-language invention descriptions, target budgets, power requirements (`usb_5v`, `battery_lipo_3v7`, `dc_barrel_7v_12v`, `solar_mppt_5v`, `mains_ac_isolated_psu`), and operating environments (`indoor_lab`, `greenhouse_humid`, `outdoor_weatherproof`, `industrial_harsh`, `wearable_portable`) into complete hardware-firmware blueprints.
  - Supports 5 detailed board profiles (`esp32_devkit_v1`, `arduino_uno_r3`, `stm32_nucleo_f401re`, `raspberry_pi_pico_w`, `raspberry_pi_4b`) with exact pin counts, logic voltage levels (`3.3V` vs. `5.0V`), 5V-tolerance flags, SRAM/Flash memory limits, communication buses (`I2C`, `SPI`, `UART`, `PWM`, `ADC`, `ONEWIRE`), host toolchain probing, and compatibility warnings.
- **Component Library & Spec Verification Provenance**:
  - Searchable catalog across `sensor`, `display`, `relay`, `actuator`, `motor`, `motor_driver`, `logic_adapter`, and `power` categories.
  - Explicitly labels every component specification and BOM row as either `verified_datasheet_spec` (with primary manufacturer datasheet URL) or `estimated_typical_range`.
- **Interactive Pin-to-Pin Wiring Designer & Electrical Validator**:
  - Validates netlists against `SHORT_CIRCUIT_POWER_GND`, `REVERSE_POLARITY`, `OVERVOLTAGE_SUPPLY`, `UNDERVOLTAGE_SUPPLY`, `DIRECT_MOTOR_ON_GPIO` (bare inductive motor without H-bridge driver), `VOLTAGE_MISMATCH_5V_TO_3V3` (e.g. 5V `HC-SR04 ECHO` on non-5V-tolerant 3.3V GPIO without `TXS0108E` level shifter), `ADC_CAPABILITY_MISSING`, `INPUT_ONLY_PIN_OUTPUT_DRIVE` (`GPIO34`/`GPIO35`), `PIN_CONFLICT`, `I2C_ADDRESS_COLLISION`, `MISSING_PIN_CONNECTION`, and `STRAPPING_PIN_WARNING`.
  - Exports interactive SVG wiring schematics (`wiring/diagram.svg`) and Markdown pinout tables (`wiring/pinout_table.md`).
- **Firmware Studio & Honest Compiler Verification**:
  - Generates editable `arduino_cpp` (`.ino`), `micropython` (`main.py`), `esp_idf_c` (`main.c`), and `rpi_python_gpiozero` (`app.py`) firmware with netlist-derived pin constants and isolated credential templates (`secrets.example.h` / `secrets_example.py`).
  - Executes real Python `ast.parse` + `py_compile` verification for `micropython`/`rpi_python_gpiozero` (`compilation_tested=True`, `verification_mode="python_ast_and_py_compile"`) and honestly reports `compilation_tested=False` (`verification_mode="static_structural_check_toolchain_not_installed"`) with `missing_dependencies` when `arduino-cli` or `platformio` is not installed on the host.
- **Deterministic Virtual Device Simulator, Safety Auditor & Versioned Export**:
  - Runs multi-tick virtual sensor stimuli and fault injection (`overtemperature`, `sensor_disconnect`, `brownout_voltage`, `mqtt_broker_offline`) while explicitly setting `execution_environment="deterministic_virtual_simulation"` and `is_physical_hardware_execution=False`.
  - Audits 3.3V and 5V regulator current budgets, inductive load isolation, and flags Mains AC (`110V–240V`) and High-Current Lithium battery packs (`18650 LiPo`) with `requires_qualified_electrical_review=True` and a mandatory physical safety disclaimer.
  - Exports versioned project bundles (`v1.0.0`, `v1.0.1`, etc.) to disk and directly into the Stage 17 File Workspace (`iot_projects/<slug>_v<version>/`).

---

## 🌟 Stage 22 Core Deliverables

- **Entity Extraction & Relationship Discovery (`KnowledgeGraphIntelligenceEngine`)**:
  - Extracts typed entities (`concept`, `technology`, `organization`, `person`, `event`, `dataset`, `component`, `claim_or_standard`) and directed relationships (`depends_on`, `created_by`, `related_to`, `part_of`, `contradicts`, `supports`, `uses`, `evaluates`, `governed_by`) from user-provided text, Stage 4 Document Vault collections, and Stage 21 Discovery results.
  - Architecture & Storage Design: Backed by a dedicated SQLite relational-graph adjacency store (`data/knowledge_graph/nexora_knowledge_graph.db`) with schema migration tracking (`kg_schema_migrations`, version `1.0.0`), composite adjacency indexes on `(user_id, workspace_id, source_entity_id)` and `(user_id, workspace_id, target_entity_id)` for fast multi-hop traversal, and strict tenant/workspace scoping (`user_id` + `workspace_id`).
- **Evidence, Provenance & Epistemic Separation**:
  - Links every extracted entity and relationship to its originating document ID, URL, page/section, and quarantined source passage (`<untrusted_kg_evidence>`).
  - Strictly distinguishes explicit source assertions (`fact_basis="explicit_fact"`, `is_inferred=false`) from AI-inferred transitive relationships (`fact_basis="ai_inferred"`, `is_inferred=true`), and attaches calibrated uncertainty labels (`verified_explicit`, `hedged_source_statement`, `inferred_transitive`, `inferred_low_confidence`).
- **Cycle-Safe Knowledge Graph Queries**:
  - Supports 5 structured query modes: `"How are these technologies connected?"` (`connection_path`), `"What depends on this component?"` (`dependency_impact`), `"Which sources disagree about this claim?"` (`contradiction_analysis`), $k$-hop `neighborhood_exploration`, and auto-routed `natural_language` queries.
  - Handles cyclic graphs safely via visited-path tracking (`cycles_detected` counter) without infinite recursion.
- **Incremental Updates, Duplicate Detection & Approval Gates**:
  - Incrementally merges new facts, aliases, and source passages into existing nodes and edges while recording an auditable changelog (`kg_change_history`).
  - Detects duplicate entity candidates (`/api/v1/knowledge-graph/duplicates`) and enforces `WAITING_FOR_APPROVAL` confirmation gates (`/api/v1/knowledge-graph/operations/{op_id}/approve`) before executing destructive entity merges or deletions.
- **Interactive Knowledge Graph Studio UI (`KnowledgeGraphStudio.tsx`)**:
  - Accessible via the top navigation bar (**Knowledge Graph** tab) featuring an interactive SVG graph canvas with zoom, pan, radial vs. layered layout toggle, entity/relationship/fact-basis filters, search, 1-click neighborhood expansion, provenance inspection panel, Knowledge Query Console, Ingestion Panel, and Governance & Duplicate Merge tab.

---

## 🌟 Stage 21 Core Deliverables

- **Modular 6-Source Connector Registry (`UniversalKnowledgeDiscoveryEngine`)**:
  - Unifies General Web Search (Stage 3), Academic Publications (OpenAlex REST API + ArXiv/DOI metadata inspection), Live News & Freshness Feeds (Stage 8), Public Datasets & Tabular Catalogs, Official Documentation & Primary Institutional Sources (`.gov`, `.int`, `.edu`, W3C/IETF/NIST/WHO/RFC), and Authorized Local Knowledge Bases (Stage 4 Document Vault + Stage 17 File Workspace).
  - Supports inline and structured query operators (`site:`, `"exact phrase"`, `-exclude`, `after:YYYY-MM-DD`, `before:YYYY-MM-DD`, `lang:<code>`), source type filters, and pagination.
  - Explicitly surfaces connector-specific execution statuses (`succeeded`, `skipped`, `unavailable`, `error`) and latency metrics instead of silently hiding failed connectors.
- **Intelligent Discovery & Defensible Provenance**:
  - Classifies query intent, expands complex queries into focused subqueries, and preserves the user's chosen or auto-detected language (including native Tamil, Hindi, Arabic, CJK, and European scripts).
  - Enforces strict anti-fabrication provenance rules: never labels a source as scholarly (`is_verified_scholarly`) or official (`is_verified_official`) without a defensible basis (`authority_basis`), and classifies every result into an explicit originality tier (`original_primary_source`, `peer_reviewed_or_preprint`, `secondary_reporting`, `syndicated_or_copied`).
  - Deduplicates canonical URLs (stripping `utm_*`, `fbclid`, `gclid` tracking parameters) and substantially overlapping snippets (Jaccard similarity $\ge 0.72$).
- **Multi-Source Knowledge Synthesis**:
  - Generates concise executive summaries and multi-section reports with clickable numbered citations (`[1]`, `[2]`), grouped findings by category, a Source Comparison Matrix (`corroborated`, `unique_finding`, `conflicting`), automated Conflict Detection across diverging sources, Evidence Gaps & Limitations, and a Chronological Timeline built strictly from sources with verified publication dates.
- **Performance, Caching & Security**:
  - Bounded parallel connector execution (`asyncio.Semaphore`), per-connector timeouts, TTL response caching, SSRF URL blocking (`localhost`, `127.0.0.1`, `169.254.169.254`, private IP ranges), and `<untrusted_discovery_evidence>` prompt-injection quarantine.
- **Universal Discovery Studio UI (`DiscoveryStudio.tsx`)**:
  - Accessible via the top navigation bar (**Discovery** tab) featuring 5 search mode selectors, 6 source connector toggles, operator & date range filters, Synthesis/Timeline/Matrix/Connector Diagnostics tabs, originality & authority badges, and one-click follow-up query exploration.

---

## 🌟 Stage 20 Core Deliverables

- **10-Suite Live Evaluation Framework (`EvaluationQualityAssuranceEngine`)**:
  - Executes real subsystem calls across Stages 1–19 in isolated evaluation namespaces (`eval_<random_hex>`) with consequential external side-effects blocked.
  - Covers General QA & Instruction Following, Web Research & Citation Freshness, Fact-Checking & Uncertainty Calibration, Document Extraction & Grounded RAG, Multilingual & Translation, Vision & Quarantined OCR, Voice Speech Sanitization & TTS, Sandboxed Code Execution & AST Inspection, Agents/Tools/Memory/Workflows, and Security/Privacy/Safety Policy Compliance.
- **Honest Metrics, Scoring Rules & Anti-Fabrication Guarantees**:
  - Tracks `task_success_rate`, `factual_support_score`, `citation_validity_score`, `extraction_accuracy_score`, `language_quality_score`, `tool_call_success_rate`, `safety_compliance_rate`, `error_rate`, `avg_latency_ms`, `p95_latency_ms`, `total_tokens`, and `estimated_cost_usd`.
  - Publishes explicit `METRIC_SCORING_RULES` with documented limitations and `is_definitive_ground_truth: false` for heuristic/advisory rubrics; reports `null` with transparent explanations (`unavailable_metrics_notes`) whenever a metric cannot be verified.
- **Versioned Test Dataset Management (`v1.x.x`)**:
  - Automatic semantic version bumps whenever benchmark cases are added, reviewed, or deleted (`GET/POST /api/v1/evaluation/cases`).
  - Excludes private user conversations by default (`contains_private_conversation_data=True` rejected) and blocks raw credentials in test payloads.
  - Clearly labels generated synthetic cases (`source_type="synthetic_labeled"`, `review_status="pending_review"`) and excludes them from official runs until approved.
- **Regression Testing & Release Gate Verdicts**:
  - Compares candidate runs against baseline runs (`POST /api/v1/evaluation/compare`) and flags regressions (`EvalRegressionAlert`) across task success, safety compliance, error rate, and latency.
  - Computes deterministic release verdicts (`RELEASE_APPROVED`, `RELEASE_BLOCKED_CRITICAL_FAILURE`, `RELEASE_BLOCKED_REGRESSION`, `INCOMPLETE_RUN`).
- **Evaluation & QA Studio Dashboard (`EvaluationStudio.tsx`)**:
  - Accessible via the top navigation bar (**Eval & QA** tab) featuring 10-suite selection, fault/interruption simulation controls, Release Gate Verdict Banner, Metric Summary Cards, Case Assertion Inspector, Historical Run Comparison, Dataset Version Manager, Scoring Rules Inspector, and Markdown/JSON report export.

---

## 🌟 Stage 19 Core Deliverables

- **Genuine Git Repository Integration (`GitVersionControlEngine`)**:
  - Detects and validates Git installation and repository state (`GET /api/v1/git/capabilities`, `GET /api/v1/git/status`).
  - Supports repository initialization (`POST /api/v1/git/init`) with automatic `.gitignore` rule recommendations, staging (`POST /api/v1/git/stage`), unstaging (`POST /api/v1/git/unstage`), commit history browsing (`GET /api/v1/git/commits`), and unified + structured side-by-side diff generation (`GET /api/v1/git/diff`).
- **Safe Change Management & Secret Protection**:
  - Blocks staging or committing hardcoded API keys (`AIza...`, `sk-...`, `ghp_...`, `glpat-...`, private keys) and `.env` files (`BLOCKED`).
  - Requires explicit user confirmation (`WAITING_FOR_APPROVAL` -> `POST /api/v1/git/operations/{id}/approve`) before commits, branch merges, or remote synchronization.
  - Detects uncommitted working-tree changes before branch switches (`BLOCKED`), blocks `--force` pushes, and safely aborts conflicted merges (`git merge --abort`) so workspaces are never left corrupted.
- **AI-Powered Code Review (`POST /api/v1/git/review`)**:
  - Analyzes changed files for bugs, security weaknesses, readability issues, and missing test updates.
  - Clearly distinguishes **Verified Defects** (`verified_defect`: AST syntax errors, hardcoded secrets, literal division by zero, `eval`/`exec`, failing Stage 18 unit tests) from **Possible Concerns** (`possible_concern`: mutable default arguments, bare `except:`, `TODO`/`FIXME` markers, missing test file updates).
  - Never auto-accepts code review suggestions without user approval.
- **Collaboration, Remotes & Honest Pull Request Preparation**:
  - Validates remote repository URLs against SSRF/private IP ranges and allowed hosts (`github.com`, `gitlab.com`, `bitbucket.org`).
  - Prepares Pull Request records (`POST /api/v1/git/pull-requests`) with branch comparison stats and issue references (`#19`), explicitly distinguishing local PR drafts (`LOCAL_DRAFT_ONLY`) from provider-confirmed remote actions (`REMOTE_CONFIRMED`).
- **Git & Version Control Studio UI (`GitVersionControlStudio.tsx`)**:
  - Accessible via the top navigation bar (**Git & VCS** tab) featuring branch selector/creator, working-tree staging controls, Unified & Side-by-Side Diff Viewer, AI Code Review panel, Commit History & Audit Log, and Remote/PR Collaboration panel.

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

---

## 📋 Stage 14: Multi-Agent Intelligence System Checklist

- [x] **Modular Specialized Agent Registry (`GET /api/v1/agents/registry`)**: Registers 8 specialized agents (`research_agent`, `coding_agent`, `education_agent`, `writing_agent`, `data_analyst_agent`, `productivity_agent`, `document_agent`, `language_agent`) with explicit purposes, capabilities, limitations, least-privilege permission scopes (`read_only`, `search_and_retrieve`, `document_read`, `workspace_write_requires_approval`), and dynamic tool availability verification.
- [x] **Central Multi-Agent Orchestrator (`POST /api/v1/agents/run`)**: Classifies requests or accepts manual agent selection, builds dependency-tracked subtask graphs, executes independent tasks in bounded parallel (`asyncio.Semaphore`) and dependent synthesis tasks sequentially.
- [x] **Loop, Duplicate Call, Conflict & Cost Safeguards**: Deduplicates identical tool invocations across agents (`duplicate_tool_calls_prevented`), detects conflicting numerical/factual claims (`conflicts_detected`), and enforces strict per-run USD spending caps (`max_cost_budget_usd`).
- [x] **Epistemic Separation & Shared Context**: Passes isolated user memories (`<user_memory_context>`), preserves source citations and Vault file references, and separates **Verified Facts**, **Working Assumptions**, and **Unresolved Questions**.
- [x] **Least-Privilege Approval Gate, Retry & Cancellation**: Consequential actions pause in `WAITING_APPROVAL` until approved (`/approve`), with full support for subtask retry (`/retry`) and run cancellation (`/cancel`) in the **Agent Swarm Workspace (`AgentStudio.tsx`)**.
- [x] **88/88 Automated Pytest Tests Passing** across Stages 1–14 (`tests/test_stage14_agents.py`).
- [x] **Frontend TypeScript & Vite Production Build Verified** (`0 errors`).

---

## 📋 Stage 15: Workflow Automation Engine Checklist

- [x] **Visual Workflow Builder & Templates (`/api/v1/workflows/*`, `WorkflowStudio.tsx`)**: Supports manual and scheduled triggers, sequential DAG task steps with dependencies, AI-agent (`research_agent`, `writing_agent`, `document_agent`, `productivity_agent`, etc.) and registered-tool (`calculator`, `web_search`, `document_retrieval`, `fact_check`, `translation`, `realtime_pulse`, `dispatch_external_message`, `delete_document`) actions, condition expressions (`always`, `previous_succeeded`, `contains:`, `not_contains:`, `equals:`), forward branching (`skip`, `fail_workflow`, `jump_to_step`), bounded retries (`0..3`), input/output templating (`{{workflow.input.<key>}}`, `{{steps.<step_id>.output}}`), pre-built templates, duplication, editing, deletion, validation, dry-run testing, activation, pause, and resume controls.
- [x] **Persistent SQLite Job Scheduler & Execution History (`data/workflows/nexora_workflows.db`)**: Supports IANA time zones (`Asia/Kolkata`, `UTC`, `America/New_York`, etc.), start dates, recurrence rules (`once`, `hourly`, `daily`, `weekly`, `interval`), and calculated `next_run_at` timestamps. Prevents duplicate scheduled runs via slot idempotency keys (`sched:{workflow_id}:{next_run_iso}`), prevents overlapping runs when `allow_concurrent_runs=false`, blocks dependency cycles via Kahn's DAG algorithm, and safely recovers interrupted runs on worker restart (`POST /api/v1/workflows/scheduler/recover`).
- [x] **Execution Monitoring & Honest Status Reporting**: Tracks `QUEUED`, `RUNNING`, `WAITING_FOR_APPROVAL`, `SUCCEEDED`, `FAILED`, `CANCELLED`, and `RETRYING` states with step-level duration, attempt counts, resolved inputs, and sensitive secret redaction. Never marks a workflow `SUCCEEDED` unless all non-skipped steps actually succeed.
- [x] **In-App Notification Center & Verified External Delivery**: Records completion, failure, approval requests, and worker recovery alerts in SQLite. External webhook (`NOTIFICATION_WEBHOOK_URL`) and email (`SMTP_HOST`) channels report honest `webhook_not_configured` / `smtp_not_configured` status unless configured and confirmed by the external endpoint.
- [x] **95/95 Automated Pytest Tests Passing** across Stages 1–15 (`tests/test_stage15_workflows.py`).
- [x] **Frontend TypeScript & Vite Production Build Verified** (`0 errors`).

---

## 📋 Stage 16: Computer Control & Digital Execution Engine Checklist

- [x] **Isolated Browser Automation (`BrowserAutomationRunner` in `backend/app/services/computer/engine.py`)**: Supports `open_url`, `navigate`, `click`, `fill_text`, `select_option`, `scroll`, `capture_screenshot` (verified PNG base64 viewport captures with secrets masked), `extract_content` (quarantined in `<untrusted_webpage_content>`), and `submit_form` with checkpoints and verified completion.
- [x] **Sandboxed Local Computer Task Runner (`LocalComputerTaskRunner`)**: Strictly separated from browser automation (`target_domain: "browser" | "local_os"`). Confines file operations (`list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `delete_workspace_file`) to `data/computer_workspace`, blocks path traversal (`..`), and limits local tasks to predefined diagnostics (`system_summary`, `workspace_disk_usage`, `python_runtime_check`) and allowlisted applications (`calculator`, `notepad`, `browser_docs`). Clearly discloses that a remote server cannot control a user's physical computer without a local companion agent.
- [x] **Preview-and-Confirm Approval Gates & Security Boundaries**: Pauses in `WAITING_FOR_APPROVAL` with a structured `ComputerActionPreview` before consequential actions (`submit_form`, `delete_workspace_file`, overwriting files, or opening applications). Detects CAPTCHA (`g-recaptcha`, `cf-turnstile`, `hcaptcha`), MFA prompts, and HTTP 401/403 walls, halting cleanly with `BLOCKED_BY_SECURITY_BOUNDARY` without ever attempting to bypass.
- [x] **SSRF, URL Allowlist, Secret Redaction & Session Isolation**: Blocks `file://`, loopback (`127.0.0.1`, `localhost`), RFC1918 private LAN IPs, and cloud metadata targets; redacts passwords and API keys (`[REDACTED_SECRET]`) across previews, logs, audit trails, and screenshots; isolates per-session DOM/cookie state; and connects to Stage 11/14/15 via `browser_automation_step` and `computer_workspace_task` in `ToolRegistry`.
- [x] **101/101 Automated Pytest Tests Passing** across Stages 1–16 (`tests/test_stage16_computer.py`).
- [x] **Frontend TypeScript & Vite Production Build Verified** (`0 errors`).

---

## 📋 Stage 17: File Management & Workspace Automation Engine Checklist

- [x] **Strict Workspace Boundary & Path Security (`FileWorkspaceEngine` in `backend/app/services/files/engine.py`)**: Isolates files per user (`data/file_workspace/<user_id>`), normalizes paths, blocks directory traversal (`..`), drive letters, null bytes, internal system folders (`.nexora_trash`, `.nexora_versions`), forbidden executable extensions (`.exe`, `.ps1`, `.bat`), credential files (`.env`, `id_rsa`), and unauthorized symbolic-link escapes.
- [x] **File Discovery, Search & Multi-Format Processing**: Lists files/folders with SHA-256 content hashes; searches filenames, extensions, categories, date/size bounds, and full-text content across `.txt`, `.md`, `.csv`, `.json`, `.docx`, `.xlsx`, `.pdf`, plus Stage 4 Document Vault chunks; wraps file content in `<untrusted_file_content>` tags.
- [x] **Creation, Editing, Conversions & Automatic Version History**: Creates and edits text/Markdown/CSV/JSON/DOCX/XLSX files; preserves originals via immutable backup snapshots in `.nexora_versions` before every overwrite/edit; supports 1-click version restoration with SHA-256 verification; converts between `CSV`, `JSON`, `XLSX`, `MD`, `TXT`, and `DOCX`.
- [x] **SHA-256 Duplicate Detection, Rule-Based Organization, Recoverable Trash & Rollback**: Detects duplicate files by SHA-256 hash; previews planned changes before bulk organization or cleanup; requires explicit confirmation (`WAITING_FOR_APPROVAL`) before deletes, unconfirmed overwrites, or bulk moves; sends deleted files to Recoverable Trash (`.nexora_trash`) with 1-click restore; and supports 1-click operation rollback.
- [x] **Cross-Stage Integration & File Workspace Studio UI (`FileWorkspaceStudio.tsx`)**: Syncs workspace files to Stage 4 Document Vault (`/api/v1/files/sync-stage4`), imports Stage 16 Browser Automation captures (`/api/v1/files/import-browser-session`), and registers `workspace_file_manager` and `workspace_bulk_organizer` in `ToolRegistry`.
- [x] **108/108 Automated Pytest Tests Passing** across Stages 1–17 (`tests/test_stage17_files.py`).
- [x] **Frontend TypeScript & Vite Production Build Verified** (`0 errors`).

---

## 📋 Stage 18: Terminal & Code Execution Engine Checklist

- [x] **Developer Code Workspace (`TerminalExecutionEngine` in `backend/app/services/terminal/engine.py`)**: Isolated per-user, per-project workspaces (`data/terminal_workspace/<user_id>/<project_id>`) supporting Python, JavaScript, TypeScript, HTML, and CSS templates; automatic pre-edit and pre-repair version backups (`.nexora_code_backups` + SQLite `terminal_backups`) with 1-click restoration.
- [x] **Syntax Checking, Formatting, Linting & Missing Dependency Detection (`/api/v1/terminal/inspect`)**: Real Python `ast.parse` syntax diagnostics, static linter (`PY_BARE_EXCEPT`, `PY_MUTABLE_DEFAULT`, `PY_DIV_BY_ZERO`, `PY_UNUSED_IMPORT`), deterministic PEP-8/JS formatting, import dependency inspection (`importlib.util.find_spec` + `requirements.txt` / `package.json`) with clear setup instructions, and untrusted repository instruction quarantine.
- [x] **Sandboxed Code & Test Execution (`/api/v1/terminal/execute`)**: Runs code and unit tests (`unittest` / `pytest` / `node`) inside an isolated subprocess environment with sanitized environment variables (all host API keys stripped), recursion/memory/timeout/output-truncation limits (`5.0s`, `128MB`, `64KB`), and a runtime sandbox site-guard that disables outbound network sockets, `os.system`/`popen`, and outside-workspace writes by default.
- [x] **Controlled Terminal & Approval Gates (`/api/v1/terminal/command`, `/executions/{id}/approve`)**: Classifies commands into `allowed_safe` (`python`, `pytest`, `node`, `ls`, `cat`, `pwd`, `echo`, `git status`), `requires_approval` (`pip install`, `npm install`, `rm`, `--allow-network`), and `blocked_forbidden` (credential theft, `env`, `.env`, `id_rsa`, `rm -rf`, command chaining `;`/`&&`/`|`, subshells, path traversal `..`).
- [x] **Bounded Autonomous Debugging & Repair (`/api/v1/terminal/debug-repair`)**: Captures real `stdout`, `stderr`, `exit_code`, and unit test results; diagnoses root causes; snapshots backups; applies targeted fixes up to `TERMINAL_MAX_REPAIR_ATTEMPTS` (default `3`); verifies with real test re-execution; and stops immediately when user intervention is required (e.g., missing external packages).
- [x] **Cross-Stage Integration & IDE Workspace (`TerminalCodeStudio.tsx`)**: Connects `terminal_code_runner` and `terminal_package_and_command` to `ToolRegistry` and Stage 14's `coding_agent`, and provides bidirectional sync with the Stage 17 File Workspace (`/api/v1/terminal/projects/{id}/sync-stage17`).
- [x] **115/115 Automated Pytest Tests Passing** across Stages 1–18 (`tests/test_stage18_terminal.py`).
- [x] **Frontend TypeScript & Vite Production Build Verified** (`0 errors`).

---
*Stage 18 is complete. Do not proceed to Stage 19 until Stage 18 has been reviewed and approved.*

