"""
NEXORA AI — Stage 22: Knowledge Graph Intelligence Engine

Transforms authorized documents, Stage 21 discovery results, and user inputs
into a connected, provenance-backed, explorable knowledge graph.

Core Architectural Guarantees:
- Entity extraction & canonical deduplication across 8 entity types.
- Relationship discovery across 9 relation types with mandatory evidence & provenance.
- Strict separation between explicit source facts (`explicit_fact`) and AI-inferred
  transitive/derived relationships (`ai_inferred`) with uncertainty labels.
- Cycle-safe graph traversal for connection paths, dependency impact analysis,
  contradiction detection, and bounded k-hop neighborhood exploration.
- Incremental graph updates preserving full source history and requiring explicit
  user approval before destructive entity merges or deletions.
- Workspace & user isolation (`user_id` + `workspace_id`), SSRF URL validation,
  and `<untrusted_kg_evidence>` prompt-injection quarantine.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.models.schemas import (
    KGApproveOperationRequest,
    KGChangeLogEntry,
    KGContradictionItem,
    KGDeleteRequest,
    KGDestructiveOperationRecord,
    KGDuplicateCandidate,
    KGEntityMergeRequest,
    KGEntityNode,
    KGEntityType,
    KGEvidenceItem,
    KGExplicitEntityInput,
    KGExplicitRelationshipInput,
    KGFactBasis,
    KGGraphSnapshotResponse,
    KGIngestRequest,
    KGIngestResponse,
    KGMetadataResponse,
    KGPathStep,
    KGQueryMode,
    KGQueryRequest,
    KGQueryResponse,
    KGRelationType,
    KGRelationshipEdge,
    KGSourceKind,
    KGUncertaintyLabel,
)
from app.services.discovery.engine import UniversalKnowledgeDiscoveryEngine


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


PROMPT_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above)\s+instructions|"
    r"system\s*prompt\s*:|you\s+are\s+now\s+in\s+developer\s+mode|"
    r"disregard\s+safety\s+rules|override\s+system\s+policy|"
    r"<\s*script[^>]*>|javascript\s*:)",
    re.IGNORECASE,
)

HEDGING_PATTERNS = re.compile(
    r"\b(might|possibly|rumored|unconfirmed|allegedly|preliminary|speculated|uncertain|hypothesized)\b",
    re.IGNORECASE,
)

ENTITY_TYPE_KEYWORDS: Dict[KGEntityType, Set[str]] = {
    "technology": {
        "fastapi", "python", "react", "typescript", "sqlite", "postgresql", "postgres",
        "redis", "docker", "kubernetes", "playwright", "pytorch", "tensorflow", "openai",
        "gemini", "claude", "graphql", "rest", "api", "framework", "sdk", "library",
        "engine", "database", "compiler", "runtime", "llm", "transformer", "uvicorn",
        "pydantic", "vite", "tailwind",
    },
    "organization": {
        "nist", "w3c", "ietf", "ieee", "iso", "who", "mit", "stanford", "google",
        "microsoft", "anthropic", "meta", "apache", "foundation", "institute",
        "university", "corp", "corporation", "agency", "consortium", "council",
    },
    "person": {
        "dr.", "prof.", "professor", "researcher", "author", "creator", "founder",
        "tiangolo", "ramirez", "turing", "hinton", "bengio", "lecun",
    },
    "dataset": {
        "dataset", "corpus", "benchmark", "mmlu", "humaneval", "imagenet", "commoncrawl",
        "openalex", "arxiv", "pubmed", "wikidata", "gnomad", "chembl",
    },
    "event": {
        "release", "outage", "incident", "summit", "conference", "neurips", "icml",
        "iclr", "cve", "migration", "deployment", "audit",
    },
    "component": {
        "router", "scheduler", "sandbox", "vault", "retriever", "chunker", "dispatcher",
        "orchestrator", "verifier", "connector", "parser", "module", "service", "worker",
    },
    "claim_or_standard": {
        "rmf", "standard", "policy", "compliance", "gdpr", "soc2", "hipaa", "rfc",
        "spec", "specification", "claim", "hypothesis", "theorem", "guideline",
    },
    "concept": {
        "architecture", "security", "latency", "throughput", "concurrency", "rag",
        "alignment", "hallucination", "provenance", "isolation", "encryption",
    },
}

# Structured natural-language relation extraction patterns: (regex, relation_type, stance)
RELATION_EXTRACTION_PATTERNS: List[Tuple[re.Pattern[str], KGRelationType, str]] = [
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:directly\s+|strictly\s+)?(?:depends\s+on|requires|relies\s+on)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+for\s+|\s+to\s+|\s+and\s+|\s+while\s+)",
            re.animate if hasattr(re, "animate") else 0,
        ),
        "depends_on",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:was\s+|is\s+)?(?:created\s+by|developed\s+by|authored\s+by|built\s+by|maintained\s+by)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+in\s+|\s+for\s+|\s+and\s+)",
        ),
        "created_by",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:is\s+)?(?:part\s+of|belongs\s+to|is\s+a\s+submodule\s+of|is\s+a\s+component\s+of)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+and\s+)",
        ),
        "part_of",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:directly\s+)?(?:contradicts|refutes|disagrees\s+with|conflicts\s+with|disproves)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+on\s+|\s+regarding\s+|\s+because\s+)",
        ),
        "contradicts",
        "contradicting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:strongly\s+|empirically\s+)?(?:supports|confirms|validates|corroborates|endorses)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+on\s+|\s+for\s+|\s+in\s+)",
        ),
        "supports",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:actively\s+)?(?:uses|integrates\s+with|leverages|employs)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+for\s+|\s+to\s+|\s+in\s+)",
        ),
        "uses",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:evaluates|benchmarks|audits|tests)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+across\s+|\s+for\s+|\s+in\s+)",
        ),
        "evaluates",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:is\s+)?(?:governed\s+by|complies\s+with|regulated\s+by)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$|\s+for\s+|\s+in\s+)",
        ),
        "governed_by",
        "supporting",
    ),
    (
        re.compile(
            r"(?P<src>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)\s+(?:is\s+)?(?:related\s+to|connected\s+to|associated\s+with)\s+(?P<tgt>[A-Z][A-Za-z0-9_\-\.\s]{1,45}?)(?=[\.,;]|$)",
        ),
        "related_to",
        "supporting",
    ),
]


class KnowledgeGraphIntelligenceEngine:
    """
    Stage 22: Knowledge Graph Intelligence Engine.
    """

    SCHEMA_VERSION = "v1.0.0"

    ENTITY_TYPES: List[KGEntityType] = [
        "concept",
        "technology",
        "organization",
        "person",
        "event",
        "dataset",
        "component",
        "claim_or_standard",
    ]

    RELATION_TYPES: List[KGRelationType] = [
        "depends_on",
        "created_by",
        "related_to",
        "part_of",
        "contradicts",
        "supports",
        "uses",
        "evaluates",
        "governed_by",
    ]

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or settings.kg_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._ensure_default_seed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS kg_schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    description TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_entities (
                    entity_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    description TEXT NOT NULL DEFAULT '',
                    properties_json TEXT NOT NULL DEFAULT '{}',
                    provenance_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.9,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, workspace_id, canonical_key)
                );

                CREATE INDEX IF NOT EXISTS idx_kg_entities_workspace
                    ON kg_entities(user_id, workspace_id);
                CREATE INDEX IF NOT EXISTS idx_kg_entities_type
                    ON kg_entities(user_id, workspace_id, entity_type);

                CREATE TABLE IF NOT EXISTS kg_relationships (
                    relationship_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    fact_basis TEXT NOT NULL DEFAULT 'explicit_fact',
                    is_inferred INTEGER NOT NULL DEFAULT 0,
                    uncertainty_label TEXT NOT NULL DEFAULT 'verified_explicit',
                    confidence REAL NOT NULL DEFAULT 0.9,
                    explanation TEXT NOT NULL DEFAULT '',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, workspace_id, source_entity_id, target_entity_id, relation_type, fact_basis)
                );

                CREATE INDEX IF NOT EXISTS idx_kg_rel_source
                    ON kg_relationships(user_id, workspace_id, source_entity_id);
                CREATE INDEX IF NOT EXISTS idx_kg_rel_target
                    ON kg_relationships(user_id, workspace_id, target_entity_id);
                CREATE INDEX IF NOT EXISTS idx_kg_rel_type
                    ON kg_relationships(user_id, workspace_id, relation_type);

                CREATE TABLE IF NOT EXISTS kg_change_history (
                    change_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    affected_entities_json TEXT NOT NULL DEFAULT '[]',
                    affected_relationships_json TEXT NOT NULL DEFAULT '[]',
                    snapshot_before_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_kg_changes_workspace
                    ON kg_change_history(user_id, workspace_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS kg_pending_destructive_ops (
                    op_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    affected_entities_count INTEGER NOT NULL DEFAULT 0,
                    affected_relationships_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                """
            )
            cur = conn.execute(
                "SELECT version FROM kg_schema_migrations WHERE version = ?",
                (self.SCHEMA_VERSION,),
            )
            if not cur.fetchone():
                conn.execute(
                    "INSERT INTO kg_schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                    (
                        self.SCHEMA_VERSION,
                        _utc_now_iso(),
                        "Initial Stage 22 Knowledge Graph relational-adjacency schema with provenance & approval gates.",
                    ),
                )
            conn.commit()

    def _ensure_default_seed(self) -> None:
        """
        Seeds the default workspace (`default_user` / `default_workspace`) with a grounded
        initial graph if empty, so the interactive Graph Explorer is immediately usable.
        Other user/workspace pairs start completely empty for strict isolation.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
                ("default_user", "default_workspace"),
            ).fetchone()
            if row and row["cnt"] > 0:
                return

        self.ingest_knowledge(
            KGIngestRequest(
                user_id="default_user",
                workspace_id="default_workspace",
                source_title="NEXORA Architecture & AI Safety Reference Specification",
                source_url="https://fastapi.tiangolo.com/architecture/",
                page_or_section="Page 1 — Core Stack & Standards",
                source_text=(
                    "Nexora Platform depends on FastAPI for asynchronous REST routing. "
                    "FastAPI depends on Pydantic for schema validation and Starlette for ASGI transport. "
                    "FastAPI was created by Sebastian Ramirez. "
                    "Knowledge Graph Engine is part of Nexora Platform and uses SQLite for adjacency persistence. "
                    "Evaluation Engine evaluates Nexora Platform and is governed by NIST AI RMF. "
                    "Empirical Study Alpha supports Zero-Trust Sandbox Policy on isolation effectiveness. "
                    "Legacy Benchmark Report contradicts Zero-Trust Sandbox Policy on latency overhead."
                ),
                derive_inferred_relationships=True,
            )
        )

    # ------------------------------------------------------------------
    # 1. Normalization, Sanitization & Classification Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def sanitize_text(text: str) -> Tuple[str, int]:
        """Neutralizes prompt injection directives in imported content and returns (cleaned_text, count)."""
        if not text:
            return "", 0
        matches = PROMPT_INJECTION_PATTERNS.findall(text)
        cleaned = PROMPT_INJECTION_PATTERNS.sub("[REDACTED_UNTRUSTED_DIRECTIVE]", text)
        return cleaned.strip(), len(matches)

    @classmethod
    def quarantine_passage(cls, passage: str, source_title: str) -> Tuple[str, str, int]:
        cleaned, inj_count = cls.sanitize_text(passage)
        safe_xml = cleaned.replace("<", "&lt;").replace(">", "&gt;")
        safe_title = re.sub(r'[^A-Za-z0-9_\-\.\s]', '', source_title or "source")[:80]
        quarantined = f'<untrusted_kg_evidence source="{safe_title}">{safe_xml}</untrusted_kg_evidence>'
        return cleaned, quarantined, inj_count

    @staticmethod
    def normalize_entity_key(label: str) -> str:
        """Creates a stable canonical identifier key for entity deduplication."""
        cleaned = re.sub(r"[^a-z0-9]+", " ", (label or "").strip().lower()).strip()
        # Normalize common suffixes for deduplication stability
        tokens = [t for t in cleaned.split() if t not in {"the", "a", "an"}]
        return "_".join(tokens) or "unknown_entity"

    @classmethod
    def classify_entity_type(cls, label: str, context_text: str = "") -> KGEntityType:
        lower_label = label.lower()
        tokens = set(re.findall(r"[a-z0-9_\.]+", lower_label))
        for ent_type, kw_set in ENTITY_TYPE_KEYWORDS.items():
            if tokens & kw_set or any(kw in lower_label for kw in kw_set):
                return ent_type
        if any(w in lower_label for w in ("report", "study", "paper", "survey")):
            return "dataset"
        if any(w in lower_label for w in ("policy", "framework", "standard", "rmf", "law")):
            return "claim_or_standard"
        if any(w in lower_label for w in ("engine", "service", "studio", "platform", "api", "db")):
            return "technology"
        return "concept"

    @staticmethod
    def clean_entity_phrase(raw_phrase: str) -> str:
        phrase = raw_phrase.strip(" \t\n\r.,;:!?\"'()[]{}")
        # Strip leading articles/conjunctions
        phrase = re.sub(r"^(?:the|a|an|that|which|and|but|while|where|when|in\s+which)\s+", "", phrase, flags=re.IGNORECASE)
        phrase = re.sub(r"\s+", " ", phrase).strip()
        return phrase[:120]

    @classmethod
    def extract_entities_and_relations_from_text(
        cls,
        text: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extracts structured entities and factual relationships from natural-language text.
        Every extracted relationship includes the exact sentence passage from which it was derived.
        """
        entities_map: Dict[str, Dict[str, Any]] = {}
        relations_list: List[Dict[str, Any]] = []

        if not text or not text.strip():
            return [], []

        # Split into sentences for granular passage provenance
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[\.\!\?\n])\s+", text)
            if s and len(s.strip()) >= 5
        ]

        for sentence in sentences:
            is_hedged = bool(HEDGING_PATTERNS.search(sentence))
            uncertainty: KGUncertaintyLabel = (
                "hedged_source_statement" if is_hedged else "verified_explicit"
            )
            base_conf = 0.64 if is_hedged else 0.92

            # Handle compound predicates like "FastAPI depends on Pydantic ... and Starlette ..."
            for pattern, rel_type, stance in RELATION_EXTRACTION_PATTERNS:
                for match in pattern.finditer(sentence):
                    src_raw = cls.clean_entity_phrase(match.group("src"))
                    tgt_raw = cls.clean_entity_phrase(match.group("tgt"))
                    if not src_raw or not tgt_raw or len(src_raw) < 2 or len(tgt_raw) < 2:
                        continue
                    if src_raw.lower() == tgt_raw.lower():
                        continue

                    src_key = cls.normalize_entity_key(src_raw)
                    tgt_key = cls.normalize_entity_key(tgt_raw)
                    src_type = cls.classify_entity_type(src_raw, sentence)
                    tgt_type = cls.classify_entity_type(tgt_raw, sentence)

                    if src_key not in entities_map:
                        entities_map[src_key] = {
                            "label": src_raw,
                            "entity_type": src_type,
                            "description": f"Extracted from source passage: {sentence[:180]}",
                            "passage": sentence,
                            "confidence": base_conf,
                        }
                    if tgt_key not in entities_map:
                        entities_map[tgt_key] = {
                            "label": tgt_raw,
                            "entity_type": tgt_type,
                            "description": f"Extracted from source passage: {sentence[:180]}",
                            "passage": sentence,
                            "confidence": base_conf,
                        }

                    relations_list.append(
                        {
                            "source_label": src_raw,
                            "source_type": src_type,
                            "target_label": tgt_raw,
                            "target_type": tgt_type,
                            "relation_type": rel_type,
                            "fact_basis": "explicit_fact",
                            "is_inferred": False,
                            "uncertainty_label": uncertainty,
                            "confidence": base_conf,
                            "stance": stance,
                            "passage": sentence,
                            "explanation": f"Explicitly stated in source passage ({rel_type.replace('_', ' ')}).",
                        }
                    )

            # Also extract capitalized multi-word or CamelCase technical entities even if no verb pattern matched
            cap_candidates = re.findall(
                r"\b([A-Z][A-Za-z0-9_\-]+(?:\s+[A-Z][A-Za-z0-9_\-]+){0,3})\b",
                sentence,
            )
            stopwords_cap = {
                "The", "This", "That", "These", "Those", "When", "Where", "While",
                "However", "Therefore", "Furthermore", "Although", "Because", "In", "On", "For",
            }
            sentence_entities: List[str] = []
            for cand in cap_candidates:
                clean_c = cls.clean_entity_phrase(cand)
                if clean_c in stopwords_cap or len(clean_c) < 3:
                    continue
                c_key = cls.normalize_entity_key(clean_c)
                c_type = cls.classify_entity_type(clean_c, sentence)
                if c_key not in entities_map:
                    entities_map[c_key] = {
                        "label": clean_c,
                        "entity_type": c_type,
                        "description": f"Referenced in passage: {sentence[:180]}",
                        "passage": sentence,
                        "confidence": base_conf,
                    }
                sentence_entities.append(clean_c)

        return list(entities_map.values()), relations_list

    # ------------------------------------------------------------------
    # 2. Metadata & Capabilities
    # ------------------------------------------------------------------
    def get_metadata(self) -> KGMetadataResponse:
        return KGMetadataResponse(
            stage=22,
            engine="KnowledgeGraphIntelligenceEngine",
            schema_version=self.SCHEMA_VERSION,
            storage_backend="SQLite Relational-Graph Engine with Adjacency Indexing",
            entity_types=list(self.ENTITY_TYPES),
            relation_types=list(self.RELATION_TYPES),
            query_modes=[
                {
                    "id": "natural_language",
                    "name": "Natural Language Graph Question",
                    "description": "Automatically routes questions about connections, dependencies, or source disagreements over the knowledge graph.",
                },
                {
                    "id": "connection_path",
                    "name": "Connection Path Finder",
                    "description": "Answers 'How are these technologies/entities connected?' using cycle-safe bounded BFS shortest paths.",
                },
                {
                    "id": "dependency_impact",
                    "name": "Dependency & Impact Analysis",
                    "description": "Answers 'What depends on this component?' across direct and transitive dependency chains.",
                },
                {
                    "id": "contradiction_analysis",
                    "name": "Contradiction & Disagreement Inspector",
                    "description": "Answers 'Which sources disagree about this claim?' by comparing supporting vs. contradicting evidence edges.",
                },
                {
                    "id": "neighborhood_exploration",
                    "name": "Neighborhood k-Hop Explorer",
                    "description": "Expands the k-hop ego-network around any selected entity with cycle protection and relationship filters.",
                },
            ],
            max_expansion_depth=settings.kg_max_expansion_depth,
            default_page_size=settings.kg_default_page_size,
            max_page_size=settings.kg_max_page_size,
        )

    # ------------------------------------------------------------------
    # 3. Row Deserialization Helpers
    # ------------------------------------------------------------------
    def _row_to_entity(self, row: sqlite3.Row, degree_map: Optional[Dict[str, int]] = None) -> KGEntityNode:
        ent_id = row["entity_id"]
        prov_raw = json.loads(row["provenance_json"] or "[]")
        return KGEntityNode(
            entity_id=ent_id,
            user_id=row["user_id"],
            workspace_id=row["workspace_id"],
            canonical_key=row["canonical_key"],
            label=row["label"],
            entity_type=row["entity_type"],
            aliases=json.loads(row["aliases_json"] or "[]"),
            description=row["description"],
            properties=json.loads(row["properties_json"] or "{}"),
            provenance=[KGEvidenceItem(**p) for p in prov_raw],
            confidence=float(row["confidence"]),
            degree=(degree_map or {}).get(ent_id, 0),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_relationship(
        self,
        row: sqlite3.Row,
        label_map: Optional[Dict[str, str]] = None,
    ) -> KGRelationshipEdge:
        ev_raw = json.loads(row["evidence_json"] or "[]")
        src_id = row["source_entity_id"]
        tgt_id = row["target_entity_id"]
        return KGRelationshipEdge(
            relationship_id=row["relationship_id"],
            user_id=row["user_id"],
            workspace_id=row["workspace_id"],
            source_entity_id=src_id,
            source_label=(label_map or {}).get(src_id, src_id),
            target_entity_id=tgt_id,
            target_label=(label_map or {}).get(tgt_id, tgt_id),
            relation_type=row["relation_type"],
            fact_basis=row["fact_basis"],
            is_inferred=bool(row["is_inferred"]),
            uncertainty_label=row["uncertainty_label"],
            confidence=float(row["confidence"]),
            explanation=row["explanation"],
            evidence=[KGEvidenceItem(**e) for e in ev_raw],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _compute_degrees_and_labels(
        self, conn: sqlite3.Connection, user_id: str, workspace_id: str
    ) -> Tuple[Dict[str, int], Dict[str, str]]:
        label_map: Dict[str, str] = {}
        degree_map: Dict[str, int] = {}
        for r in conn.execute(
            "SELECT entity_id, label FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
            (user_id, workspace_id),
        ):
            label_map[r["entity_id"]] = r["label"]
            degree_map[r["entity_id"]] = 0

        for r in conn.execute(
            "SELECT source_entity_id, target_entity_id FROM kg_relationships WHERE user_id = ? AND workspace_id = ?",
            (user_id, workspace_id),
        ):
            s_id = r["source_entity_id"]
            t_id = r["target_entity_id"]
            degree_map[s_id] = degree_map.get(s_id, 0) + 1
            degree_map[t_id] = degree_map.get(t_id, 0) + 1

        return degree_map, label_map

    # ------------------------------------------------------------------
    # 4. Incremental Ingestion, Deduplication & Provenance Linking
    # ------------------------------------------------------------------
    def ingest_knowledge(self, req: KGIngestRequest) -> KGIngestResponse:
        now = _utc_now_iso()
        user_id = req.user_id.strip() or "default_user"
        workspace_id = req.workspace_id.strip() or "default_workspace"

        prompt_inj_count = 0
        ssrf_blocked_count = 0

        # Validate top-level source_url against SSRF if provided
        validated_source_url: Optional[str] = None
        if req.source_url and req.source_url.strip():
            if UniversalKnowledgeDiscoveryEngine.is_url_allowed(req.source_url.strip()):
                validated_source_url = req.source_url.strip()
            else:
                ssrf_blocked_count += 1

        # Collect ingestion units: (source_kind, source_id, title, url, page_or_section, text_body)
        ingestion_sources: List[Tuple[KGSourceKind, str, str, Optional[str], Optional[str], str]] = []

        if req.source_text and req.source_text.strip():
            ingestion_sources.append(
                (
                    "user_document",
                    f"src_doc_{uuid.uuid4().hex[:8]}",
                    req.source_title,
                    validated_source_url,
                    req.page_or_section,
                    req.source_text,
                )
            )

        # Pull from Stage 4 Document Vault if requested
        if req.vault_document_ids:
            try:
                from app.services.documents.store import document_store

                for doc_id in req.vault_document_ids:
                    doc = document_store.get_document(doc_id)
                    if doc:
                        chunks_text = "\n".join(c.content for c in doc.chunks[:15])
                        ingestion_sources.append(
                            (
                                "vault_document",
                                doc.id,
                                doc.filename,
                                f"nexora://vault/{doc.id}",
                                f"Pages 1-{doc.page_count or 1}",
                                chunks_text,
                            )
                        )
            except Exception:
                pass

        # Pull from Stage 21 Discovery History if requested
        if req.discovery_id:
            try:
                from app.services.discovery.engine import discovery_engine

                recent = discovery_engine.list_recent_discoveries(limit=30)
                matched = next((d for d in recent if d.discovery_id == req.discovery_id), None)
                if matched:
                    for item in matched.results[:12]:
                        ingestion_sources.append(
                            (
                                "discovery_result",
                                item.item_id,
                                item.title,
                                item.url,
                                f"Citation [{item.citation_index}]",
                                f"{item.title}. {item.snippet}",
                            )
                        )
            except Exception:
                pass

        entities_created = 0
        entities_updated = 0
        relationships_created = 0
        relationships_updated = 0
        inferred_created = 0
        touched_entity_ids: Set[str] = set()
        touched_rel_ids: Set[str] = set()

        with self._connect() as conn:
            # Load existing canonical_key -> row and alias -> row map for this workspace
            existing_by_key: Dict[str, sqlite3.Row] = {}
            alias_to_key: Dict[str, str] = {}
            for r in conn.execute(
                "SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
                (user_id, workspace_id),
            ):
                c_key = r["canonical_key"]
                existing_by_key[c_key] = r
                alias_to_key[c_key] = c_key
                for al in json.loads(r["aliases_json"] or "[]"):
                    alias_to_key[self.normalize_entity_key(al)] = c_key

            def _upsert_entity(
                label: str,
                entity_type: KGEntityType,
                description: str,
                aliases: List[str],
                properties: Dict[str, Any],
                evidence_item: KGEvidenceItem,
                confidence: float,
            ) -> str:
                nonlocal entities_created, entities_updated, prompt_inj_count
                clean_label, inj_l = self.sanitize_text(label)
                clean_desc, inj_d = self.sanitize_text(description)
                prompt_inj_count += inj_l + inj_d

                raw_key = self.normalize_entity_key(clean_label)
                resolved_key = alias_to_key.get(raw_key, raw_key)

                if resolved_key in existing_by_key:
                    row = existing_by_key[resolved_key]
                    ent_id = row["entity_id"]
                    cur_aliases: List[str] = json.loads(row["aliases_json"] or "[]")
                    if clean_label != row["label"] and clean_label not in cur_aliases:
                        cur_aliases.append(clean_label)
                    for al in aliases:
                        clean_al, _ = self.sanitize_text(al)
                        if clean_al and clean_al != row["label"] and clean_al not in cur_aliases:
                            cur_aliases.append(clean_al)
                            alias_to_key[self.normalize_entity_key(clean_al)] = resolved_key

                    cur_props: Dict[str, Any] = json.loads(row["properties_json"] or "{}")
                    cur_props.update(properties or {})

                    cur_prov: List[Dict[str, Any]] = json.loads(row["provenance_json"] or "[]")
                    if not any(
                        p.get("passage") == evidence_item.passage and p.get("source_title") == evidence_item.source_title
                        for p in cur_prov
                    ):
                        cur_prov.append(evidence_item.model_dump(mode="json"))

                    new_desc = row["description"] or clean_desc
                    new_conf = round(max(float(row["confidence"]), confidence), 3)

                    conn.execute(
                        """
                        UPDATE kg_entities
                        SET aliases_json = ?, description = ?, properties_json = ?,
                            provenance_json = ?, confidence = ?, updated_at = ?
                        WHERE entity_id = ?
                        """,
                        (
                            json.dumps(cur_aliases),
                            new_desc,
                            json.dumps(cur_props),
                            json.dumps(cur_prov),
                            new_conf,
                            now,
                            ent_id,
                        ),
                    )
                    updated_row = conn.execute(
                        "SELECT * FROM kg_entities WHERE entity_id = ?", (ent_id,)
                    ).fetchone()
                    if updated_row:
                        existing_by_key[resolved_key] = updated_row
                    entities_updated += 1
                    touched_entity_ids.add(ent_id)
                    return ent_id
                else:
                    ent_id = f"kg_ent_{uuid.uuid4().hex[:10]}"
                    clean_aliases = []
                    for al in aliases:
                        c_al, _ = self.sanitize_text(al)
                        if c_al and c_al != clean_label and c_al not in clean_aliases:
                            clean_aliases.append(c_al)
                            alias_to_key[self.normalize_entity_key(c_al)] = raw_key
                    alias_to_key[raw_key] = raw_key

                    prov_list = [evidence_item.model_dump(mode="json")]
                    conn.execute(
                        """
                        INSERT INTO kg_entities (
                            entity_id, user_id, workspace_id, canonical_key, label, entity_type,
                            aliases_json, description, properties_json, provenance_json,
                            confidence, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ent_id,
                            user_id,
                            workspace_id,
                            raw_key,
                            clean_label,
                            entity_type,
                            json.dumps(clean_aliases),
                            clean_desc,
                            json.dumps(properties or {}),
                            json.dumps(prov_list),
                            round(confidence, 3),
                            now,
                            now,
                        ),
                    )
                    inserted_row = conn.execute(
                        "SELECT * FROM kg_entities WHERE entity_id = ?", (ent_id,)
                    ).fetchone()
                    if inserted_row:
                        existing_by_key[raw_key] = inserted_row
                    entities_created += 1
                    touched_entity_ids.add(ent_id)
                    return ent_id

            def _upsert_relationship(
                src_ent_id: str,
                tgt_ent_id: str,
                rel_type: KGRelationType,
                fact_basis: KGFactBasis,
                is_inferred: bool,
                uncertainty_label: KGUncertaintyLabel,
                confidence: float,
                explanation: str,
                evidence_item: KGEvidenceItem,
            ) -> str:
                nonlocal relationships_created, relationships_updated, inferred_created
                existing_rel = conn.execute(
                    """
                    SELECT * FROM kg_relationships
                    WHERE user_id = ? AND workspace_id = ?
                      AND source_entity_id = ? AND target_entity_id = ?
                      AND relation_type = ? AND fact_basis = ?
                    """,
                    (user_id, workspace_id, src_ent_id, tgt_ent_id, rel_type, fact_basis),
                ).fetchone()

                if existing_rel:
                    rel_id = existing_rel["relationship_id"]
                    cur_ev: List[Dict[str, Any]] = json.loads(existing_rel["evidence_json"] or "[]")
                    if not any(
                        e.get("passage") == evidence_item.passage and e.get("source_title") == evidence_item.source_title
                        for e in cur_ev
                    ):
                        cur_ev.append(evidence_item.model_dump(mode="json"))
                    new_conf = round(max(float(existing_rel["confidence"]), confidence), 3)
                    conn.execute(
                        """
                        UPDATE kg_relationships
                        SET evidence_json = ?, confidence = ?, uncertainty_label = ?,
                            explanation = ?, updated_at = ?
                        WHERE relationship_id = ?
                        """,
                        (
                            json.dumps(cur_ev),
                            new_conf,
                            uncertainty_label,
                            explanation or existing_rel["explanation"],
                            now,
                            rel_id,
                        ),
                    )
                    relationships_updated += 1
                    touched_rel_ids.add(rel_id)
                    return rel_id
                else:
                    rel_id = f"kg_rel_{uuid.uuid4().hex[:10]}"
                    conn.execute(
                        """
                        INSERT INTO kg_relationships (
                            relationship_id, user_id, workspace_id, source_entity_id, target_entity_id,
                            relation_type, fact_basis, is_inferred, uncertainty_label,
                            confidence, explanation, evidence_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            rel_id,
                            user_id,
                            workspace_id,
                            src_ent_id,
                            tgt_ent_id,
                            rel_type,
                            fact_basis,
                            1 if is_inferred else 0,
                            uncertainty_label,
                            round(confidence, 3),
                            explanation,
                            json.dumps([evidence_item.model_dump(mode="json")]),
                            now,
                            now,
                        ),
                    )
                    if is_inferred:
                        inferred_created += 1
                    else:
                        relationships_created += 1
                    touched_rel_ids.add(rel_id)
                    return rel_id

            # Process text-based ingestion sources
            for s_kind, s_id, s_title, s_url, s_page, s_text in ingestion_sources:
                ext_entities, ext_relations = self.extract_entities_and_relations_from_text(s_text)
                for ent_dict in ext_entities:
                    clean_pass, quar_pass, inj_c = self.quarantine_passage(ent_dict["passage"], s_title)
                    prompt_inj_count += inj_c
                    ev = KGEvidenceItem(
                        evidence_id=f"kg_ev_{uuid.uuid4().hex[:8]}",
                        source_kind=s_kind,
                        source_id=s_id,
                        source_title=s_title,
                        source_url=s_url,
                        page_or_section=s_page,
                        passage=clean_pass,
                        quarantined_passage=quar_pass,
                        stance="supporting",
                        extracted_at=now,
                    )
                    _upsert_entity(
                        label=ent_dict["label"],
                        entity_type=ent_dict["entity_type"],
                        description=ent_dict["description"],
                        aliases=[],
                        properties={},
                        evidence_item=ev,
                        confidence=ent_dict["confidence"],
                    )

                for rel_dict in ext_relations:
                    clean_pass, quar_pass, inj_c = self.quarantine_passage(rel_dict["passage"], s_title)
                    prompt_inj_count += inj_c
                    ev = KGEvidenceItem(
                        evidence_id=f"kg_ev_{uuid.uuid4().hex[:8]}",
                        source_kind=s_kind,
                        source_id=s_id,
                        source_title=s_title,
                        source_url=s_url,
                        page_or_section=s_page,
                        passage=clean_pass,
                        quarantined_passage=quar_pass,
                        stance=rel_dict["stance"],
                        extracted_at=now,
                    )
                    src_id = _upsert_entity(
                        label=rel_dict["source_label"],
                        entity_type=rel_dict["source_type"],
                        description=f"Source entity in {rel_dict['relation_type']} relation.",
                        aliases=[],
                        properties={},
                        evidence_item=ev,
                        confidence=rel_dict["confidence"],
                    )
                    tgt_id = _upsert_entity(
                        label=rel_dict["target_label"],
                        entity_type=rel_dict["target_type"],
                        description=f"Target entity in {rel_dict['relation_type']} relation.",
                        aliases=[],
                        properties={},
                        evidence_item=ev,
                        confidence=rel_dict["confidence"],
                    )
                    if src_id != tgt_id:
                        _upsert_relationship(
                            src_ent_id=src_id,
                            tgt_ent_id=tgt_id,
                            rel_type=rel_dict["relation_type"],
                            fact_basis=rel_dict["fact_basis"],
                            is_inferred=rel_dict["is_inferred"],
                            uncertainty_label=rel_dict["uncertainty_label"],
                            confidence=rel_dict["confidence"],
                            explanation=rel_dict["explanation"],
                            evidence_item=ev,
                        )

            # Process explicit entities
            for exp_ent in req.explicit_entities:
                clean_pass, quar_pass, inj_c = self.quarantine_passage(
                    exp_ent.description or f"Explicit entity definition: {exp_ent.label}",
                    req.source_title,
                )
                prompt_inj_count += inj_c
                ev = KGEvidenceItem(
                    evidence_id=f"kg_ev_{uuid.uuid4().hex[:8]}",
                    source_kind="user_document",
                    source_id=f"src_exp_{uuid.uuid4().hex[:6]}",
                    source_title=req.source_title,
                    source_url=validated_source_url,
                    page_or_section=req.page_or_section,
                    passage=clean_pass,
                    quarantined_passage=quar_pass,
                    stance="supporting",
                    extracted_at=now,
                )
                _upsert_entity(
                    label=exp_ent.label,
                    entity_type=exp_ent.entity_type,
                    description=exp_ent.description or f"Verified {exp_ent.entity_type}: {exp_ent.label}",
                    aliases=exp_ent.aliases,
                    properties=exp_ent.properties,
                    evidence_item=ev,
                    confidence=0.95,
                )

            # Process explicit relationships
            for exp_rel in req.explicit_relationships:
                rel_url: Optional[str] = validated_source_url
                if exp_rel.source_url and exp_rel.source_url.strip():
                    if UniversalKnowledgeDiscoveryEngine.is_url_allowed(exp_rel.source_url.strip()):
                        rel_url = exp_rel.source_url.strip()
                    else:
                        ssrf_blocked_count += 1
                        rel_url = None

                raw_passage = exp_rel.passage or (
                    f"{exp_rel.source_label} {exp_rel.relation_type.replace('_', ' ')} {exp_rel.target_label}."
                )
                clean_pass, quar_pass, inj_c = self.quarantine_passage(
                    raw_passage,
                    exp_rel.source_title or req.source_title,
                )
                prompt_inj_count += inj_c

                is_inf = exp_rel.fact_basis == "ai_inferred"
                is_hedged = bool(HEDGING_PATTERNS.search(raw_passage))
                if is_inf:
                    unc_label: KGUncertaintyLabel = (
                        "inferred_low_confidence"
                        if (exp_rel.confidence is not None and exp_rel.confidence < 0.65)
                        else "inferred_transitive"
                    )
                    conf_val = exp_rel.confidence if exp_rel.confidence is not None else 0.72
                else:
                    unc_label = "hedged_source_statement" if is_hedged else "verified_explicit"
                    conf_val = exp_rel.confidence if exp_rel.confidence is not None else (0.65 if is_hedged else 0.94)

                stance_val: str = "contradicting" if exp_rel.relation_type == "contradicts" else "supporting"
                ev = KGEvidenceItem(
                    evidence_id=f"kg_ev_{uuid.uuid4().hex[:8]}",
                    source_kind="user_document",
                    source_id=f"src_rel_{uuid.uuid4().hex[:6]}",
                    source_title=exp_rel.source_title or req.source_title,
                    source_url=rel_url,
                    page_or_section=exp_rel.page_or_section or req.page_or_section,
                    passage=clean_pass,
                    quarantined_passage=quar_pass,
                    stance=stance_val,  # type: ignore[arg-type]
                    extracted_at=now,
                )
                src_id = _upsert_entity(
                    label=exp_rel.source_label,
                    entity_type=exp_rel.source_type,
                    description=f"Entity participating in {exp_rel.relation_type} relationship.",
                    aliases=[],
                    properties={},
                    evidence_item=ev,
                    confidence=conf_val,
                )
                tgt_id = _upsert_entity(
                    label=exp_rel.target_label,
                    entity_type=exp_rel.target_type,
                    description=f"Entity participating in {exp_rel.relation_type} relationship.",
                    aliases=[],
                    properties={},
                    evidence_item=ev,
                    confidence=conf_val,
                )
                if src_id != tgt_id:
                    _upsert_relationship(
                        src_ent_id=src_id,
                        tgt_ent_id=tgt_id,
                        rel_type=exp_rel.relation_type,
                        fact_basis=exp_rel.fact_basis,
                        is_inferred=is_inf,
                        uncertainty_label=unc_label,
                        confidence=conf_val,
                        explanation=(
                            f"AI-inferred relationship ({exp_rel.relation_type})"
                            if is_inf
                            else f"Explicitly stated in {exp_rel.source_title or req.source_title}"
                        ),
                        evidence_item=ev,
                    )

            # Derive transitive AI-inferred relationships (`depends_on` / `part_of`) if enabled
            if req.derive_inferred_relationships and settings.kg_enable_ai_inferred_edges:
                explicit_deps = conn.execute(
                    """
                    SELECT * FROM kg_relationships
                    WHERE user_id = ? AND workspace_id = ?
                      AND relation_type IN ('depends_on', 'part_of')
                      AND fact_basis = 'explicit_fact'
                    """,
                    (user_id, workspace_id),
                ).fetchall()

                _, label_map_tmp = self._compute_degrees_and_labels(conn, user_id, workspace_id)

                for e1 in explicit_deps:
                    for e2 in explicit_deps:
                        if (
                            e1["relation_type"] == e2["relation_type"]
                            and e1["target_entity_id"] == e2["source_entity_id"]
                            and e1["source_entity_id"] != e2["target_entity_id"]
                        ):
                            a_id = e1["source_entity_id"]
                            b_id = e1["target_entity_id"]
                            c_id = e2["target_entity_id"]
                            r_type = e1["relation_type"]

                            # Skip if an explicit edge A -> C already exists
                            already_explicit = conn.execute(
                                """
                                SELECT 1 FROM kg_relationships
                                WHERE user_id = ? AND workspace_id = ?
                                  AND source_entity_id = ? AND target_entity_id = ?
                                  AND relation_type = ? AND fact_basis = 'explicit_fact'
                                """,
                                (user_id, workspace_id, a_id, c_id, r_type),
                            ).fetchone()
                            if already_explicit:
                                continue

                            a_lbl = label_map_tmp.get(a_id, a_id)
                            b_lbl = label_map_tmp.get(b_id, b_id)
                            c_lbl = label_map_tmp.get(c_id, c_id)
                            inf_conf = round(min(float(e1["confidence"]), float(e2["confidence"])) * 0.78, 3)
                            inf_unc: KGUncertaintyLabel = (
                                "inferred_low_confidence" if inf_conf < 0.65 else "inferred_transitive"
                            )
                            inf_passage = (
                                f"Transitive inference: '{a_lbl}' {r_type.replace('_', ' ')} '{b_lbl}', "
                                f"and '{b_lbl}' {r_type.replace('_', ' ')} '{c_lbl}'."
                            )
                            _, quar_inf, _ = self.quarantine_passage(inf_passage, "Stage 22 Graph Reasoner")
                            inf_ev = KGEvidenceItem(
                                evidence_id=f"kg_ev_{uuid.uuid4().hex[:8]}",
                                source_kind="inferred_transitivity",
                                source_id=f"{e1['relationship_id']}+{e2['relationship_id']}",
                                source_title="Stage 22 Transitive Graph Reasoner",
                                source_url=None,
                                page_or_section="2-Hop Transitive Chain",
                                passage=inf_passage,
                                quarantined_passage=quar_inf,
                                stance="supporting",
                                extracted_at=now,
                            )
                            _upsert_relationship(
                                src_ent_id=a_id,
                                tgt_ent_id=c_id,
                                rel_type=r_type,
                                fact_basis="ai_inferred",
                                is_inferred=True,
                                uncertainty_label=inf_unc,
                                confidence=inf_conf,
                                explanation=(
                                    f"AI-inferred transitive {r_type.replace('_', ' ')} via intermediate node '{b_lbl}'."
                                ),
                                evidence_item=inf_ev,
                            )

            # Record change history
            change_id = f"kg_chg_{uuid.uuid4().hex[:10]}"
            summary_msg = (
                f"Ingested '{req.source_title}': +{entities_created} entities ({entities_updated} merged), "
                f"+{relationships_created} explicit relations ({relationships_updated} updated), "
                f"+{inferred_created} AI-inferred relations."
            )
            conn.execute(
                """
                INSERT INTO kg_change_history (
                    change_id, user_id, workspace_id, action_type, summary,
                    affected_entities_json, affected_relationships_json, snapshot_before_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change_id,
                    user_id,
                    workspace_id,
                    "ingest_merge",
                    summary_msg,
                    json.dumps(sorted(list(touched_entity_ids))),
                    json.dumps(sorted(list(touched_rel_ids))),
                    "{}",
                    now,
                ),
            )
            conn.commit()

            degree_map, label_map = self._compute_degrees_and_labels(conn, user_id, workspace_id)
            ent_rows = conn.execute(
                "SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ? ORDER BY updated_at DESC LIMIT 60",
                (user_id, workspace_id),
            ).fetchall()
            rel_rows = conn.execute(
                "SELECT * FROM kg_relationships WHERE user_id = ? AND workspace_id = ? ORDER BY updated_at DESC LIMIT 80",
                (user_id, workspace_id),
            ).fetchall()

            entities_out = [self._row_to_entity(r, degree_map) for r in ent_rows]
            rels_out = [self._row_to_relationship(r, label_map) for r in rel_rows]

        change_log = KGChangeLogEntry(
            change_id=change_id,
            user_id=user_id,
            workspace_id=workspace_id,
            action_type="ingest_merge",
            summary=summary_msg,
            affected_entity_ids=sorted(list(touched_entity_ids)),
            affected_relationship_ids=sorted(list(touched_rel_ids)),
            created_at=now,
        )

        return KGIngestResponse(
            user_id=user_id,
            workspace_id=workspace_id,
            entities_created=entities_created,
            entities_updated=entities_updated,
            relationships_created=relationships_created,
            relationships_updated=relationships_updated,
            inferred_relationships_created=inferred_created,
            prompt_injection_neutralized_count=prompt_inj_count,
            ssrf_blocked_urls_count=ssrf_blocked_count,
            entities=entities_out,
            relationships=rels_out,
            change_log=change_log,
            summary=summary_msg,
        )

    # ------------------------------------------------------------------
    # 5. Graph Snapshot & Filtering with Pagination
    # ------------------------------------------------------------------
    def get_graph_snapshot(
        self,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        search: Optional[str] = None,
        entity_type: Optional[str] = None,
        relation_type: Optional[str] = None,
        fact_basis: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> KGGraphSnapshotResponse:
        user_id = user_id.strip() or "default_user"
        workspace_id = workspace_id.strip() or "default_workspace"
        effective_page_size = min(max(1, page_size), settings.kg_max_page_size)

        with self._connect() as conn:
            degree_map, label_map = self._compute_degrees_and_labels(conn, user_id, workspace_id)

            total_nodes_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
                (user_id, workspace_id),
            ).fetchone()
            total_edges_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM kg_relationships WHERE user_id = ? AND workspace_id = ?",
                (user_id, workspace_id),
            ).fetchone()
            total_nodes_ws = int(total_nodes_row["cnt"]) if total_nodes_row else 0
            total_edges_ws = int(total_edges_row["cnt"]) if total_edges_row else 0

            clauses = ["user_id = ?", "workspace_id = ?"]
            params: List[Any] = [user_id, workspace_id]

            if entity_type and entity_type.strip():
                clauses.append("entity_type = ?")
                params.append(entity_type.strip())
            if search and search.strip():
                q = f"%{search.strip().lower()}%"
                clauses.append("(LOWER(label) LIKE ? OR LOWER(description) LIKE ? OR LOWER(aliases_json) LIKE ?)")
                params.extend([q, q, q])

            where_sql = " AND ".join(clauses)
            filtered_count_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM kg_entities WHERE {where_sql}",
                params,
            ).fetchone()
            filtered_total = int(filtered_count_row["cnt"]) if filtered_count_row else 0

            total_pages = max(1, math.ceil(filtered_total / effective_page_size))
            cur_page = min(max(1, page), total_pages)
            offset = (cur_page - 1) * effective_page_size

            ent_rows = conn.execute(
                f"SELECT * FROM kg_entities WHERE {where_sql} ORDER BY confidence DESC, label ASC LIMIT ? OFFSET ?",
                [*params, effective_page_size, offset],
            ).fetchall()
            nodes = [self._row_to_entity(r, degree_map) for r in ent_rows]
            node_ids = {n.entity_id for n in nodes}

            # Fetch edges connecting the returned nodes (or matching relation filters)
            rel_clauses = ["user_id = ?", "workspace_id = ?"]
            rel_params: List[Any] = [user_id, workspace_id]
            if relation_type and relation_type.strip():
                rel_clauses.append("relation_type = ?")
                rel_params.append(relation_type.strip())
            if fact_basis and fact_basis.strip():
                rel_clauses.append("fact_basis = ?")
                rel_params.append(fact_basis.strip())

            rel_rows = conn.execute(
                f"SELECT * FROM kg_relationships WHERE {' AND '.join(rel_clauses)} ORDER BY confidence DESC",
                rel_params,
            ).fetchall()

            edges: List[KGRelationshipEdge] = []
            for r in rel_rows:
                if r["source_entity_id"] in node_ids or r["target_entity_id"] in node_ids:
                    edges.append(self._row_to_relationship(r, label_map))
                    if len(edges) >= effective_page_size * 3:
                        break

            # Ensure any endpoint nodes referenced by returned edges are included so UI edges never dangle
            missing_node_ids = {
                eid
                for e in edges
                for eid in (e.source_entity_id, e.target_entity_id)
                if eid not in node_ids
            }
            if missing_node_ids:
                placeholders = ",".join("?" for _ in missing_node_ids)
                extra_rows = conn.execute(
                    f"SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ? AND entity_id IN ({placeholders})",
                    [user_id, workspace_id, *list(missing_node_ids)],
                ).fetchall()
                for er in extra_rows:
                    nodes.append(self._row_to_entity(er, degree_map))

        return KGGraphSnapshotResponse(
            user_id=user_id,
            workspace_id=workspace_id,
            total_nodes_in_workspace=total_nodes_ws,
            total_edges_in_workspace=total_edges_ws,
            returned_nodes_count=len(nodes),
            returned_edges_count=len(edges),
            page=cur_page,
            page_size=effective_page_size,
            total_pages=total_pages,
            has_more=cur_page < total_pages,
            nodes=nodes,
            edges=edges,
        )

    # ------------------------------------------------------------------
    # 6. Knowledge Queries (Paths, Dependencies, Contradictions, Neighborhood)
    # ------------------------------------------------------------------
    def _resolve_entity_by_query(
        self, conn: sqlite3.Connection, user_id: str, workspace_id: str, name_or_id: str
    ) -> Optional[sqlite3.Row]:
        if not name_or_id or not name_or_id.strip():
            return None
        q = name_or_id.strip()
        # 1. Exact entity_id
        row = conn.execute(
            "SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ? AND entity_id = ?",
            (user_id, workspace_id, q),
        ).fetchone()
        if row:
            return row
        # 2. Canonical key
        c_key = self.normalize_entity_key(q)
        row = conn.execute(
            "SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ? AND canonical_key = ?",
            (user_id, workspace_id, c_key),
        ).fetchone()
        if row:
            return row
        # 3. Case-insensitive label or alias substring
        like_q = f"%{q.lower()}%"
        row = conn.execute(
            """
            SELECT * FROM kg_entities
            WHERE user_id = ? AND workspace_id = ?
              AND (LOWER(label) LIKE ? OR LOWER(aliases_json) LIKE ?)
            ORDER BY LENGTH(label) ASC LIMIT 1
            """,
            (user_id, workspace_id, like_q, like_q),
        ).fetchone()
        return row

    def query_graph(self, req: KGQueryRequest) -> KGQueryResponse:
        start_ts = time.perf_counter()
        user_id = req.user_id.strip() or "default_user"
        workspace_id = req.workspace_id.strip() or "default_workspace"
        max_depth = min(max(1, req.max_depth), settings.kg_max_expansion_depth)

        mode = req.mode
        question = (req.question or "").strip()
        src_param = (req.source_entity or "").strip() or None
        tgt_param = (req.target_entity or "").strip() or None

        with self._connect() as conn:
            degree_map, label_map = self._compute_degrees_and_labels(conn, user_id, workspace_id)
            all_ent_rows = {
                r["entity_id"]: r
                for r in conn.execute(
                    "SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
                    (user_id, workspace_id),
                ).fetchall()
            }

            rel_sql = "SELECT * FROM kg_relationships WHERE user_id = ? AND workspace_id = ?"
            rel_args: List[Any] = [user_id, workspace_id]
            if not req.include_inferred:
                rel_sql += " AND is_inferred = 0"
            if req.relation_types:
                placeholders = ",".join("?" for _ in req.relation_types)
                rel_sql += f" AND relation_type IN ({placeholders})"
                rel_args.extend(req.relation_types)

            all_rel_rows = conn.execute(rel_sql, rel_args).fetchall()
            all_edges = [self._row_to_relationship(r, label_map) for r in all_rel_rows]

            # Auto-classify natural language questions if mode == 'natural_language'
            q_lower = question.lower()
            if mode == "natural_language":
                if any(w in q_lower for w in ("disagree", "contradict", "conflict", "dispute", "oppose")):
                    mode = "contradiction_analysis"
                elif any(w in q_lower for w in ("what depends on", "who depends on", "dependents of", "impact of", "relies on")):
                    mode = "dependency_impact"
                elif any(w in q_lower for w in ("connect", "path between", "linked", "relationship between", "how are")):
                    mode = "connection_path"
                else:
                    mode = "neighborhood_exploration"

                # Try to match entity names mentioned in the question if src_param / tgt_param not explicitly provided
                if not src_param or not tgt_param:
                    mentioned_ids: List[str] = []
                    # Sort entities by label length descending so longer specific names match first
                    sorted_ents = sorted(all_ent_rows.values(), key=lambda x: len(x["label"]), reverse=True)
                    for er in sorted_ents:
                        lbl_l = er["label"].lower()
                        if lbl_l in q_lower and er["entity_id"] not in mentioned_ids:
                            mentioned_ids.append(er["entity_id"])
                    if not src_param and len(mentioned_ids) >= 1:
                        src_param = mentioned_ids[0]
                    if not tgt_param and len(mentioned_ids) >= 2:
                        tgt_param = mentioned_ids[1]

            paths_out: List[List[KGPathStep]] = []
            dependents_out: List[KGEntityNode] = []
            contradictions_out: List[KGContradictionItem] = []
            sub_node_ids: Set[str] = set()
            sub_edges_map: Dict[str, KGRelationshipEdge] = {}
            cycles_detected = 0
            answer_summary = ""

            # --------------------------------------------------------------
            # Mode A: Connection Path ("How are these technologies connected?")
            # --------------------------------------------------------------
            if mode == "connection_path":
                src_row = self._resolve_entity_by_query(conn, user_id, workspace_id, src_param or "")
                tgt_row = self._resolve_entity_by_query(conn, user_id, workspace_id, tgt_param or "")
                if not src_row or not tgt_row:
                    answer_summary = (
                        "Could not resolve both source and target entities in this workspace graph. "
                        "Specify two existing entities to trace their connection path."
                    )
                elif src_row["entity_id"] == tgt_row["entity_id"]:
                    ent_node = self._row_to_entity(src_row, degree_map)
                    sub_node_ids.add(ent_node.entity_id)
                    answer_summary = f"Source and target refer to the same entity: '{ent_node.label}'."
                else:
                    s_id = src_row["entity_id"]
                    t_id = tgt_row["entity_id"]
                    # Build undirected adjacency list with directed edge metadata for path finding
                    adj: Dict[str, List[Tuple[str, KGRelationshipEdge]]] = {}
                    for edge in all_edges:
                        adj.setdefault(edge.source_entity_id, []).append((edge.target_entity_id, edge))
                        adj.setdefault(edge.target_entity_id, []).append((edge.source_entity_id, edge))

                    queue: deque[Tuple[str, List[KGPathStep], Set[str]]] = deque([(s_id, [], {s_id})])
                    found_paths: List[List[KGPathStep]] = []

                    while queue and len(found_paths) < 5:
                        curr_id, path_steps, visited_in_path = queue.popleft()
                        if len(path_steps) >= max_depth:
                            continue
                        for next_id, edge in adj.get(curr_id, []):
                            if next_id in visited_in_path:
                                cycles_detected += 1
                                continue
                            step = KGPathStep(
                                step_index=len(path_steps) + 1,
                                relationship_id=edge.relationship_id,
                                source_entity_id=edge.source_entity_id,
                                source_label=edge.source_label,
                                relation_type=edge.relation_type,
                                target_entity_id=edge.target_entity_id,
                                target_label=edge.target_label,
                                fact_basis=edge.fact_basis,
                                is_inferred=edge.is_inferred,
                                uncertainty_label=edge.uncertainty_label,
                                confidence=edge.confidence,
                                evidence=edge.evidence,
                            )
                            new_steps = path_steps + [step]
                            if next_id == t_id:
                                found_paths.append(new_steps)
                            else:
                                queue.append((next_id, new_steps, visited_in_path | {next_id}))

                    paths_out = found_paths
                    for p in found_paths:
                        for st in p:
                            sub_node_ids.add(st.source_entity_id)
                            sub_node_ids.add(st.target_entity_id)
                            matching_e = next((e for e in all_edges if e.relationship_id == st.relationship_id), None)
                            if matching_e:
                                sub_edges_map[matching_e.relationship_id] = matching_e

                    if found_paths:
                        shortest = found_paths[0]
                        chain_desc = " -> ".join(
                            f"{st.source_label} --[{st.relation_type} ({st.fact_basis})]--> {st.target_label}"
                            for st in shortest
                        )
                        answer_summary = (
                            f"Found {len(found_paths)} connection path(s) between '{src_row['label']}' and "
                            f"'{tgt_row['label']}' (shortest path: {len(shortest)} hop(s)): {chain_desc}."
                        )
                    else:
                        sub_node_ids.update({s_id, t_id})
                        answer_summary = (
                            f"No connection path found between '{src_row['label']}' and '{tgt_row['label']}' "
                            f"within max_depth={max_depth}."
                        )

            # --------------------------------------------------------------
            # Mode B: Dependency Impact ("What depends on this component?")
            # --------------------------------------------------------------
            elif mode == "dependency_impact":
                target_query = src_param or tgt_param or ""
                comp_row = self._resolve_entity_by_query(conn, user_id, workspace_id, target_query)
                if not comp_row:
                    answer_summary = (
                        f"Could not find component '{target_query}' in the workspace knowledge graph."
                    )
                else:
                    comp_id = comp_row["entity_id"]
                    sub_node_ids.add(comp_id)
                    # Reverse adjacency for `depends_on`, `part_of`, `uses` (who depends on comp_id?)
                    rev_adj: Dict[str, List[KGRelationshipEdge]] = {}
                    for edge in all_edges:
                        if edge.relation_type in ("depends_on", "part_of", "uses"):
                            rev_adj.setdefault(edge.target_entity_id, []).append(edge)

                    visited_deps: Set[str] = {comp_id}
                    q_dep: deque[Tuple[str, List[KGPathStep]]] = deque([(comp_id, [])])
                    dep_ids_ordered: List[str] = []

                    while q_dep:
                        curr_target, steps_so_far = q_dep.popleft()
                        if len(steps_so_far) >= max_depth:
                            continue
                        for edge in rev_adj.get(curr_target, []):
                            dependent_id = edge.source_entity_id
                            sub_edges_map[edge.relationship_id] = edge
                            sub_node_ids.add(dependent_id)
                            step = KGPathStep(
                                step_index=len(steps_so_far) + 1,
                                relationship_id=edge.relationship_id,
                                source_entity_id=edge.source_entity_id,
                                source_label=edge.source_label,
                                relation_type=edge.relation_type,
                                target_entity_id=edge.target_entity_id,
                                target_label=edge.target_label,
                                fact_basis=edge.fact_basis,
                                is_inferred=edge.is_inferred,
                                uncertainty_label=edge.uncertainty_label,
                                confidence=edge.confidence,
                                evidence=edge.evidence,
                            )
                            new_chain = steps_so_far + [step]
                            paths_out.append(new_chain)
                            if dependent_id in visited_deps:
                                cycles_detected += 1
                                continue
                            visited_deps.add(dependent_id)
                            dep_ids_ordered.append(dependent_id)
                            q_dep.append((dependent_id, new_chain))

                    for did in dep_ids_ordered:
                        if did in all_ent_rows:
                            dependents_out.append(self._row_to_entity(all_ent_rows[did], degree_map))

                    if dependents_out:
                        dep_names = ", ".join(d.label for d in dependents_out)
                        answer_summary = (
                            f"{len(dependents_out)} entity/component(s) depend on '{comp_row['label']}' "
                            f"(directly or transitively within {max_depth} hops): {dep_names}."
                        )
                    else:
                        answer_summary = (
                            f"No upstream dependents were found that depend on '{comp_row['label']}'."
                        )

            # --------------------------------------------------------------
            # Mode C: Contradiction Analysis ("Which sources disagree about this claim?")
            # --------------------------------------------------------------
            elif mode == "contradiction_analysis":
                filter_row = (
                    self._resolve_entity_by_query(conn, user_id, workspace_id, src_param or tgt_param or "")
                    if (src_param or tgt_param)
                    else None
                )
                filter_id = filter_row["entity_id"] if filter_row else None

                contradict_edges = [
                    e
                    for e in all_edges
                    if e.relation_type == "contradicts"
                    and (filter_id is None or e.source_entity_id == filter_id or e.target_entity_id == filter_id)
                ]
                support_edges = [
                    e
                    for e in all_edges
                    if e.relation_type == "supports"
                ]

                for ce in contradict_edges:
                    sub_node_ids.update({ce.source_entity_id, ce.target_entity_id})
                    sub_edges_map[ce.relationship_id] = ce
                    # Find any supporting edges targeting the same claim/target
                    matching_sup = next(
                        (
                            se
                            for se in support_edges
                            if se.target_entity_id == ce.target_entity_id
                            or se.source_entity_id == ce.target_entity_id
                        ),
                        None,
                    )
                    sup_sources: List[str] = []
                    if matching_sup:
                        sub_node_ids.update({matching_sup.source_entity_id, matching_sup.target_entity_id})
                        sub_edges_map[matching_sup.relationship_id] = matching_sup
                        sup_sources = [
                            f"{ev.source_title} ({ev.page_or_section or 'verified passage'})"
                            for ev in matching_sup.evidence
                        ]
                    contra_sources = [
                        f"{ev.source_title} ({ev.page_or_section or 'verified passage'})"
                        for ev in ce.evidence
                    ]
                    contradictions_out.append(
                        KGContradictionItem(
                            subject_label=ce.source_label,
                            target_label=ce.target_label,
                            supporting_edge=matching_sup,
                            contradicting_edge=ce,
                            supporting_sources=sup_sources,
                            contradicting_sources=contra_sources,
                            explanation=(
                                f"'{ce.source_label}' contradicts '{ce.target_label}' "
                                f"(cited in {', '.join(contra_sources) or 'source'})"
                                + (
                                    f", whereas '{matching_sup.source_label}' supports '{matching_sup.target_label}' "
                                    f"(cited in {', '.join(sup_sources)})."
                                    if matching_sup
                                    else "."
                                )
                            ),
                        )
                    )

                if contradictions_out:
                    answer_summary = (
                        f"Detected {len(contradictions_out)} contested claim(s)/contradiction(s): "
                        + " ".join(c.explanation for c in contradictions_out[:3])
                    )
                else:
                    answer_summary = "No contradicting relationships or source disagreements were found for the specified scope."

            # --------------------------------------------------------------
            # Mode D: Neighborhood Exploration (Bounded k-hop Ego Network)
            # --------------------------------------------------------------
            else:
                center_row = (
                    self._resolve_entity_by_query(conn, user_id, workspace_id, src_param or question)
                    if (src_param or question)
                    else None
                )
                if not center_row and all_ent_rows:
                    center_row = next(iter(all_ent_rows.values()))

                if not center_row:
                    answer_summary = "The workspace knowledge graph is currently empty."
                else:
                    c_id = center_row["entity_id"]
                    sub_node_ids.add(c_id)
                    visited_hops: Set[str] = {c_id}
                    frontier: Set[str] = {c_id}

                    for _hop in range(min(max_depth, 3)):
                        next_frontier: Set[str] = set()
                        for edge in all_edges:
                            if edge.source_entity_id in frontier or edge.target_entity_id in frontier:
                                sub_edges_map[edge.relationship_id] = edge
                                for endpoint in (edge.source_entity_id, edge.target_entity_id):
                                    sub_node_ids.add(endpoint)
                                    if endpoint not in visited_hops:
                                        visited_hops.add(endpoint)
                                        next_frontier.add(endpoint)
                                    elif endpoint != c_id:
                                        cycles_detected += 1
                        frontier = next_frontier
                        if not frontier:
                            break

                    answer_summary = (
                        f"Expanded neighborhood around '{center_row['label']}': "
                        f"{len(sub_node_ids)} connected entities and {len(sub_edges_map)} relationships."
                    )

            sub_nodes = [
                self._row_to_entity(all_ent_rows[nid], degree_map)
                for nid in sub_node_ids
                if nid in all_ent_rows
            ]
            sub_edges = list(sub_edges_map.values())
            explicit_cnt = sum(1 for e in sub_edges if not e.is_inferred)
            inferred_cnt = sum(1 for e in sub_edges if e.is_inferred)

        elapsed_ms = round((time.perf_counter() - start_ts) * 1000, 2)
        return KGQueryResponse(
            query_id=f"kg_qry_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            workspace_id=workspace_id,
            mode_executed=mode,
            question=question or f"{mode} ({src_param or ''} -> {tgt_param or ''})",
            answer_summary=answer_summary,
            paths=paths_out,
            dependent_entities=dependents_out,
            contradictions=contradictions_out,
            subgraph_nodes=sub_nodes,
            subgraph_edges=sub_edges,
            cycles_detected=cycles_detected,
            explicit_facts_count=explicit_cnt,
            inferred_facts_count=inferred_cnt,
            latency_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # 7. Duplicate Entity Detection & Approval-Gated Merges / Deletions
    # ------------------------------------------------------------------
    def find_duplicate_candidates(
        self,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> List[KGDuplicateCandidate]:
        user_id = user_id.strip() or "default_user"
        workspace_id = workspace_id.strip() or "default_workspace"

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM kg_entities WHERE user_id = ? AND workspace_id = ? ORDER BY label ASC",
                (user_id, workspace_id),
            ).fetchall()

        candidates: List[KGDuplicateCandidate] = []
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a = rows[i]
                b = rows[j]
                key_a = a["canonical_key"]
                key_b = b["canonical_key"]
                tok_a = set(key_a.split("_"))
                tok_b = set(key_b.split("_"))
                shared = tok_a & tok_b
                union = tok_a | tok_b
                jaccard = len(shared) / len(union) if union else 0.0

                # Check prefix/substring containment (e.g., "fastapi" vs "fastapi_framework")
                is_prefix_match = (
                    (key_a.startswith(key_b) or key_b.startswith(key_a))
                    and min(len(key_a), len(key_b)) >= 4
                )

                if jaccard >= 0.5 or is_prefix_match:
                    score = round(max(jaccard, 0.82 if is_prefix_match else jaccard), 2)
                    candidates.append(
                        KGDuplicateCandidate(
                            candidate_id=f"dup_{a['entity_id'][-4:]}_{b['entity_id'][-4:]}",
                            entity_a_id=a["entity_id"],
                            entity_a_label=a["label"],
                            entity_b_id=b["entity_id"],
                            entity_b_label=b["label"],
                            entity_type=a["entity_type"],
                            similarity_score=score,
                            reason=(
                                f"Overlapping canonical tokens ({', '.join(sorted(shared)) or 'prefix match'}) "
                                "suggest these nodes may represent the same entity."
                            ),
                        )
                    )
        return candidates

    def merge_entities(self, req: KGEntityMergeRequest) -> KGDestructiveOperationRecord:
        """
        Merges `source_entity_id` into `target_entity_id`.
        Because merging destructively removes `source_entity_id` and rewrites graph topology,
        it requires `confirmed=True` or explicit approval via `/operations/{op_id}/approve`.
        """
        now = _utc_now_iso()
        user_id = req.user_id.strip() or "default_user"
        workspace_id = req.workspace_id.strip() or "default_workspace"

        if req.source_entity_id == req.target_entity_id:
            raise ValueError("Cannot merge an entity with itself.")

        with self._connect() as conn:
            src_row = conn.execute(
                "SELECT * FROM kg_entities WHERE entity_id = ? AND user_id = ? AND workspace_id = ?",
                (req.source_entity_id, user_id, workspace_id),
            ).fetchone()
            tgt_row = conn.execute(
                "SELECT * FROM kg_entities WHERE entity_id = ? AND user_id = ? AND workspace_id = ?",
                (req.target_entity_id, user_id, workspace_id),
            ).fetchone()

            if not src_row or not tgt_row:
                raise PermissionError(
                    "Source or target entity not found in the authorized user workspace."
                )

            rel_cnt_row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM kg_relationships
                WHERE user_id = ? AND workspace_id = ?
                  AND (source_entity_id = ? OR target_entity_id = ?)
                """,
                (user_id, workspace_id, req.source_entity_id, req.source_entity_id),
            ).fetchone()
            affected_rels = int(rel_cnt_row["cnt"]) if rel_cnt_row else 0

            op_id = f"kg_op_{uuid.uuid4().hex[:10]}"
            summary = (
                f"Merge entity '{src_row['label']}' ({req.source_entity_id}) into "
                f"'{tgt_row['label']}' ({req.target_entity_id}), preserving aliases and provenance."
            )
            payload = {
                "source_entity_id": req.source_entity_id,
                "target_entity_id": req.target_entity_id,
            }

            if not req.confirmed:
                conn.execute(
                    """
                    INSERT INTO kg_pending_destructive_ops (
                        op_id, user_id, workspace_id, operation_type, status, summary,
                        payload_json, affected_entities_count, affected_relationships_count,
                        created_at, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        op_id,
                        user_id,
                        workspace_id,
                        "merge_entities",
                        "WAITING_FOR_APPROVAL",
                        summary,
                        json.dumps(payload),
                        2,
                        affected_rels,
                        now,
                        None,
                    ),
                )
                conn.commit()
                return KGDestructiveOperationRecord(
                    op_id=op_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    operation_type="merge_entities",
                    status="WAITING_FOR_APPROVAL",
                    requires_approval=True,
                    summary=summary,
                    affected_entities_count=2,
                    affected_relationships_count=affected_rels,
                    created_at=now,
                    resolved_at=None,
                )

            return self._execute_entity_merge(
                conn=conn,
                op_id=op_id,
                user_id=user_id,
                workspace_id=workspace_id,
                src_row=src_row,
                tgt_row=tgt_row,
                affected_rels=affected_rels,
                now=now,
            )

    def _execute_entity_merge(
        self,
        conn: sqlite3.Connection,
        op_id: str,
        user_id: str,
        workspace_id: str,
        src_row: sqlite3.Row,
        tgt_row: sqlite3.Row,
        affected_rels: int,
        now: str,
    ) -> KGDestructiveOperationRecord:
        src_id = src_row["entity_id"]
        tgt_id = tgt_row["entity_id"]

        # Snapshot before merge
        snapshot_before = {
            "source_entity": dict(src_row),
            "target_entity": dict(tgt_row),
        }

        # Merge aliases & provenance into target
        tgt_aliases: List[str] = json.loads(tgt_row["aliases_json"] or "[]")
        src_aliases: List[str] = json.loads(src_row["aliases_json"] or "[]")
        for candidate_al in [src_row["label"], *src_aliases]:
            if candidate_al and candidate_al != tgt_row["label"] and candidate_al not in tgt_aliases:
                tgt_aliases.append(candidate_al)

        tgt_prov: List[Dict[str, Any]] = json.loads(tgt_row["provenance_json"] or "[]")
        src_prov: List[Dict[str, Any]] = json.loads(src_row["provenance_json"] or "[]")
        for p in src_prov:
            if p not in tgt_prov:
                tgt_prov.append(p)

        tgt_props: Dict[str, Any] = json.loads(tgt_row["properties_json"] or "{}")
        src_props: Dict[str, Any] = json.loads(src_row["properties_json"] or "{}")
        merged_props = {**src_props, **tgt_props}

        conn.execute(
            """
            UPDATE kg_entities
            SET aliases_json = ?, provenance_json = ?, properties_json = ?, updated_at = ?
            WHERE entity_id = ?
            """,
            (
                json.dumps(tgt_aliases),
                json.dumps(tgt_prov),
                json.dumps(merged_props),
                now,
                tgt_id,
            ),
        )

        # Re-point relationships from src_id to tgt_id
        rels_to_move = conn.execute(
            """
            SELECT * FROM kg_relationships
            WHERE user_id = ? AND workspace_id = ?
              AND (source_entity_id = ? OR target_entity_id = ?)
            """,
            (user_id, workspace_id, src_id, src_id),
        ).fetchall()

        for r in rels_to_move:
            new_src = tgt_id if r["source_entity_id"] == src_id else r["source_entity_id"]
            new_tgt = tgt_id if r["target_entity_id"] == src_id else r["target_entity_id"]
            if new_src == new_tgt:
                # Remove self-loop created by merge
                conn.execute("DELETE FROM kg_relationships WHERE relationship_id = ?", (r["relationship_id"],))
                continue

            conflict = conn.execute(
                """
                SELECT * FROM kg_relationships
                WHERE user_id = ? AND workspace_id = ?
                  AND source_entity_id = ? AND target_entity_id = ?
                  AND relation_type = ? AND fact_basis = ?
                  AND relationship_id != ?
                """,
                (user_id, workspace_id, new_src, new_tgt, r["relation_type"], r["fact_basis"], r["relationship_id"]),
            ).fetchone()
            if conflict:
                # Merge evidence into existing relationship and delete duplicate edge
                c_ev = json.loads(conflict["evidence_json"] or "[]")
                for ev_item in json.loads(r["evidence_json"] or "[]"):
                    if ev_item not in c_ev:
                        c_ev.append(ev_item)
                conn.execute(
                    "UPDATE kg_relationships SET evidence_json = ?, updated_at = ? WHERE relationship_id = ?",
                    (json.dumps(c_ev), now, conflict["relationship_id"]),
                )
                conn.execute("DELETE FROM kg_relationships WHERE relationship_id = ?", (r["relationship_id"],))
            else:
                conn.execute(
                    "UPDATE kg_relationships SET source_entity_id = ?, target_entity_id = ?, updated_at = ? WHERE relationship_id = ?",
                    (new_src, new_tgt, now, r["relationship_id"]),
                )

        conn.execute("DELETE FROM kg_entities WHERE entity_id = ?", (src_id,))

        summary = (
            f"Merged entity '{src_row['label']}' ({src_id}) into '{tgt_row['label']}' ({tgt_id}) "
            f"with full alias and source provenance preservation."
        )
        conn.execute(
            """
            INSERT INTO kg_change_history (
                change_id, user_id, workspace_id, action_type, summary,
                affected_entities_json, affected_relationships_json, snapshot_before_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"kg_chg_{uuid.uuid4().hex[:10]}",
                user_id,
                workspace_id,
                "entity_merge_approved",
                summary,
                json.dumps([src_id, tgt_id]),
                json.dumps([r["relationship_id"] for r in rels_to_move]),
                json.dumps(snapshot_before),
                now,
            ),
        )
        conn.commit()

        return KGDestructiveOperationRecord(
            op_id=op_id,
            user_id=user_id,
            workspace_id=workspace_id,
            operation_type="merge_entities",
            status="SUCCEEDED",
            requires_approval=True,
            summary=summary,
            affected_entities_count=2,
            affected_relationships_count=affected_rels,
            created_at=now,
            resolved_at=now,
        )

    def delete_items(self, req: KGDeleteRequest) -> KGDestructiveOperationRecord:
        """
        Deletes specified entities/relationships or clears the workspace graph.
        Requires explicit confirmation (`confirmed=True` or approval of pending operation).
        """
        now = _utc_now_iso()
        user_id = req.user_id.strip() or "default_user"
        workspace_id = req.workspace_id.strip() or "default_workspace"

        op_type: str = "clear_workspace" if req.clear_workspace else "delete_items"
        op_id = f"kg_op_{uuid.uuid4().hex[:10]}"

        with self._connect() as conn:
            if req.clear_workspace:
                e_cnt = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
                    (user_id, workspace_id),
                ).fetchone()["cnt"]
                r_cnt = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM kg_relationships WHERE user_id = ? AND workspace_id = ?",
                    (user_id, workspace_id),
                ).fetchone()["cnt"]
            else:
                e_cnt = len(req.entity_ids)
                r_cnt = len(req.relationship_ids)

            summary = (
                f"Clear all {e_cnt} entities and {r_cnt} relationships in workspace '{workspace_id}'."
                if req.clear_workspace
                else f"Delete {e_cnt} entity(s) and {r_cnt} relationship(s) from workspace '{workspace_id}'."
            )
            payload = {
                "entity_ids": req.entity_ids,
                "relationship_ids": req.relationship_ids,
                "clear_workspace": req.clear_workspace,
            }

            if not req.confirmed:
                conn.execute(
                    """
                    INSERT INTO kg_pending_destructive_ops (
                        op_id, user_id, workspace_id, operation_type, status, summary,
                        payload_json, affected_entities_count, affected_relationships_count,
                        created_at, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        op_id,
                        user_id,
                        workspace_id,
                        op_type,
                        "WAITING_FOR_APPROVAL",
                        summary,
                        json.dumps(payload),
                        int(e_cnt),
                        int(r_cnt),
                        now,
                        None,
                    ),
                )
                conn.commit()
                return KGDestructiveOperationRecord(
                    op_id=op_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    operation_type=op_type,  # type: ignore[arg-type]
                    status="WAITING_FOR_APPROVAL",
                    requires_approval=True,
                    summary=summary,
                    affected_entities_count=int(e_cnt),
                    affected_relationships_count=int(r_cnt),
                    created_at=now,
                    resolved_at=None,
                )

            return self._execute_delete(
                conn=conn,
                op_id=op_id,
                user_id=user_id,
                workspace_id=workspace_id,
                entity_ids=req.entity_ids,
                relationship_ids=req.relationship_ids,
                clear_workspace=req.clear_workspace,
                now=now,
            )

    def _execute_delete(
        self,
        conn: sqlite3.Connection,
        op_id: str,
        user_id: str,
        workspace_id: str,
        entity_ids: List[str],
        relationship_ids: List[str],
        clear_workspace: bool,
        now: str,
    ) -> KGDestructiveOperationRecord:
        if clear_workspace:
            conn.execute(
                "DELETE FROM kg_relationships WHERE user_id = ? AND workspace_id = ?",
                (user_id, workspace_id),
            )
            conn.execute(
                "DELETE FROM kg_entities WHERE user_id = ? AND workspace_id = ?",
                (user_id, workspace_id),
            )
            summary = f"Cleared workspace '{workspace_id}' after explicit user approval."
            op_type: str = "clear_workspace"
        else:
            op_type = "delete_items"
            for rid in relationship_ids:
                conn.execute(
                    "DELETE FROM kg_relationships WHERE relationship_id = ? AND user_id = ? AND workspace_id = ?",
                    (rid, user_id, workspace_id),
                )
            for eid in entity_ids:
                conn.execute(
                    """
                    DELETE FROM kg_relationships
                    WHERE user_id = ? AND workspace_id = ?
                      AND (source_entity_id = ? OR target_entity_id = ?)
                    """,
                    (user_id, workspace_id, eid, eid),
                )
                conn.execute(
                    "DELETE FROM kg_entities WHERE entity_id = ? AND user_id = ? AND workspace_id = ?",
                    (eid, user_id, workspace_id),
                )
            summary = (
                f"Deleted {len(entity_ids)} entity(s) and {len(relationship_ids)} relationship(s) "
                f"from workspace '{workspace_id}' after explicit user approval."
            )

        conn.execute(
            """
            INSERT INTO kg_change_history (
                change_id, user_id, workspace_id, action_type, summary,
                affected_entities_json, affected_relationships_json, snapshot_before_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"kg_chg_{uuid.uuid4().hex[:10]}",
                user_id,
                workspace_id,
                "delete_approved",
                summary,
                json.dumps(entity_ids),
                json.dumps(relationship_ids),
                "{}",
                now,
            ),
        )
        conn.commit()
        return KGDestructiveOperationRecord(
            op_id=op_id,
            user_id=user_id,
            workspace_id=workspace_id,
            operation_type=op_type,  # type: ignore[arg-type]
            status="SUCCEEDED",
            requires_approval=True,
            summary=summary,
            affected_entities_count=len(entity_ids),
            affected_relationships_count=len(relationship_ids),
            created_at=now,
            resolved_at=now,
        )

    def approve_operation(self, op_id: str, req: KGApproveOperationRequest) -> KGDestructiveOperationRecord:
        now = _utc_now_iso()
        user_id = req.user_id.strip() or "default_user"
        workspace_id = req.workspace_id.strip() or "default_workspace"

        with self._connect() as conn:
            op_row = conn.execute(
                "SELECT * FROM kg_pending_destructive_ops WHERE op_id = ? AND user_id = ? AND workspace_id = ?",
                (op_id, user_id, workspace_id),
            ).fetchone()
            if not op_row:
                raise PermissionError(f"Operation '{op_id}' not found in the authorized workspace.")

            if op_row["status"] != "WAITING_FOR_APPROVAL":
                return KGDestructiveOperationRecord(
                    op_id=op_row["op_id"],
                    user_id=op_row["user_id"],
                    workspace_id=op_row["workspace_id"],
                    operation_type=op_row["operation_type"],
                    status=op_row["status"],
                    requires_approval=True,
                    summary=op_row["summary"],
                    affected_entities_count=int(op_row["affected_entities_count"]),
                    affected_relationships_count=int(op_row["affected_relationships_count"]),
                    created_at=op_row["created_at"],
                    resolved_at=op_row["resolved_at"],
                )

            if not req.approved:
                conn.execute(
                    "UPDATE kg_pending_destructive_ops SET status = 'CANCELLED', resolved_at = ? WHERE op_id = ?",
                    (now, op_id),
                )
                conn.commit()
                return KGDestructiveOperationRecord(
                    op_id=op_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    operation_type=op_row["operation_type"],
                    status="CANCELLED",
                    requires_approval=True,
                    summary=f"Cancelled destructive operation: {op_row['summary']}",
                    affected_entities_count=int(op_row["affected_entities_count"]),
                    affected_relationships_count=int(op_row["affected_relationships_count"]),
                    created_at=op_row["created_at"],
                    resolved_at=now,
                )

            payload = json.loads(op_row["payload_json"] or "{}")
            if op_row["operation_type"] == "merge_entities":
                src_row = conn.execute(
                    "SELECT * FROM kg_entities WHERE entity_id = ? AND user_id = ? AND workspace_id = ?",
                    (payload["source_entity_id"], user_id, workspace_id),
                ).fetchone()
                tgt_row = conn.execute(
                    "SELECT * FROM kg_entities WHERE entity_id = ? AND user_id = ? AND workspace_id = ?",
                    (payload["target_entity_id"], user_id, workspace_id),
                ).fetchone()
                if not src_row or not tgt_row:
                    raise ValueError("Source or target entity for merge no longer exists.")
                res = self._execute_entity_merge(
                    conn=conn,
                    op_id=op_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    src_row=src_row,
                    tgt_row=tgt_row,
                    affected_rels=int(op_row["affected_relationships_count"]),
                    now=now,
                )
            else:
                res = self._execute_delete(
                    conn=conn,
                    op_id=op_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    entity_ids=payload.get("entity_ids", []),
                    relationship_ids=payload.get("relationship_ids", []),
                    clear_workspace=bool(payload.get("clear_workspace", False)),
                    now=now,
                )

            conn.execute(
                "UPDATE kg_pending_destructive_ops SET status = 'SUCCEEDED', resolved_at = ? WHERE op_id = ?",
                (now, op_id),
            )
            conn.commit()
            return res

    def list_pending_operations(
        self,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> List[KGDestructiveOperationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM kg_pending_destructive_ops
                WHERE user_id = ? AND workspace_id = ?
                ORDER BY created_at DESC LIMIT 25
                """,
                (user_id.strip() or "default_user", workspace_id.strip() or "default_workspace"),
            ).fetchall()
        return [
            KGDestructiveOperationRecord(
                op_id=r["op_id"],
                user_id=r["user_id"],
                workspace_id=r["workspace_id"],
                operation_type=r["operation_type"],
                status=r["status"],
                requires_approval=True,
                summary=r["summary"],
                affected_entities_count=int(r["affected_entities_count"]),
                affected_relationships_count=int(r["affected_relationships_count"]),
                created_at=r["created_at"],
                resolved_at=r["resolved_at"],
            )
            for r in rows
        ]

    def list_change_history(
        self,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        limit: int = 25,
    ) -> List[KGChangeLogEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM kg_change_history
                WHERE user_id = ? AND workspace_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id.strip() or "default_user", workspace_id.strip() or "default_workspace", limit),
            ).fetchall()
        return [
            KGChangeLogEntry(
                change_id=r["change_id"],
                user_id=r["user_id"],
                workspace_id=r["workspace_id"],
                action_type=r["action_type"],
                summary=r["summary"],
                affected_entity_ids=json.loads(r["affected_entities_json"] or "[]"),
                affected_relationship_ids=json.loads(r["affected_relationships_json"] or "[]"),
                created_at=r["created_at"],
            )
            for r in rows
        ]


knowledge_graph_engine = KnowledgeGraphIntelligenceEngine()
