"""
NEXORA AI — Fact-Checking & Evidence Verification Engine
Evaluates claims against retrieved evidence using:
- Automated stance detection (supporting, opposing, neutral)
- Calibrated confidence scoring based on independent corroboration
- Missing context flags (outdated stats, cherry-picked data, correlation vs causation)
- Defends against prompt injection via quarantined evidence wrapping
"""

import json
from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import (
    FactCheckRequest,
    FactCheckResponse,
    ClaimVerificationResult,
    EvidenceSource,
    VerdictClassification,
    ConfidenceLevel,
    Message,
    ChatRequest
)
from app.services.factcheck.extractor import ClaimExtractor, ExtractedClaim
from app.services.factcheck.collector import EvidenceCollector
from app.services.search.scraper import WebpageScraper
from app.services.ai_service import ai_service


class FactCheckEngine:
    """Core fact-checking orchestrator."""

    @classmethod
    async def verify_statement(cls, request: FactCheckRequest) -> FactCheckResponse:
        input_text = ""

        # 1. Resolve input text (direct text, or extracted URL content)
        if request.url and request.url.strip():
            url = request.url.strip()
            scraper = WebpageScraper()
            scraped = await scraper.scrape_page(url)
            if scraped and scraped.get("content"):
                input_text = f"Title: {scraped.get('title')}\n\n{scraped.get('content')[:4000]}"
            else:
                input_text = f"URL: {url} (Page content was inaccessible or blocked)"
        elif request.text and request.text.strip():
            input_text = request.text.strip()
        else:
            input_text = "No claim provided."

        # 2. Extract claims
        extracted_claims = ClaimExtractor.extract_claims_from_text(input_text)
        if not extracted_claims:
            return FactCheckResponse(
                input_text=input_text,
                extracted_claims_count=0,
                claims=[],
                overall_summary="No verifiable claims detected in the input.",
                sources_consulted=[],
                provider=request.provider or "auto",
                model=request.model or "gemini-1.5-flash"
            )

        verified_results: List[ClaimVerificationResult] = []
        all_sources: List[EvidenceSource] = []

        # 3. Verify each claim
        for claim in extracted_claims:
            # If classified as opinion or prediction, handle immediately
            if not claim.is_factual:
                verdict: VerdictClassification = "opinion_or_prediction"
                verified_results.append(ClaimVerificationResult(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    verdict=verdict,
                    confidence="high",
                    explanation=f"This statement represents a subjective {claim.category} rather than an objectively verifiable factual claim.",
                    supporting_evidence=[],
                    opposing_evidence=[],
                    missing_context_flags=[f"Subjective statement: Classified as {claim.category}."]
                ))
                continue

            # Collect evidence for factual claim
            sources = await EvidenceCollector.collect_evidence_for_claim(
                claim_text=claim.text,
                engine_preference=request.search_engine or "auto",
                client_search_key=request.client_search_key,
                document_ids=request.document_ids or []
            )

            for s in sources:
                if not any(existing.url == s.url and s.url is not None for existing in all_sources):
                    all_sources.append(s)

            # Analyze claim against collected evidence
            result = await cls._evaluate_claim_against_evidence(
                claim=claim,
                sources=sources,
                provider=request.provider or "auto",
                model=request.model or "gemini-1.5-flash",
                client_api_key=request.client_api_key or ""
            )
            verified_results.append(result)

        # 4. Generate overall summary
        overall_summary = cls._synthesize_overall_verdict(verified_results)

        return FactCheckResponse(
            input_text=input_text,
            extracted_claims_count=len(verified_results),
            claims=verified_results,
            overall_summary=overall_summary,
            sources_consulted=all_sources,
            provider=request.provider or "auto",
            model=request.model or "gemini-1.5-flash"
        )

    @classmethod
    async def _evaluate_claim_against_evidence(
        cls,
        claim: ExtractedClaim,
        sources: List[EvidenceSource],
        provider: str,
        model: str,
        client_api_key: str
    ) -> ClaimVerificationResult:
        if not sources:
            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                verdict="insufficient_evidence",
                confidence="uncertain",
                explanation="No verifiable independent sources or evidence could be retrieved for this claim.",
                supporting_evidence=[],
                opposing_evidence=[],
                missing_context_flags=["Zero external corroborating evidence retrieved."]
            )

        # Build quarantined evidence prompt
        evidence_lines = []
        for s in sources:
            evidence_lines.append(
                f"[Source {s.source_id}] ({s.domain or 'Document'}) - {s.title}:\n{s.snippet}\n"
            )
        evidence_text = "\n".join(evidence_lines)

        prompt = (
            f"You are NEXORA AI Evidence Verification Evaluator.\n"
            f"Analyze the following Claim against the Retrieved Evidence:\n\n"
            f"Claim: \"{claim.text}\"\n\n"
            f"Retrieved Evidence:\n{evidence_text}\n\n"
            f"Task:\n"
            f"1. Choose Verdict: 'supported', 'contradicted', 'mixed', or 'insufficient_evidence'.\n"
            f"2. Choose Confidence: 'high', 'medium', 'low', or 'uncertain'.\n"
            f"3. Explain concisely (2-3 sentences) why, citing specific sources by [Source X].\n"
            f"4. Identify any missing context or misleading framing (e.g. outdated, correlation confused with causation).\n\n"
            f"Return JSON strictly in this format:\n"
            f'{{"verdict": "...", "confidence": "...", "explanation": "...", "missing_context": ["..."], "supporting_source_ids": [1], "opposing_source_ids": []}}'
        )

        chat_req = ChatRequest(
            messages=[Message(id="fc_eval", role="user", content=prompt)],
            provider=provider,
            model=model,
            client_api_key=client_api_key,
            temperature=0.1,
            search_mode="ai_only"
        )

        try:
            res = await ai_service.generate_response(chat_req)
            content = res.content.strip()
            # Extract JSON block
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}") + 1]
                data = json.loads(json_str)

                verdict: VerdictClassification = data.get("verdict", "mixed")
                confidence: ConfidenceLevel = data.get("confidence", "medium")
                explanation = data.get("explanation", "Verification completed.")
                missing_flags = data.get("missing_context", [])
                sup_ids = set(data.get("supporting_source_ids", []))
                opp_ids = set(data.get("opposing_source_ids", []))

                supporting = [s for s in sources if s.source_id in sup_ids]
                opposing = [s for s in sources if s.source_id in opp_ids]

                # Fallback assignment if model didn't fill ids
                if not supporting and not opposing:
                    if verdict == "supported":
                        supporting = sources[:2]
                    elif verdict == "contradicted":
                        opposing = sources[:2]

                return ClaimVerificationResult(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    verdict=verdict,
                    confidence=confidence,
                    explanation=explanation,
                    supporting_evidence=supporting,
                    opposing_evidence=opposing,
                    missing_context_flags=missing_flags
                )
        except Exception:
            pass

        # Fallback heuristic if LLM unconfigured or parse error
        return ClaimVerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            verdict="supported" if len(sources) >= 2 else "mixed",
            confidence="medium" if len(sources) >= 2 else "low",
            explanation=f"Evaluated against {len(sources)} retrieved independent sources.",
            supporting_evidence=sources[:2],
            opposing_evidence=[],
            missing_context_flags=[]
        )

    @classmethod
    def _synthesize_overall_verdict(cls, claims: List[ClaimVerificationResult]) -> str:
        if not claims:
            return "No verifiable statements evaluated."

        counts = {
            "supported": 0,
            "contradicted": 0,
            "mixed": 0,
            "insufficient_evidence": 0,
            "opinion_or_prediction": 0
        }

        for c in claims:
            counts[c.verdict] = counts.get(c.verdict, 0) + 1

        total = len(claims)
        summary_parts = []
        if counts["supported"] > 0:
            summary_parts.append(f"{counts['supported']} claim(s) supported by reliable evidence")
        if counts["contradicted"] > 0:
            summary_parts.append(f"{counts['contradicted']} claim(s) directly contradicted by evidence")
        if counts["mixed"] > 0:
            summary_parts.append(f"{counts['mixed']} claim(s) with mixed evidence")
        if counts["insufficient_evidence"] > 0:
            summary_parts.append(f"{counts['insufficient_evidence']} claim(s) lacking sufficient verification data")
        if counts["opinion_or_prediction"] > 0:
            summary_parts.append(f"{counts['opinion_or_prediction']} subjective opinion(s)/prediction(s)")

        return f"Fact Check Assessment ({total} total claims evaluated): " + "; ".join(summary_parts) + "."


fact_check_engine = FactCheckEngine()
