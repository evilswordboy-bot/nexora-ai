import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  Mic,
  Workflow,
  Terminal,
  Compass,
  Eye,
  Share2,
  Users,
  Network,
  Database,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Cpu,
  Lock,
  BookOpen,
  Layers,
  ChevronRight,
  Radio,
  ShieldAlert,
  Plane,
} from 'lucide-react';

import { useChat } from '../../context/ChatContext';

interface CapabilityCard {
  id: string;
  title: string;
  stageBadge: string;
  description: string;
  highlights: string[];
  targetView:
    | 'chat'
    | 'workflows'
    | 'terminal'
    | 'discovery'
    | 'vision'
    | 'knowledgegraph'
    | 'agents'
    | 'firmware'
    | 'telemetry'
    | 'security'
    | 'schematic'
    | 'pcb'
    | 'travel';
  icon: React.FC<{ className?: string }>;

}

const CAPABILITY_CARDS: CapabilityCard[] = [
  {
    id: 'conversational-ai',
    title: 'Conversational AI',
    stageBadge: 'Stages 1–2 & 6',
    description:
      'Real-time Server-Sent Events (SSE) streaming across configured providers with context grounding and 90+ language support.',
    highlights: ['Token-by-token SSE stream', 'Indic & global scripts', 'Grounded inline citations'],
    targetView: 'chat',
    icon: Sparkles,
  },
  {
    id: 'voice-assistance',
    title: 'Voice Assistance',
    stageBadge: 'Stage 7',
    description:
      'Hands-free dictation, live interim transcript streaming, natural speech sanitization, and multilingual neural voice playback.',
    highlights: ['Push-to-Talk & Voice Chat', 'Code/URL speech sanitizer', 'Adjustable speech rate'],
    targetView: 'chat',
    icon: Mic,
  },
  {
    id: 'intelligent-automation',
    title: 'Intelligent Automation',
    stageBadge: 'Stages 15–17',
    description:
      'Durable SQLite DAG workflow scheduler, isolated browser automation, and permission-scoped file workspace management.',
    highlights: ['Timezone DAG scheduling', 'Step output templating', 'Preview & approval gates'],
    targetView: 'workflows',
    icon: Workflow,
  },
  {
    id: 'coding-and-firmware',
    title: 'Coding & Embedded Studio',
    stageBadge: 'Stages 18–19 & 23–24',
    description:
      'Sandboxed code execution, AST linting, genuine Git version control, IoT wiring validation, and multi-file embedded firmware IDE.',
    highlights: ['Isolated process sandbox', 'Git diff & secret guard', 'ESP32 / STM32 / Pico W IDE'],
    targetView: 'terminal',
    icon: Terminal,
  },
  {
    id: 'deep-research',
    title: 'Universal Research & Discovery',
    stageBadge: 'Stages 3 & 21',
    description:
      'Unified multi-source discovery across web, OpenAlex/arXiv scholarly publications, live news, public datasets, and local vaults.',
    highlights: ['6 modular source connectors', 'Originality & authority tiers', 'Cross-source conflict matrix'],
    targetView: 'discovery',
    icon: Compass,
  },
  {
    id: 'creative-visual-studio',
    title: 'Visual & Multimodal Studio',
    stageBadge: 'Stage 9',
    description:
      'Technical image inspection, prompt-injection quarantined OCR extraction, schematic analysis, and side-by-side visual comparison.',
    highlights: ['Pillow container verification', 'Quarantined OCR extraction', 'Side-by-side visual diffing'],
    targetView: 'vision',
    icon: Eye,
  },
  {
    id: 'data-science-graph',
    title: 'Data Science & Knowledge Graph',
    stageBadge: 'Stages 4 & 22',
    description:
      'CSV/XLSX/PDF/DOCX intelligence paired with a relational-graph engine for cycle-safe path queries and provenance tracking.',
    highlights: ['Explicit vs. AI-inferred facts', 'Cycle-safe BFS path queries', 'Tabular & RAG analytics'],
    targetView: 'knowledgegraph',
    icon: Share2,
  },
  {
    id: 'multi-agent-collaboration',
    title: 'Multi-Agent Collaboration',
    stageBadge: 'Stage 14',
    description:
      'Coordinated swarm of 8 specialized agents with least-privilege tool scopes, duplicate call prevention, and epistemic separation.',
    highlights: ['8 specialist AI roles', 'Parallel DAG orchestration', 'Verified vs. assumed facts'],
    targetView: 'agents',
    icon: Users,
  },
  {
    id: 'iot-telemetry-engine',
    title: 'IoT Telemetry & Device Registry',
    stageBadge: 'Stage 25',
    description:
      'Authenticated HTTP/MQTT ingestion pipeline with PBKDF2 token hashing, physical sensor bounds validation, cooldown anomaly alerts, and consequential actuation gates.',
    highlights: ['Salted PBKDF2 device tokens', 'Zero fabricated readings', 'Approval-gated reboots & OTA'],
    targetView: 'telemetry',
    icon: Radio,
  },
  {
    id: 'iot-security-engine',
    title: 'IoT Security & Threat Detection',
    stageBadge: 'Stage 26',
    description:
      'Defensive device posture auditing, rule-based config checks with secret redaction, behavioral anomaly detection, and approval-gated containment.',
    highlights: ['Device posture auditing', 'Secret masking & credential checks', 'Anomaly detection & containment'],
    targetView: 'security',
    icon: ShieldAlert,
  },
  {
    id: 'circuit-schematic-studio',
    title: 'Circuit Schematic Design Studio',
    stageBadge: 'Stage 27',
    description:
      'Interactive EDA netlist canvas, topological Electrical Rule Checks (ERC), standard SPICE simulation, E24 engineering calculators, and AI circuit synthesis.',
    highlights: ['Interactive SVG netlist canvas', 'Static ERC diagnostic rules', 'SPICE & analytical linear solver'],
    targetView: 'schematic',
    icon: Cpu,
  },
  {
    id: 'pcb-layout-studio',
    title: 'PCB Layout & Design Studio',
    stageBadge: 'Stage 28',
    description:
      'Multilayer EDA board editor, ratsnest flylines, assisted 45° routing, IPC-2152 DRC checks, 3D orbital preview, and Gerber/KiCad/drill exports.',
    highlights: ['Interactive SVG/Canvas routing', '8-Rule geometric & short DRC', 'Gerber RS-274X & KiCad PCB'],
    targetView: 'pcb',
    icon: Layers,
  },
  {
    id: 'travel-ticket-commerce',
    title: 'Universal Travel & Ticket Booking',
    stageBadge: 'Stage 29',
    description:
      'Unified multi-provider discovery and booking for flights, trains, buses, hotels, movies, and events with live availability, transparent pricing, and tokenized payment security.',
    highlights: ['Amadeus, IRCTC, RedBus, Booking & Ticketmaster', 'Tokenized cards & zero raw CVV storage', 'Idempotent checkout & digital pass PNR'],
    targetView: 'travel',
    icon: Plane,
  },
];


