import React, { useState } from 'react';
import { SearchResultItem } from '../../types';
import { Globe, ExternalLink, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';

interface SourcesSectionProps {
  sources: SearchResultItem[];
  researchQueries?: string[];
}

export const SourcesSection: React.FC<SourcesSectionProps> = ({ sources, researchQueries }) => {
  const [expanded, setExpanded] = useState(true);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="my-3.5 rounded-2xl bg-midnight-950/70 border border-slate-800/90 overflow-hidden shadow-lg transition-all">
      {/* Header bar */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="px-4 py-2.5 bg-midnight-900/60 flex items-center justify-between cursor-pointer hover:bg-midnight-900 transition-colors"
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-cyan-300">
          <Globe className="w-4 h-4 text-cyan-400" />
          <span>Grounded in {sources.length} Verified Sources</span>
          {researchQueries && researchQueries.length > 0 && (
            <span className="hidden sm:inline-block px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/30 text-[10px]">
              {researchQueries.length} Research Vectors
            </span>
          )}
        </div>

        <button className="text-slate-400 hover:text-slate-200 p-1">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Expanded Sources Grid */}
      {expanded && (
        <div className="p-3 space-y-2.5">
          {researchQueries && researchQueries.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pb-2 border-b border-slate-800/60">
              <span className="text-[11px] text-slate-500 mr-1 flex items-center gap-1">
                <BookOpen className="w-3 h-3" /> Queries:
              </span>
              {researchQueries.map((q, idx) => (
                <span
                  key={idx}
                  className="text-[11px] px-2 py-0.5 rounded-md bg-slate-900 text-slate-300 border border-slate-800"
                >
                  "{q}"
                </span>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {sources.map((source, index) => {
              const sourceNum = source.source_id || index + 1;

              return (
                <a
                  key={index}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group p-2.5 rounded-xl bg-midnight-900/50 hover:bg-midnight-850 border border-slate-800/80 hover:border-cyan-500/40 transition-all flex flex-col justify-between"
                  title={source.snippet}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="shrink-0 w-4 h-4 rounded bg-cyan-500/20 text-cyan-400 text-[10px] font-bold flex items-center justify-center">
                          {sourceNum}
                        </span>
                        <span className="text-[11px] font-medium text-slate-400 group-hover:text-cyan-300 truncate">
                          {source.domain}
                        </span>
                      </div>
                      <ExternalLink className="w-3 h-3 text-slate-500 group-hover:text-cyan-400 shrink-0 transition-colors" />
                    </div>

                    <h4 className="text-xs font-semibold text-slate-200 group-hover:text-white line-clamp-1">
                      {source.title}
                    </h4>

                    {source.snippet && (
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-relaxed">
                        {source.snippet}
                      </p>
                    )}
                  </div>
                </a>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
