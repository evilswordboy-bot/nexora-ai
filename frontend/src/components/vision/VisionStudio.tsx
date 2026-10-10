import React, { useState, useRef } from 'react';
import { useChat } from '../../context/ChatContext';
import { api } from '../../services/api';
import {
  VisionAnalysisType,
  VisionAnalyzeResponse,
  OCRResponse,
  ImageCompareResponse,
} from '../../types';
import {
  Sparkles,
  Upload,
  FileText,
  Layers,
  ArrowRightLeft,
  ScanText,
  ShieldAlert,
  Loader2,
  Trash2,
  CheckCircle,
  Copy,
  Info,
} from 'lucide-react';

export const VisionStudio: React.FC = () => {
  const { settings, showToast } = useChat();

  const [activeTab, setActiveTab] = useState<'inspect' | 'ocr' | 'compare'>('inspect');
  const [analysisType, setAnalysisType] = useState<VisionAnalysisType>('general');
  const [prompt, setPrompt] = useState('Analyze this visual in detail, identifying components, hierarchy, and key insights.');

  // State for single/multi inspect
  const [inspectImages, setInspectImages] = useState<string[]>([]);
  const [inspectResult, setInspectResult] = useState<VisionAnalyzeResponse | null>(null);

  // State for OCR
  const [ocrImage, setOcrImage] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResponse | null>(null);

  // State for compare
  const [compareImg1, setCompareImg1] = useState<string | null>(null);
  const [compareImg2, setCompareImg2] = useState<string | null>(null);
  const [compareFocus, setCompareFocus] = useState<'general' | 'ui_diff' | 'chart_comparison' | 'text_diff'>('general');
  const [compareResult, setCompareResult] = useState<ImageCompareResponse | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const inspectInputRef = useRef<HTMLInputElement>(null);
  const ocrInputRef = useRef<HTMLInputElement>(null);
  const comp1InputRef = useRef<HTMLInputElement>(null);
  const comp2InputRef = useRef<HTMLInputElement>(null);

  const readFileAsBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (file.size > 10 * 1024 * 1024) {
        reject(new Error('File exceeds 10MB limit.'));
        return;
      }
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error('Failed to read file.'));
      reader.readAsDataURL(file);
    });
  };

  const handleInspectUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    try {
      const files = Array.from(e.target.files);
      const b64List: string[] = [];
      for (const f of files) {
        if (inspectImages.length + b64List.length >= 5) break;
        const b64 = await readFileAsBase64(f);
        b64List.push(b64);
      }
      setInspectImages((prev) => [...prev, ...b64List].slice(0, 5));
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleRunInspect = async () => {
    if (inspectImages.length === 0) {
      showToast('Please upload at least one image.', 'error');
      return;
    }
    setIsLoading(true);
    setInspectResult(null);
    try {
      const res = await api.analyzeVision(
        {
          images: inspectImages,
          prompt,
          analysis_type: analysisType,
        },
        settings
      );
      setInspectResult(res);
      showToast('Visual analysis completed.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Analysis failed.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunOCR = async () => {
    if (!ocrImage) {
      showToast('Please upload an image containing text.', 'error');
      return;
    }
    setIsLoading(true);
    setOcrResult(null);
    try {
      const res = await api.extractOCR({
        image: ocrImage,
        language_hint: settings.preferredLanguage !== 'auto' ? settings.preferredLanguage : 'eng',
        quarantine_output: true,
      });
      setOcrResult(res);
      showToast(`OCR complete: ${res.word_count} words extracted.`, 'success');
    } catch (err: any) {
      showToast(err.message || 'OCR extraction failed.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunCompare = async () => {
    if (!compareImg1 || !compareImg2) {
      showToast('Please upload both images for comparison.', 'error');
      return;
    }
    setIsLoading(true);
    setCompareResult(null);
    try {
      const res = await api.compareImages(
        {
          image1: compareImg1,
          image2: compareImg2,
          image1_label: 'Design v1',
          image2_label: 'Design v2',
          comparison_focus: compareFocus,
        },
        settings
      );
      setCompareResult(res);
      showToast('Visual comparison completed.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Comparison failed.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const copyText = (t: string) => {
    navigator.clipboard.writeText(t);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 overflow-y-auto bg-midnight-950 p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center shadow-cyan-glow">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-xl font-bold text-slate-100">Vision Intelligence Studio</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                Stage 9
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Multimodal image understanding, OCR extraction with prompt-injection defense, and visual comparison.
            </p>
          </div>

          {/* Studio Mode Selector */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-midnight-900 border border-slate-800">
            <button
              onClick={() => setActiveTab('inspect')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'inspect'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Visual Analysis</span>
            </button>
            <button
              onClick={() => setActiveTab('ocr')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'ocr'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ScanText className="w-3.5 h-3.5" />
              <span>OCR Extraction</span>
            </button>
            <button
              onClick={() => setActiveTab('compare')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'compare'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ArrowRightLeft className="w-3.5 h-3.5" />
              <span>Image Comparison</span>
            </button>
          </div>
        </div>

        {/* TAB 1: VISUAL ANALYSIS */}
        {activeTab === 'inspect' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Left Column: Upload & Settings */}
              <div className="md:col-span-1 space-y-4">
                <div className="p-4 rounded-2xl bg-midnight-900/90 border border-slate-800 space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Image Uploads</h3>

                  <input
                    type="file"
                    ref={inspectInputRef}
                    onChange={handleInspectUpload}
                    multiple
                    accept="image/png,image/jpeg,image/jpg,image/webp"
                    className="hidden"
                  />

                  <div
                    onClick={() => inspectInputRef.current?.click()}
                    className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-6 text-center cursor-pointer transition-colors bg-midnight-950/40 group"
                  >
                    <Upload className="w-8 h-8 text-slate-500 group-hover:text-cyan-400 mx-auto mb-2 transition-colors" />
                    <p className="text-xs font-medium text-slate-300">Click to upload images</p>
                    <p className="text-[10px] text-slate-500 mt-1">PNG, JPG, WEBP (Max 5, 10MB each)</p>
                  </div>

                  {inspectImages.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Uploaded ({inspectImages.length}/5)</span>
                        <button
                          onClick={() => setInspectImages([])}
                          className="text-[11px] text-red-400 hover:underline"
                        >
                          Clear all
                        </button>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        {inspectImages.map((src, i) => (
                          <div key={i} className="relative group rounded-lg overflow-hidden border border-slate-700 aspect-square bg-black">
                            <img src={src} alt="Uploaded" className="w-full h-full object-cover" />
                            <button
                              onClick={() => setInspectImages((prev) => prev.filter((_, idx) => idx !== i))}
                              className="absolute top-1 right-1 p-1 rounded bg-red-600/80 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Analysis Category */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Analysis Type</label>
                    <select
                      value={analysisType}
                      onChange={(e) => setAnalysisType(e.target.value as VisionAnalysisType)}
                      className="w-full text-xs bg-midnight-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500/60"
                    >
                      <option value="general">General Scene & Objects</option>
                      <option value="ui_diagram">UI Design & UX Hierarchy</option>
                      <option value="charts_data">Charts, Trends & Data Points</option>
                      <option value="technical_circuit">Technical Schematics & Circuits</option>
                      <option value="ocr_extract">Deep Text & Equations</option>
                    </select>
                  </div>

                  <button
                    onClick={handleRunInspect}
                    disabled={isLoading || inspectImages.length === 0}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-600 text-white text-xs font-bold shadow-cyan-glow hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                  >
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    <span>Run Visual Intelligence</span>
                  </button>
                </div>
              </div>

              {/* Right Column: Prompt & Output */}
              <div className="md:col-span-2 space-y-4">
                <div className="p-4 rounded-2xl bg-midnight-900/90 border border-slate-800 space-y-3">
                  <label className="text-xs font-semibold text-slate-300">Custom Inquiry / Prompt</label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={2}
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/60 resize-none font-sans"
                    placeholder="Ask questions about specific visual elements or design details..."
                  />
                </div>

                {inspectResult ? (
                  <div className="p-5 rounded-2xl bg-midnight-900 border border-slate-800 space-y-4 shadow-xl">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-cyan-400" />
                        <span className="text-xs font-bold text-slate-200">Analysis Result</span>
                        <span className="text-[10px] text-slate-500 font-mono">({inspectResult.model})</span>
                      </div>
                      <button
                        onClick={() => copyText(inspectResult.analysis)}
                        className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                      >
                        {copied ? <CheckCircle className="w-3.5 h-3.5 text-cyan-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>

                    {/* Metadata chips */}
                    <div className="flex flex-wrap gap-2">
                      {inspectResult.image_metadata.map((meta, i) => (
                        <div key={i} className="px-2 py-1 rounded bg-midnight-950 border border-slate-800 text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
                          <span>Img {i+1}: {meta.width}x{meta.height}</span>
                          <span className="text-cyan-400">{meta.format.toUpperCase()}</span>
                          <span>{meta.aspect_ratio}</span>
                        </div>
                      ))}
                    </div>

                    <div className="prose prose-invert prose-xs max-w-none text-slate-200 text-xs leading-relaxed whitespace-pre-wrap">
                      {inspectResult.analysis}
                    </div>
                  </div>
                ) : (
                  <div className="p-12 text-center border border-dashed border-slate-800/80 rounded-2xl text-slate-500">
                    <Sparkles className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                    <p className="text-xs">Upload images and click Run to analyze visual content with the configured vision engine.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: OCR EXTRACTION */}
        {activeTab === 'ocr' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl bg-midnight-900 border border-slate-800 space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">OCR Image Input</h3>

              <input
                type="file"
                ref={ocrInputRef}
                onChange={async (e) => {
                  if (e.target.files && e.target.files[0]) {
                    try {
                      const b64 = await readFileAsBase64(e.target.files[0]);
                      setOcrImage(b64);
                    } catch (err: any) {
                      showToast(err.message, 'error');
                    }
                  }
                }}
                accept="image/png,image/jpeg,image/jpg,image/webp"
                className="hidden"
              />

              {ocrImage ? (
                <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-black aspect-video">
                  <img src={ocrImage} alt="OCR Target" className="w-full h-full object-contain" />
                  <button
                    onClick={() => setOcrImage(null)}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-red-600/80 text-white"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => ocrInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-8 text-center cursor-pointer transition-colors bg-midnight-950/40 group"
                >
                  <ScanText className="w-8 h-8 text-slate-500 group-hover:text-cyan-400 mx-auto mb-2 transition-colors" />
                  <p className="text-xs font-medium text-slate-300">Upload screenshot, photo, or document image</p>
                  <p className="text-[10px] text-slate-500 mt-1">PNG, JPG, WEBP with printed or handwritten text</p>
                </div>
              )}

              <button
                onClick={handleRunOCR}
                disabled={isLoading || !ocrImage}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-600 text-white text-xs font-bold shadow-cyan-glow hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanText className="w-4 h-4" />}
                <span>Extract Text via OCR</span>
              </button>
            </div>

            <div className="p-5 rounded-2xl bg-midnight-900 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-bold text-slate-200">Extracted OCR Transcription</span>
                </div>
                {ocrResult && (
                  <button
                    onClick={() => copyText(ocrResult.text)}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                  >
                    {copied ? <CheckCircle className="w-3.5 h-3.5 text-cyan-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                )}
              </div>

              {ocrResult ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                    <span>Characters: <b className="text-cyan-400">{ocrResult.raw_character_count}</b></span>
                    <span>Words: <b className="text-cyan-400">{ocrResult.word_count}</b></span>
                    {ocrResult.is_quarantined && (
                      <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                        <ShieldAlert className="w-3 h-3 text-amber-400" />
                        Prompt-Injection Defended
                      </span>
                    )}
                  </div>

                  <div className="p-3 rounded-xl bg-midnight-950 border border-slate-800 text-xs font-mono text-slate-300 max-h-[350px] overflow-y-auto whitespace-pre-wrap">
                    {ocrResult.text || 'No legible text detected in image.'}
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center text-slate-500">
                  <p className="text-xs">Extracted OCR text with security boundary tags will appear here.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: IMAGE COMPARISON */}
        {activeTab === 'compare' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Image A */}
              <div className="p-4 rounded-2xl bg-midnight-900 border border-slate-800 space-y-3">
                <span className="text-xs font-bold text-cyan-400">Design v1 (Baseline)</span>
                <input
                  type="file"
                  ref={comp1InputRef}
                  onChange={async (e) => {
                    if (e.target.files && e.target.files[0]) {
                      const b64 = await readFileAsBase64(e.target.files[0]);
                      setCompareImg1(b64);
                    }
                  }}
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  className="hidden"
                />
                {compareImg1 ? (
                  <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-black aspect-video">
                    <img src={compareImg1} alt="Image 1" className="w-full h-full object-contain" />
                    <button
                      onClick={() => setCompareImg1(null)}
                      className="absolute top-2 right-2 p-1.5 rounded-lg bg-red-600/80 text-white"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div
                    onClick={() => comp1InputRef.current?.click()}
                    className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-8 text-center cursor-pointer bg-midnight-950/40 group"
                  >
                    <Upload className="w-6 h-6 text-slate-500 group-hover:text-cyan-400 mx-auto mb-2" />
                    <p className="text-xs text-slate-300">Upload Image A</p>
                  </div>
                )}
              </div>

              {/* Image B */}
              <div className="p-4 rounded-2xl bg-midnight-900 border border-slate-800 space-y-3">
                <span className="text-xs font-bold text-violet-400">Design v2 (Revision)</span>
                <input
                  type="file"
                  ref={comp2InputRef}
                  onChange={async (e) => {
                    if (e.target.files && e.target.files[0]) {
                      const b64 = await readFileAsBase64(e.target.files[0]);
                      setCompareImg2(b64);
                    }
                  }}
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  className="hidden"
                />
                {compareImg2 ? (
                  <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-black aspect-video">
                    <img src={compareImg2} alt="Image 2" className="w-full h-full object-contain" />
                    <button
                      onClick={() => setCompareImg2(null)}
                      className="absolute top-2 right-2 p-1.5 rounded-lg bg-red-600/80 text-white"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div
                    onClick={() => comp2InputRef.current?.click()}
                    className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-8 text-center cursor-pointer bg-midnight-950/40 group"
                  >
                    <Upload className="w-6 h-6 text-slate-500 group-hover:text-cyan-400 mx-auto mb-2" />
                    <p className="text-xs text-slate-300">Upload Image B</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3">
              <select
                value={compareFocus}
                onChange={(e) => setCompareFocus(e.target.value as any)}
                className="w-full sm:w-auto text-xs bg-midnight-900 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none"
              >
                <option value="general">General Comparison</option>
                <option value="ui_diff">UI Layout & Component Diff</option>
                <option value="chart_comparison">Chart & Data Points Comparison</option>
                <option value="text_diff">Typography & Textual Modifications</option>
              </select>

              <button
                onClick={handleRunCompare}
                disabled={isLoading || !compareImg1 || !compareImg2}
                className="w-full sm:flex-1 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-xs font-bold shadow-violet-glow hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRightLeft className="w-4 h-4" />}
                <span>Compare Visual Artifacts</span>
              </button>
            </div>

            {compareResult && (
              <div className="p-5 rounded-2xl bg-midnight-900 border border-slate-800 space-y-4">
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Comparison Synthesis</h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-3 rounded-xl bg-midnight-950 border border-slate-800 space-y-1">
                    <span className="text-[11px] font-bold text-cyan-400">Identified Shared Features</span>
                    <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
                      {compareResult.similarities.map((s, idx) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3 rounded-xl bg-midnight-950 border border-slate-800 space-y-1">
                    <span className="text-[11px] font-bold text-amber-400">Identified Discrepancies</span>
                    <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
                      {compareResult.differences.map((d, idx) => (
                        <li key={idx}>{d}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="prose prose-invert prose-xs max-w-none text-slate-200 text-xs leading-relaxed whitespace-pre-wrap pt-2 border-t border-slate-800">
                  {compareResult.comparison_summary}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