const PIPELINE_STEPS = [
  {
    step: '01',
    name: 'Understand',
    title: 'Multimodal & Multilingual Intent Parsing',
    detail:
      'Analyzes user prompts, attached documents, images, and language script while enforcing safety guardrails and quarantining untrusted external inputs.',
  },
  {
    step: '02',
    name: 'Reason',
    title: 'Epistemic & Graph-Grounded Analysis',
    detail:
      'Separates explicit source facts from working inferences, retrieves relevant persistent memories and knowledge graph paths, and selects optimal model routes.',
  },
  {
    step: '03',
    name: 'Plan',
    title: 'Dependency-Tracked Subtask Decomposition',
    detail:
      'Breaks complex engineering or research goals into ordered subtasks with explicit completion criteria, cost budgets, and least-privilege tool assignments.',
  },
  {
    step: '04',
    name: 'Execute',
    title: 'Sandboxed Tool, Code & Agent Dispatch',
    detail:
      'Runs web/scholarly connectors, isolated code sandboxes, Git operations, or IoT simulations while pausing at explicit user approval gates for consequential actions.',
  },
  {
    step: '05',
    name: 'Verify',
    title: 'Evidence-Based Fact & Quality Assurance',
    detail:
      'Cross-checks claims against retrieved sources, runs real unit tests and static analyzers, and reports honest compiler, test, and citation outcomes.',
  },
];

