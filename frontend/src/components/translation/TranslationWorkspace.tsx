import React, { useState, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { api } from '../../services/api';
import {
  TranslationTone,
  LanguageDetectionResult,
  SentencePair,
  TranslationResponse,
} from '../../types';
import {
  Globe,
  ArrowRightLeft,
  Copy,
  Check,
  Sparkles,
  BookOpen,
  Volume2,
  RefreshCw,
  Sliders,
  AlertCircle,
  HelpCircle,
  Layers,
} from 'lucide-react';

const COMMON_LANGUAGES = [
  { code: 'auto', name: 'Auto Detect' },
  { code: 'ta', name: 'Tamil (தமிழ்)' },
  { code: 'hi', name: 'Hindi (हिन्दी)' },
  { code: 'te', name: 'Telugu (తెలుగు)' },
  { code: 'ml', name: 'Malayalam (മലയാളം)' },
  { code: 'kn', name: 'Kannada (ಕನ್ನಡ)' },
  { code: 'bn', name: 'Bengali (বাংলা)' },
  { code: 'mr', name: 'Marathi (मराठी)' },
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish (Español)' },
  { code: 'fr', name: 'French (Français)' },
  { code: 'de', name: 'German (Deutsch)' },
  { code: 'ja', name: 'Japanese (日本語)' },
  { code: 'zh', name: 'Chinese (中文)' },
  { code: 'ar', name: 'Arabic (العربية)' },
  { code: 'ru', name: 'Russian (Русский)' },
];

const TONES: { id: TranslationTone; label: string; desc: string }[] = [
  { id: 'formal', label: 'Formal / Respectful', desc: 'Standard polite grammar & respectful honorifics' },
  { id: 'casual', label: 'Casual / Conversational', desc: 'Natural spoken idiom for everyday speech' },
  { id: 'technical', label: 'Technical / Exact', desc: 'Preserves technical precision & jargon' },
  { id: 'simplified', label: 'Simplified / Plain', desc: 'Clear, direct, easy-to-read phrasing' },
];

export const TranslationWorkspace: React.FC = () => {
  const { settings, showToast } = useChat();

  const [sourceText, setSourceText] = useState('');
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('ta');
  const [tone, setTone] = useState<TranslationTone>('formal');
  const [includeTransliteration, setIncludeTransliteration] = useState(true);

  const [isTranslating, setIsTranslating] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionResult, setDetectionResult] = useState<LanguageDetectionResult | null>(null);
  const [translationResult, setTranslationResult] = useState<TranslationResponse | null>(null);
  const [copiedFull, setCopiedFull] = useState(false);
  const [copiedSentenceIndex, setCopiedSentenceIndex] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'side_by_side' | 'full_text'>('side_by_side');

  // Debounced real-time detection on typing
  useEffect(() => {
    if (!sourceText.trim() || sourceText.length < 3) {
      setDetectionResult(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setIsDetecting(true);
        const res = await api.detectLanguage(sourceText);
        setDetectionResult(res);
      } catch (err) {
        // Silently fail or keep previous detection
      } finally {
        setIsDetecting(false);
      }
    }, 450);

    return () => clearTimeout(timer);
  }, [sourceText]);

  const handleTranslate = async () => {
    if (!sourceText.trim()) {
      showToast('Please enter text to translate.', 'error');
      return;
    }

    if (sourceLang === targetLang && sourceLang !== 'auto') {
      showToast('Source and Target languages must be different.', 'info');
      return;
    }

    setIsTranslating(true);
    try {
      const res = await api.translateText({
        text: sourceText,
        sourceLanguage: sourceLang,
        targetLanguage: targetLang,
        tone,
        includeTransliteration,
        settings,
      });
      setTranslationResult(res);
      showToast('Translation completed successfully.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Translation failed. Check backend connection.', 'error');
    } finally {
      setIsTranslating(false);
    }
  };

  const handleCopyFull = () => {
    if (!translationResult) return;
    navigator.clipboard.writeText(translationResult.translated_text);
    setCopiedFull(true);
    setTimeout(() => setCopiedFull(false), 2000);
    showToast('Translated text copied to clipboard', 'info');
  };

  const handleCopySentence = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedSentenceIndex(idx);
    setTimeout(() => setCopiedSentenceIndex(null), 1500);
  };

  const handleSwapLanguages = () => {
    if (sourceLang === 'auto') {
      if (detectionResult) {
        const detected = detectionResult.detected_language;
        setSourceLang(targetLang);
        setTargetLang(detected);
      }
    } else {
      const prevSource = sourceLang;
      setSourceLang(targetLang);
      setTargetLang(prevSource);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-midnight-950 px-4 py-6 md:px-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header Title Banner */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-2xl bg-midnight-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center shadow-cyan-glow">
              <Globe className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-100">Translation Studio & Multilingual Engine</h1>
                <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  Stage 6
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Deep Indic script preservation, Tanglish/Hinglish detection, multi-tone styling & Latin script transliteration.
              </p>
            </div>
          </div>
        </div>

        {/* Translation Controls Bar */}
        <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
          {/* Language Selectors */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 bg-midnight-950 px-3 py-1.5 rounded-lg border border-slate-700/60">
              <span className="text-xs text-slate-400 font-medium">From:</span>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="bg-transparent text-xs font-semibold text-cyan-300 focus:outline-none cursor-pointer"
              >
                {COMMON_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code} className="bg-midnight-900 text-slate-200">
                    {l.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSwapLanguages}
              disabled={sourceLang === 'auto' && !detectionResult}
              className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-700 text-slate-300 transition-colors disabled:opacity-40"
              title="Swap languages"
            >
              <ArrowRightLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-1.5 bg-midnight-950 px-3 py-1.5 rounded-lg border border-slate-700/60">
              <span className="text-xs text-slate-400 font-medium">To:</span>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="bg-transparent text-xs font-semibold text-cyan-300 focus:outline-none cursor-pointer"
              >
                {COMMON_LANGUAGES.filter((l) => l.code !== 'auto').map((l) => (
                  <option key={l.code} value={l.code} className="bg-midnight-900 text-slate-200">
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Tone Selector */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {TONES.map((t) => (
              <button
                key={t.id}
                onClick={() => setTone(t.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  tone === t.id
                    ? 'bg-gradient-to-r from-cyan-500/20 to-violet-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'bg-slate-800/40 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
                title={t.desc}
              >
                {t.label.split(' / ')[0]}
              </button>
            ))}
          </div>

          {/* Transliteration Checkbox & Action Button */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
              <input
                type="checkbox"
                checked={includeTransliteration}
                onChange={(e) => setIncludeTransliteration(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-midnight-950 text-cyan-500 focus:ring-cyan-500/20"
              />
              <span>Phonetic Transliteration</span>
            </label>

            <button
              onClick={handleTranslate}
              disabled={isTranslating || !sourceText.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white text-xs font-bold shadow-cyan-glow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTranslating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Translating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Translate</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Input & Output Studio Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Source Input Box */}
          <div className="flex flex-col bg-midnight-900 border border-slate-800 rounded-2xl p-4 min-h-[360px] relative shadow-lg">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-300">Input Text</span>
                {isDetecting && (
                  <span className="text-[10px] text-cyan-400 flex items-center gap-1">
                    <RefreshCw className="w-2.5 h-2.5 animate-spin" /> Detecting...
                  </span>
                )}
                {detectionResult && !isDetecting && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-cyan-300 border border-slate-700">
                      Detected: {detectionResult.language_name} ({Math.round(detectionResult.confidence * 100)}%)
                    </span>
                    {detectionResult.is_code_switched && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-950/60 text-violet-300 border border-violet-700/50">
                        {detectionResult.code_switch_types.join(', ')}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <span className="text-[11px] text-slate-500">{sourceText.length} characters</span>
            </div>

            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="Enter or paste text here (Tamil, Hindi, Tanglish, Hinglish, English, or any supported language)..."
              className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 text-sm leading-relaxed resize-none focus:outline-none"
            />

            {/* Quick Demo Samples */}
            <div className="pt-3 border-t border-slate-800/60 flex items-center gap-2 overflow-x-auto text-[11px]">
              <span className="text-slate-500 shrink-0">Try samples:</span>
              <button
                onClick={() => setSourceText('வணக்கம், இன்று வானிலை மிகவும் அழகாக இருக்கிறது. நீங்கள் நலமா?')}
                className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
              >
                Tamil
              </button>
              <button
                onClick={() => setSourceText('नमस्ते, आज का दिन बहुत सुंदर है। आप कैसे हैं?')}
                className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
              >
                Hindi
              </button>
              <button
                onClick={() => setSourceText('Nalaiku meeting cancel pannalam, romba mazhai peiyuthu bro.')}
                className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
              >
                Tanglish
              </button>
              <button
                onClick={() => setSourceText('Kal ka meeting postpone karna padega, bahut baarish ho rahi hai.')}
                className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
              >
                Hinglish
              </button>
            </div>
          </div>

          {/* Translation Output Box */}
          <div className="flex flex-col bg-midnight-900 border border-slate-800 rounded-2xl p-4 min-h-[360px] relative shadow-lg">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-300">Target Output</span>
                {translationResult && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950/60 text-cyan-300 border border-cyan-800/50">
                      Tone: {translationResult.tone}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                      {translationResult.provider}
                    </span>
                  </div>
                )}
              </div>

              {translationResult && (
                <div className="flex items-center gap-2">
                  <div className="flex items-center p-0.5 bg-midnight-950 rounded-lg border border-slate-800 text-[10px]">
                    <button
                      onClick={() => setActiveTab('side_by_side')}
                      className={`px-2 py-0.5 rounded ${
                        activeTab === 'side_by_side' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400'
                      }`}
                    >
                      Sentence Alignment
                    </button>
                    <button
                      onClick={() => setActiveTab('full_text')}
                      className={`px-2 py-0.5 rounded ${
                        activeTab === 'full_text' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400'
                      }`}
                    >
                      Full Text
                    </button>
                  </div>

                  <button
                    onClick={handleCopyFull}
                    className="p-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 transition-colors"
                    title="Copy full translation"
                  >
                    {copiedFull ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-300" />}
                  </button>
                </div>
              )}
            </div>

            {/* Translation Content Area */}
            {!translationResult && !isTranslating ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
                <Layers className="w-10 h-10 mb-2 stroke-1 text-slate-600" />
                <p className="text-sm font-medium">Ready to translate</p>
                <p className="text-xs text-slate-500 max-w-xs mt-1">
                  Type or paste text on the left, choose your desired tone and language, and click Translate.
                </p>
              </div>
            ) : isTranslating ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-cyan-400">
                <RefreshCw className="w-8 h-8 animate-spin mb-3 text-cyan-400" />
                <p className="text-sm font-medium">Translating & aligning sentences...</p>
                <p className="text-xs text-slate-500 mt-1">Preserving cultural nuance and honorifics</p>
              </div>
            ) : activeTab === 'full_text' ? (
              <div className="flex-1 overflow-y-auto space-y-4">
                <div className="text-sm leading-relaxed text-slate-100 whitespace-pre-wrap">
                  {translationResult?.translated_text}
                </div>

                {translationResult?.full_transliteration && (
                  <div className="p-3 rounded-xl bg-midnight-950/70 border border-slate-800/80">
                    <div className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Volume2 className="w-3.5 h-3.5" />
                      Phonetic Transliteration (Latin Script)
                    </div>
                    <p className="text-xs text-slate-300 italic font-mono leading-relaxed">
                      {translationResult.full_transliteration}
                    </p>
                  </div>
                )}

                {translationResult?.nuance_notes && (
                  <div className="p-3 rounded-xl bg-violet-950/20 border border-violet-800/40">
                    <div className="text-[11px] font-bold text-violet-300 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5" />
                      Cultural & Tone Nuance
                    </div>
                    <p className="text-xs text-violet-200 leading-relaxed">
                      {translationResult.nuance_notes}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              /* Side-by-side Sentence Pair View */
              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                {translationResult?.sentence_pairs.map((pair, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-midnight-950/80 border border-slate-800 hover:border-slate-700 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="text-[10px] font-mono text-slate-500">Sentence {idx + 1}</span>
                      <button
                        onClick={() => handleCopySentence(pair.target_sentence, idx)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-cyan-300 transition-opacity"
                        title="Copy this sentence"
                      >
                        {copiedSentenceIndex === idx ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>

                    <div className="space-y-1.5">
                      <p className="text-xs text-slate-400 border-l-2 border-slate-700 pl-2">
                        {pair.source_sentence}
                      </p>
                      <p className="text-sm text-slate-100 font-medium border-l-2 border-cyan-500 pl-2">
                        {pair.target_sentence}
                      </p>
                      {pair.transliteration && (
                        <p className="text-[11px] text-cyan-400/80 italic font-mono pl-2">
                          ↳ {pair.transliteration}
                        </p>
                      )}
                    </div>
                  </div>
                ))}

                {translationResult?.nuance_notes && (
                  <div className="p-3 rounded-xl bg-violet-950/20 border border-violet-800/40">
                    <div className="text-[11px] font-bold text-violet-300 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5" />
                      Cultural & Tone Nuance
                    </div>
                    <p className="text-xs text-violet-200 leading-relaxed">
                      {translationResult.nuance_notes}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
