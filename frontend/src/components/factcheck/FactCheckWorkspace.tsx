import React, { useState } from 'react';
import { useChat } from '../../context/ChatContext';
import { api } from '../../services/api';
import { FactCheckResponse, ClaimVerificationResult, EvidenceSource, VerdictClassification } from '../../types';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ExternalLink,
  Copy,
  Check,
  Search,
  Sparkles,
  Loader2,
  Globe,
  FileText,
  Scale
} from 'lucide-react';

export const FactCheckWorkspace: React.FC = () => {
  const { settings, showToast, selectedDocumentIds } = useChat();

  const [inputMode, setInputMode] = useState<'text' | 'url'>('text');
  const [claimText, setClaimText] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [result, setResult] = useState<FactCheckResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const handleVerify = async () => {
    if (inputMode === 'text' && !claimText.trim()) {
      showToast('Please enter text or statements to fact-check.', 'error');
      return;
    }
    if (inputMode === 'url' && !urlInput.trim()) {
      showToast('Please enter a target URL to verify.', 'error');
      return;
    }

    setIsVerifying(true);
    setResult(null);

    try {
      const response = await api.verifyClaims({
        text: inputMode === 'text' ? claimText : undefined,
        url: inputMode === 'url' ? urlInput : undefined,
        documentIds: selectedDocumentIds,
        settings,
      });
      setResult(response);
    } catch (err: any) {
      showToast(err.message || 'Fact-checking verification failed.', 'error');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCopyReport = () => {
    if (!result) return;
    const reportLines = [
      `# NEXORA AI Fact Check Report`,
      `**Summary:** ${result.overall_summary}`,
      `**Claims Evaluated:** ${result.extracted_claims_count}`,
      '',
      ...result.claims.map((c) => (
        `### Claim ${c.claim_id}: "${c.claim_text}"\n` +
        `**Verdict:** ${c.verdict.toUpperCase()} (Confidence: ${c.confidence})\n` +
        `**Explanation:** ${c.explanation}\n` +
        (c.missing_context_flags.length ? `**Context Flags:** ${c.missing_context_flags.join(', ')}\n` : '') +
        (c.supporting_evidence.length ? `**Supporting:** ${c.supporting_evidence.map((s) => s.title).join('; ')}\n` : '') +
        (c.opposing_evidence.length ? `**Opposing:** ${c.opposing_evidence.map((s) => s.title).join('; ')}\n` : '')
      )),
    ];
    navigator.clipboard.writeText(reportLines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    showToast('Fact check report copied to clipboard', 'success');
  };

  const getVerdictBadge = (verdict: VerdictClassification) => {
    switch (verdict) {
      case 'supported':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Supported</span>
          </span>
        );
      case 'contradicted':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/30">
            <XCircle className="w-3.5 h-3.5" />
            <span>Contradicted</span>
          </span>
        );
      case 'mixed':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Mixed Evidence</span>
          </span>
        );
      case 'opinion_or_prediction':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-violet-500/10 text-violet-400 border border-violet-500/30">
            <Scale className="w-3.5 h-3.5" />
            <span>Opinion / Prediction</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Insufficient Evidence</span>
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950 text-slate-100">
      {/* Header bar */}
      <div className="p-4 sm:px-6 border-b border-slate-800/80 bg-midnight-900/40 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">Fact-Checking & Evidence Verification</h2>
            <p className="text-xs text-slate-400">
              Evaluates statements and claims against multi-source web evidence and primary documents
            </p>
          </div>
        </div>

        {selectedDocumentIds.length > 0 && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-xs text-cyan-300">
            <FileText className="w-3.5 h-3.5" />
            <span>{selectedDocumentIds.length} Document(s) Cross-Referenced</span>
          </div>
        )}
      </div>

      {/* Main Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 max-w-5xl mx-auto w-full">
        {/* Input Card */}
        <div className="bg-midnight-900/60 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
          {/* Tabs: Text vs URL */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <button
              onClick={() => setInputMode('text')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                inputMode === 'text'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Claim Text / Narrative</span>
            </button>
            <button
              onClick={() => setInputMode('url')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                inputMode === 'url'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Article / Webpage URL</span>
            </button>
          </div>

          {inputMode === 'text' ? (
            <textarea
              rows={4}
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
              placeholder="Paste any article paragraph, news report, claim, or statement to dissect and fact-check..."
              className="w-full bg-midnight-950 border border-slate-800 rounded-xl p-3 text-xs sm:text-sm text-slate-200 focus:border-cyan-500/50 focus:outline-none leading-relaxed"
            />
          ) : (
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://example.com/news-story-to-verify"
              className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-200 focus:border-cyan-500/50 focus:outline-none"
            />
          )}

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-500">
              Corroborates against multi-engine web search and configured documents.
            </span>
            <button
              onClick={handleVerify}
              disabled={isVerifying}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold shadow-md transition-all ${
                isVerifying
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
                  : 'bg-gradient-to-r from-cyan-500 to-violet-600 text-white shadow-cyan-glow hover:opacity-90'
              }`}
            >
              {isVerifying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying Claims & Sources...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Verify Claims</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Verification Loading State */}
        {isVerifying && (
          <div className="p-8 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mx-auto animate-pulse">
              <Scale className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">Cross-Examining Evidence</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Extracting atomic claims, querying independent web indexes, checking primary reporting, and detecting potential misinformation or missing context...
            </p>
          </div>
        )}

        {/* Verification Results View */}
        {result && (
          <div className="space-y-6">
            {/* Overall Assessment Banner */}
            <div className="p-5 rounded-2xl bg-midnight-900/80 border border-cyan-500/30 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                    Verification Assessment
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    ({result.extracted_claims_count} claim{result.extracted_claims_count !== 1 ? 's' : ''})
                  </span>
                </div>
                <p className="text-sm font-semibold text-slate-100">{result.overall_summary}</p>
              </div>

              <button
                onClick={handleCopyReport}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors shrink-0"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Report'}</span>
              </button>
            </div>

            {/* Claims Breakdown Grid */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Claim-By-Claim Analysis
              </h3>

              {result.claims.map((claim) => (
                <div
                  key={claim.claim_id}
                  className="p-5 rounded-2xl bg-midnight-900/50 border border-slate-800 space-y-4 shadow-sm"
                >
                  {/* Claim Header */}
                  <div className="flex flex-wrap items-start justify-between gap-2.5 pb-3 border-b border-slate-800/80">
                    <div className="flex items-start gap-2.5">
                      <span className="text-xs font-bold text-slate-500 font-mono mt-0.5">
                        #{claim.claim_id}
                      </span>
                      <p className="text-sm font-bold text-slate-100 leading-snug">
                        "{claim.claim_text}"
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {getVerdictBadge(claim.verdict)}
                      <span className="text-[11px] font-semibold text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
                        Confidence: {claim.confidence.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                    {claim.explanation}
                  </div>

                  {/* Missing Context Warnings */}
                  {claim.missing_context_flags.length > 0 && (
                    <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/20 text-xs text-amber-300 space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        <span>Context & Nuance Flags</span>
                      </div>
                      <ul className="list-disc pl-5 text-[11px] text-amber-200/80 space-y-0.5">
                        {claim.missing_context_flags.map((flag, idx) => (
                          <li key={idx}>{flag}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Evidence Cards */}
                  {(claim.supporting_evidence.length > 0 || claim.opposing_evidence.length > 0) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                      {/* Supporting */}
                      {claim.supporting_evidence.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Supporting Sources ({claim.supporting_evidence.length})</span>
                          </span>
                          <div className="space-y-2">
                            {claim.supporting_evidence.map((src) => (
                              <div
                                key={src.source_id}
                                className="p-2.5 rounded-xl bg-midnight-950 border border-emerald-500/20 text-xs space-y-1"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-slate-200 truncate">{src.title}</span>
                                  {src.url && (
                                    <a
                                      href={src.url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-cyan-400 hover:text-cyan-300 shrink-0 ml-1"
                                    >
                                      <ExternalLink className="w-3 h-3" />
                                    </a>
                                  )}
                                </div>
                                <p className="text-[11px] text-slate-400 italic line-clamp-2">"{src.snippet}"</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Opposing */}
                      {claim.opposing_evidence.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-[11px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
                            <XCircle className="w-3 h-3" />
                            <span>Opposing / Refuting Sources ({claim.opposing_evidence.length})</span>
                          </span>
                          <div className="space-y-2">
                            {claim.opposing_evidence.map((src) => (
                              <div
                                key={src.source_id}
                                className="p-2.5 rounded-xl bg-midnight-950 border border-red-500/20 text-xs space-y-1"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-slate-200 truncate">{src.title}</span>
                                  {src.url && (
                                    <a
                                      href={src.url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-cyan-400 hover:text-cyan-300 shrink-0 ml-1"
                                    >
                                      <ExternalLink className="w-3 h-3" />
                                    </a>
                                  )}
                                </div>
                                <p className="text-[11px] text-slate-400 italic line-clamp-2">"{src.snippet}"</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