const TECHNOLOGY_PILLARS = [
  {
    title: 'Capability-Aware Model Routing',
    stage: 'Stage 12 Engine',
    icon: Network,
    targetView: 'routing' as const,
    description:
      'Dynamically selects across configured providers (Gemini, OpenAI, Anthropic, or honest offline fallback) using Quality-First, Balanced, or Speed-First policies with bounded failover and USD budget caps.',
    metrics: ['Dynamic Model Registry', 'Bounded 429/503 Failover', 'Per-Request & Daily Cost Guards'],
  },
  {
    title: 'Specialist AI Agent Swarm',
    stage: 'Stage 14 Engine',
    icon: Users,
    targetView: 'agents' as const,
    description:
      'Coordinates Research, Coding, Education, Writing, Data Analyst, Productivity, Document, and Language specialists with tool deduplication and cross-agent conflict detection.',
    metrics: ['8 Least-Privilege Agent Roles', 'Bounded Parallel Execution', 'Epistemic Fact Separation'],
  },
  {
    title: 'Persistent Project Context',
    stage: 'Stages 4, 13 & 22',
    icon: Database,
    targetView: 'memory' as const,
    description:
      'Combines HMAC-SHA256 encrypted-at-rest user memory (`enc:v1`), lexical BM25 Document Vault RAG, and an indexed SQLite Knowledge Graph with workspace isolation.',
    metrics: ['At-Rest Encrypted Memory', 'Multi-Format Document Vault', 'Indexed Adjacency Graph'],
  },
  {
    title: 'Strict Privacy & Security Controls',
    stage: 'Stages 11, 16, 17 & 19',
    icon: Lock,
    targetView: 'files' as const,
    description:
      'Blocks PII and API keys from memory/Git commits, confines file and terminal operations to authorized workspaces, blocks SSRF private IPs, and quarantines untrusted tool outputs.',
    metrics: ['XML Prompt-Injection Quarantine', 'SSRF & Path Traversal Defense', 'Explicit User Approval Gates'],
  },
  {
    title: 'Evidence-Based Verification',
    stage: 'Stages 5, 20 & 24',
    icon: ShieldCheck,
    targetView: 'evaluation' as const,
    description:
      'Verifies factual claims with calibrated confidence verdicts and runs a 10-suite automated QA harness plus embedded static safety analyzers with zero fabricated benchmark scores.',
    metrics: ['Claim-Level Stance Verdicts', '10-Suite Release Gate Harness', 'Authentic Compiler & Test Logs'],
  },
];

export const NexoraLandingPage: React.FC = () => {
  const { setActiveWorkspaceView, setSetupGuideModalOpen, isBackendConnected } = useChat();
  const [activePipelineIdx, setActivePipelineIdx] = useState<number>(0);
  const [parallaxOffset, setParallaxOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    const listener = (event: MediaQueryListEvent) => setPrefersReducedMotion(event.matches);
    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, []);

  const handleHeroMouseMove = (e: React.MouseEvent<HTMLElement>) => {
    if (prefersReducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const normX = (e.clientX - rect.left) / rect.width - 0.5;
    const normY = (e.clientY - rect.top) / rect.height - 0.5;
    setParallaxOffset({
      x: Math.round(normX * 14),
      y: Math.round(normY * 10),
    });
  };

  const handleLaunchWorkspace = (
    target:
      | 'chat'
      | 'documents'
      | 'factcheck'
      | 'translation'
      | 'realtime'
      | 'vision'
      | 'reasoning'
      | 'routing'
      | 'memory'
      | 'agents'
      | 'workflows'
      | 'computer'
      | 'files'
      | 'terminal'
      | 'git'
      | 'evaluation'
      | 'discovery'
      | 'knowledgegraph'
      | 'iot'
      | 'firmware'
      | 'telemetry'
      | 'security'
      | 'schematic'
      | 'pcb'
      | 'travel' = 'chat'
  ) => {
    setActiveWorkspaceView(target);
  };


  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    }
  };

  return (
    <div
      id="landing-scroll-root"
      className="h-screen w-screen overflow-y-auto overflow-x-hidden bg-[#02050b] text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200 scroll-smooth"
    >
      {/* 1. NAVIGATION BAR */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#02050b]/85 border-b border-cyan-500/15">
        <nav
          aria-label="Primary Landing Navigation"
          className="max-w-7xl mx-auto px-4 sm:px-8 h-20 flex items-center justify-between"
        >
          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            <img
              src="assets/nexora-eagle-logo.jpg"
              alt="NEXORA AI Official Metallic Eagle Logo"
              className="w-11 h-11 rounded-xl object-cover border border-cyan-400/50 shadow-[0_0_20px_rgba(6,182,212,0.35)]"
            />
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span
                  style={{ fontFamily: "'Orbitron', sans-serif" }}
                  className="text-lg sm:text-xl font-extrabold tracking-[0.2em] bg-gradient-to-r from-white via-slate-200 to-cyan-300 bg-clip-text text-transparent"
                >
                  NEXORA AI
                </span>
                <span
                  style={{ fontFamily: "'Orbitron', sans-serif" }}
                  className="text-[10px] font-bold tracking-[0.18em] px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-400/30"
                >
                  SKS
                </span>
              </div>
              <span className="text-[10px] tracking-[0.24em] uppercase text-slate-400">
                Unified Intelligence Platform
              </span>
            </div>
          </div>

          {/* Center Navigation Links */}
          <div className="hidden md:flex items-center gap-8 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
            <button
              onClick={() => scrollToSection('hero')}
              className="hover:text-cyan-300 transition-colors py-1"
            >
              Home
            </button>
            <button
              onClick={() => scrollToSection('capabilities')}
              className="hover:text-cyan-300 transition-colors py-1"
            >
              Capabilities
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="hover:text-cyan-300 transition-colors py-1"
            >
              Architecture
            </button>
            <button
              onClick={() => scrollToSection('technology')}
              className="hover:text-cyan-300 transition-colors py-1"
            >
              Technology
            </button>
            <button
              onClick={() => scrollToSection('mission')}
              className="hover:text-cyan-300 transition-colors py-1"
            >
              About
            </button>
          </div>

          {/* Right CTA Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleLaunchWorkspace('chat')}
              style={{ fontFamily: "'Orbitron', sans-serif" }}
              className="relative group px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-[0.16em] text-slate-950 bg-gradient-to-r from-cyan-300 via-cyan-400 to-sky-400 hover:from-cyan-200 hover:to-cyan-300 shadow-[0_0_28px_rgba(34,211,238,0.45)] hover:shadow-[0_0_38px_rgba(34,211,238,0.75)] transition-all duration-300 flex items-center gap-2"
            >
              <span>Launch NEXORA</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>
        </nav>
      </header>

      {/* 2. HERO SECTION */}
      <section
        id="hero"
        onMouseMove={handleHeroMouseMove}
        className="relative min-h-[calc(100vh-5rem)] flex flex-col items-center justify-between px-4 sm:px-8 pt-6 pb-12 overflow-hidden bg-gradient-to-b from-[#02050b] via-[#050d1e] to-[#02050b]"
      >
        {/* Subtle Sci-Fi Radial & Particle Atmosphere */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 overflow-hidden"
        >
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[780px] h-[520px] rounded-full bg-cyan-500/10 blur-[130px]" />
          <div className="absolute top-1/4 left-1/4 w-2 h-2 rounded-full bg-cyan-300/60 shadow-[0_0_12px_#22d3ee]" />
          <div className="absolute top-1/3 right-1/4 w-1.5 h-1.5 rounded-full bg-cyan-400/50 shadow-[0_0_10px_#06b6d4]" />
          <div className="absolute bottom-1/3 left-1/5 w-1.5 h-1.5 rounded-full bg-sky-300/40 shadow-[0_0_8px_#38bdf8]" />
          <div className="absolute bottom-1/4 right-1/5 w-2 h-2 rounded-full bg-cyan-300/50 shadow-[0_0_12px_#22d3ee]" />
        </div>

        {/* Top Branding & Metallic Typography Above Eagle (Without Covering Eagle) */}
        <div className="relative z-10 text-center max-w-4xl mx-auto space-y-2 pt-2">
          <div
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-4xl sm:text-6xl md:text-7xl font-black tracking-[0.28em] bg-gradient-to-b from-white via-slate-200 to-cyan-300 bg-clip-text text-transparent drop-shadow-[0_0_24px_rgba(34,211,238,0.35)]"
          >
            SKS
          </div>

          <div
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-xl sm:text-3xl font-extrabold tracking-[0.32em] text-slate-100 uppercase"
          >
            NEXORA AI
          </div>

          <p
            style={{ fontFamily: "'Rajdhani', sans-serif" }}
            className="text-xs sm:text-sm md:text-base font-semibold tracking-[0.42em] uppercase text-cyan-300 drop-shadow-[0_0_12px_rgba(6,182,212,0.55)]"
          >
            INTELLIGENCE. BEYOND LIMITS.
          </p>
        </div>

        {/* Centerpiece: Untouched Metallic Robotic Eagle Image */}
        <div
          style={{
            transform: prefersReducedMotion
              ? 'none'
              : `translate3d(${parallaxOffset.x}px, ${parallaxOffset.y}px, 0)`,
            transition: 'transform 180ms ease-out',
          }}
          className="relative z-10 my-4 w-full max-w-5xl mx-auto flex flex-col items-center"
        >
          <div className="relative w-full rounded-2xl overflow-hidden border border-cyan-500/25 shadow-[0_0_70px_rgba(6,182,212,0.2)] bg-[#02050b]">
            <img
              src="assets/nexora-eagle-hero.jpg"
              alt="NEXORA AI Metallic Robotic Eagle Centerpiece"
              loading="eager"
              fetchPriority="high"
              className="w-full h-auto object-contain select-none block"
            />
          </div>

          {/* Discreet Small Uppercase Text "A BKKLSSNJ" Directly Below the Eagle */}
          <div
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="mt-3 text-[11px] sm:text-xs font-semibold uppercase tracking-[0.55em] text-cyan-300/90 drop-shadow-[0_0_10px_rgba(34,211,238,0.65)] select-all"
          >
            A &nbsp; B K K L S S N J
          </div>
        </div>

        {/* Headline, Short Description, and Dual CTA Buttons Below Eagle */}
        <div className="relative z-10 text-center max-w-3xl mx-auto space-y-5 pt-2">
          <h1
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-2xl sm:text-4xl md:text-5xl font-extrabold uppercase tracking-[0.14em] bg-gradient-to-r from-slate-100 via-white to-cyan-200 bg-clip-text text-transparent leading-tight"
          >
            THE NEXT EVOLUTION OF INTELLIGENCE
          </h1>

          <p className="text-sm sm:text-base text-slate-300/90 max-w-2xl mx-auto leading-relaxed">
            A unified engineering and research workspace uniting multi-model reasoning, verified
            multi-source discovery, specialist agent swarms, sandboxed code execution, knowledge
            graphs, and embedded hardware design.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              onClick={() => handleLaunchWorkspace('chat')}
              style={{ fontFamily: "'Orbitron', sans-serif" }}
              className="px-7 py-3.5 rounded-xl text-xs sm:text-sm font-bold uppercase tracking-[0.18em] text-slate-950 bg-gradient-to-r from-cyan-300 via-cyan-400 to-sky-400 hover:from-cyan-200 hover:to-cyan-300 shadow-[0_0_30px_rgba(34,211,238,0.5)] hover:shadow-[0_0_45px_rgba(34,211,238,0.8)] transition-all duration-300 flex items-center gap-2.5"
            >
              <span>Explore NEXORA</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => scrollToSection('capabilities')}
              style={{ fontFamily: "'Orbitron', sans-serif" }}
              className="px-7 py-3.5 rounded-xl text-xs sm:text-sm font-bold uppercase tracking-[0.18em] text-cyan-200 bg-slate-900/80 hover:bg-slate-800/90 border border-cyan-400/40 hover:border-cyan-300 shadow-[0_0_20px_rgba(6,182,212,0.15)] transition-all duration-300"
            >
              Discover Capabilities
            </button>
          </div>
        </div>
      </section>

      {/* 3. CAPABILITIES SECTION (8 Premium Glass-Style Cards) */}
      <section
        id="capabilities"
        className="relative py-24 px-4 sm:px-8 max-w-7xl mx-auto border-t border-slate-800/80"
      >
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
          <span
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-xs font-bold uppercase tracking-[0.3em] text-cyan-400"
          >
            24 Verified Engineering Stages
          </span>
          <h2
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-2xl sm:text-4xl font-bold uppercase tracking-[0.12em] text-white"
          >
            Core Platform Capabilities
          </h2>
          <p className="text-sm text-slate-400">
            Every capability card below connects directly to a live, operational studio inside the
            NEXORA AI workspace.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {CAPABILITY_CARDS.map((card) => {
            const IconComponent = card.icon;
            return (
              <div
                key={card.id}
                className="group relative rounded-2xl p-6 bg-gradient-to-b from-slate-900/75 to-[#050b18]/90 backdrop-blur-md border border-slate-800/90 hover:border-cyan-400/50 shadow-lg hover:shadow-[0_0_35px_rgba(6,182,212,0.18)] transition-all duration-300 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-300 group-hover:bg-cyan-500/20 group-hover:scale-105 transition-all">
                      <IconComponent className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full bg-slate-950/90 text-cyan-300 border border-cyan-500/25">
                      {card.stageBadge}
                    </span>
                  </div>

                  <h3
                    style={{ fontFamily: "'Orbitron', sans-serif" }}
                    className="text-base font-bold tracking-wider text-white mb-2 group-hover:text-cyan-200 transition-colors"
                  >
                    {card.title}
                  </h3>

                  <p className="text-xs text-slate-400 leading-relaxed mb-4">{card.description}</p>

                  <ul className="space-y-1.5 mb-6">
                    {card.highlights.map((item) => (
                      <li
                        key={item}
                        className="flex items-center gap-2 text-[11px] text-slate-300"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button
                  onClick={() => handleLaunchWorkspace(card.targetView)}
                  className="w-full py-2.5 px-3 rounded-xl bg-slate-950/90 hover:bg-cyan-500/20 border border-slate-800 group-hover:border-cyan-500/40 text-xs font-semibold text-cyan-300 flex items-center justify-between transition-all"
                >
                  <span>Open Studio</span>
                  <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. HOW IT WORKS: UNDERSTAND -> REASON -> PLAN -> EXECUTE -> VERIFY */}
      <section
        id="how-it-works"
        className="relative py-24 px-4 sm:px-8 bg-[#040915] border-t border-b border-slate-800/80"
      >
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-14 space-y-3">
            <span
              style={{ fontFamily: "'Orbitron', sans-serif" }}
              className="text-xs font-bold uppercase tracking-[0.3em] text-cyan-400"
            >
              Deterministic Execution Loop
            </span>
            <h2
              style={{ fontFamily: "'Orbitron', sans-serif" }}
              className="text-2xl sm:text-4xl font-bold uppercase tracking-[0.12em] text-white"
            >
              How NEXORA AI Works
            </h2>
            <p className="text-sm text-slate-400">
              Every complex task progresses through an auditable five-stage cognitive and execution
              pipeline.
            </p>
          </div>

          {/* 5-Step Sequence Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 mb-8">
            {PIPELINE_STEPS.map((item, idx) => {
              const isActive = idx === activePipelineIdx;
              return (
                <button
                  key={item.name}
                  onClick={() => setActivePipelineIdx(idx)}
                  className={`text-left p-4 rounded-2xl border transition-all ${
                    isActive
                      ? 'bg-cyan-950/40 border-cyan-400 shadow-[0_0_25px_rgba(6,182,212,0.2)]'
                      : 'bg-slate-950/70 border-slate-800/90 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-cyan-400">{item.step}</span>
                    {idx < PIPELINE_STEPS.length - 1 && (
                      <ArrowRight className="w-3.5 h-3.5 text-slate-600 hidden sm:block" />
                    )}
                  </div>
                  <div
                    style={{ fontFamily: "'Orbitron', sans-serif" }}
                    className={`text-sm font-bold uppercase tracking-wider ${
                      isActive ? 'text-white' : 'text-slate-300'
                    }`}
                  >
                    {item.name}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Step Detail Card */}
          <div className="rounded-2xl p-6 sm:p-8 bg-slate-950/90 border border-cyan-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-3xl">
              <div className="flex items-center gap-2.5">
                <span className="px-2.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono text-xs font-bold">
                  STEP {PIPELINE_STEPS[activePipelineIdx].step}:{' '}
                  {PIPELINE_STEPS[activePipelineIdx].name.toUpperCase()}
                </span>
              </div>
              <h3
                style={{ fontFamily: "'Orbitron', sans-serif" }}
                className="text-lg sm:text-xl font-bold text-white"
              >
                {PIPELINE_STEPS[activePipelineIdx].title}
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                {PIPELINE_STEPS[activePipelineIdx].detail}
              </p>
            </div>

            <button
              onClick={() => handleLaunchWorkspace('reasoning')}
              className="shrink-0 px-5 py-3 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-400/40 text-xs font-bold uppercase tracking-wider text-cyan-200 flex items-center gap-2"
            >
              <span>Inspect Reasoning Engine</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* 5. TECHNOLOGY SECTION (Strictly Implemented Capabilities Only) */}
      <section id="technology" className="relative py-24 px-4 sm:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
          <span
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-xs font-bold uppercase tracking-[0.3em] text-cyan-400"
          >
            Verified Production Architecture
          </span>
          <h2
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-2xl sm:text-4xl font-bold uppercase tracking-[0.12em] text-white"
          >
            Engineered for Trust & Precision
          </h2>
          <p className="text-sm text-slate-400">
            Built on transparent, verifiable subsystems—never fabricating benchmarks, compiler
            outputs, or unverified claims.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {TECHNOLOGY_PILLARS.map((pillar) => {
            const IconComp = pillar.icon;
            return (
              <div
                key={pillar.title}
                className="rounded-2xl p-6 bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-300">
                      <IconComp className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-mono text-cyan-300 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                      {pillar.stage}
                    </span>
                  </div>

                  <h3
                    style={{ fontFamily: "'Orbitron', sans-serif" }}
                    className="text-base font-bold text-white mb-2"
                  >
                    {pillar.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">
                    {pillar.description}
                  </p>

                  <div className="space-y-1.5 mb-5">
                    {pillar.metrics.map((m) => (
                      <div
                        key={m}
                        className="text-[11px] font-mono text-slate-300 bg-slate-950/80 px-2.5 py-1.5 rounded border border-slate-800/80"
                      >
                        • {m}
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => handleLaunchWorkspace(pillar.targetView)}
                  className="text-xs font-semibold text-cyan-300 hover:text-cyan-200 flex items-center gap-1.5 pt-2"
                >
                  <span>Explore {pillar.title}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}

          {/* Embedded & Hardware Engineering Card */}
          <div className="rounded-2xl p-6 bg-gradient-to-br from-cyan-950/30 via-slate-900/70 to-slate-950 border border-cyan-500/35 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-400/40 flex items-center justify-center text-cyan-300">
                  <Cpu className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono text-cyan-300 bg-slate-950 px-2.5 py-1 rounded border border-cyan-500/30">
                  Stages 23 & 24
                </span>
              </div>

              <h3
                style={{ fontFamily: "'Orbitron', sans-serif" }}
                className="text-base font-bold text-white mb-2"
              >
                IoT & Embedded Firmware Studio
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed mb-4">
                Plan hardware prototypes across ESP32, Arduino Uno, STM32, and Raspberry Pi, validate
                pin-to-pin electrical netlists, and engineer modular C/C++ and MicroPython firmware.
              </p>

              <div className="space-y-1.5 mb-5">
                <div className="text-[11px] font-mono text-slate-300 bg-slate-950/80 px-2.5 py-1.5 rounded border border-slate-800/80">
                  • Electrical & Pin Conflict Validator
                </div>
                <div className="text-[11px] font-mono text-slate-300 bg-slate-950/80 px-2.5 py-1.5 rounded border border-slate-800/80">
                  • Static Embedded Safety Analyzer
                </div>
                <div className="text-[11px] font-mono text-slate-300 bg-slate-950/80 px-2.5 py-1.5 rounded border border-slate-800/80">
                  • Approval-Gated Device Flashing
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => handleLaunchWorkspace('iot')}
                className="text-xs font-semibold text-cyan-300 hover:text-cyan-200 flex items-center gap-1"
              >
                <span>IoT Builder</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <span className="text-slate-600">|</span>
              <button
                onClick={() => handleLaunchWorkspace('firmware')}
                className="text-xs font-semibold text-emerald-300 hover:text-emerald-200 flex items-center gap-1"
              >
                <span>Firmware Studio</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 6. MISSION SECTION */}
      <section
        id="mission"
        className="relative py-24 px-4 sm:px-8 bg-gradient-to-b from-[#040915] to-[#02050b] border-t border-slate-800/80"
      >
        <div className="max-w-5xl mx-auto rounded-3xl p-8 sm:p-12 bg-slate-900/50 border border-cyan-500/25 shadow-[0_0_50px_rgba(6,182,212,0.1)] space-y-6 text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold uppercase tracking-widest">
            <Layers className="w-3.5 h-3.5" />
            <span>Our Engineering Mission</span>
          </div>

          <h2
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-2xl sm:text-4xl font-bold uppercase tracking-[0.12em] text-white"
          >
            Turning Ideas Into Practical, Verified Outcomes
          </h2>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-3xl mx-auto">
            NEXORA AI is built as a unified workspace where research, reasoning, software
            development, knowledge graphs, and hardware prototyping converge. Instead of switching
            between disconnected tools—or trusting unverified black-box answers—NEXORA links every
            answer to its underlying evidence, source citations, compiler diagnostics, and user
            approval controls.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 text-left">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-cyan-300 mb-1">
                Honest Epistemics
              </div>
              <p className="text-xs text-slate-400">
                Explicitly distinguishes primary evidence, peer-reviewed research, and verified
                compiler outputs from AI inferences or unconfigured tools.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-cyan-300 mb-1">
                Human-in-the-Loop Safety
              </div>
              <p className="text-xs text-slate-400">
                Consequential actions—file deletions, Git commits, package installs, and hardware
                flashing—always require explicit user review and approval.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-cyan-300 mb-1">
                End-to-End Continuity
              </div>
              <p className="text-xs text-slate-400">
                Move seamlessly from deep literature discovery to knowledge graph modeling, code
                execution, and embedded firmware generation in one workspace.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 7. FINAL CTA SECTION */}
      <section className="relative py-24 px-4 sm:px-8 text-center border-t border-slate-800/80 overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 flex items-center justify-center"
        >
          <div className="w-[600px] h-[300px] rounded-full bg-cyan-500/10 blur-[120px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto space-y-6">
          <p
            style={{ fontFamily: "'Rajdhani', sans-serif" }}
            className="text-xs sm:text-sm font-bold uppercase tracking-[0.4em] text-cyan-400"
          >
            INTELLIGENCE. BEYOND LIMITS.
          </p>

          <h2
            style={{ fontFamily: "'Orbitron', sans-serif" }}
            className="text-2xl sm:text-4xl md:text-5xl font-extrabold uppercase tracking-[0.14em] text-white leading-tight"
          >
            YOUR IDEAS. YOUR INTELLIGENCE. YOUR NEXT MOVE.
          </h2>

          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Enter the full NEXORA AI workspace to start chatting, researching, building workflows,
            writing code, or engineering embedded systems.
          </p>

          <div className="pt-3 flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={() => handleLaunchWorkspace('chat')}
              style={{ fontFamily: "'Orbitron', sans-serif" }}
              className="px-8 py-4 rounded-xl text-xs sm:text-sm font-bold uppercase tracking-[0.2em] text-slate-950 bg-gradient-to-r from-cyan-300 via-cyan-400 to-sky-400 hover:from-cyan-200 hover:to-cyan-300 shadow-[0_0_35px_rgba(34,211,238,0.55)] hover:shadow-[0_0_50px_rgba(34,211,238,0.85)] transition-all duration-300 flex items-center gap-3"
            >
              <span>Launch NEXORA AI</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => setSetupGuideModalOpen(true)}
              className="px-6 py-4 rounded-xl text-xs font-semibold uppercase tracking-wider text-slate-200 bg-slate-900 hover:bg-slate-800 border border-slate-700 flex items-center gap-2 transition-colors"
            >
              <BookOpen className="w-4 h-4 text-cyan-400" />
              <span>Architecture & Setup Guide</span>
            </button>
          </div>
        </div>
      </section>

      {/* 8. FOOTER */}
      <footer className="border-t border-slate-800/80 bg-[#010307] py-12 px-4 sm:px-8 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div className="space-y-2">
            <div className="flex items-center gap-2.5">
              <img
                src="assets/nexora-eagle-logo.jpg"
                alt="NEXORA AI Logo"
                className="w-7 h-7 rounded-lg object-cover border border-cyan-400/40 shadow-[0_0_12px_rgba(6,182,212,0.25)]"
              />
              <span
                style={{ fontFamily: "'Orbitron', sans-serif" }}
                className="text-sm font-bold tracking-[0.25em] text-cyan-400"
              >
                NEXORA AI
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                Stages 1–27 Operational
              </span>
              <span
                className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded ${
                  isBackendConnected
                    ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                    : 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                }`}
              >
                {isBackendConnected ? 'Backend Online' : 'Offline Mode Ready'}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 max-w-md">
              Privacy & Security: Encrypted local memory vault (`enc:v1`), automatic PII/secret
              redaction, strict workspace path isolation, and explicit user approval gates.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs">
            <button
              onClick={() => scrollToSection('hero')}
              className="hover:text-cyan-300 transition-colors"
            >
              Home
            </button>
            <button
              onClick={() => scrollToSection('capabilities')}
              className="hover:text-cyan-300 transition-colors"
            >
              Capabilities
            </button>
            <button
              onClick={() => scrollToSection('technology')}
              className="hover:text-cyan-300 transition-colors"
            >
              Technology
            </button>
            <button
              onClick={() => scrollToSection('mission')}
              className="hover:text-cyan-300 transition-colors"
            >
              About
            </button>
            <button
              onClick={() => setSetupGuideModalOpen(true)}
              className="hover:text-cyan-300 transition-colors"
            >
              Documentation
            </button>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-cyan-300 transition-colors"
            >
              OpenAPI Reference
            </a>
            <button
              onClick={() => handleLaunchWorkspace('chat')}
              className="text-cyan-400 hover:text-cyan-300 font-semibold"
            >
              Launch Workspace →
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};
