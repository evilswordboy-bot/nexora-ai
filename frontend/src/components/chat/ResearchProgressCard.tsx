import React from 'react';
import { ResearchProgress } from '../../types';
import { Compass, Search, BookOpen, Sparkles, CheckCircle2 } from 'lucide-react';

interface ResearchProgressCardProps {
  progress: ResearchProgress;
}

export const ResearchProgressCard: React.FC<ResearchProgressCardProps> = ({ progress }) => {
  const steps = [
    { key: 'decomposing', label: 'Query Decomposition', icon: Compass },
    { key: 'searching', label: 'Web Exploration', icon: Search },
    { key: 'reading', label: 'Content Extraction', icon: BookOpen },
    { key: 'synthesizing', label: 'Evidence Synthesis', icon: Sparkles },
  ];

  const currentIdx = steps.findIndex((s) => s.key === progress.step);

  return (
    <div className="py-4 px-4 sm:px-6 bg-midnight-900/60 border-y border-violet-500/20 shadow-violet-glow my-2 animate-in fade-in duration-300">
      <div className="max-w-3xl mx-auto space-y-3">
        {/* Header status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-violet-300">
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-ping" />
            <span>NEXORA Deep Research Pipeline Active</span>
          </div>
          <span className="text-[11px] font-medium text-slate-400 capitalize">
            {progress.step} Phase
          </span>
        </div>

        {/* Stepper pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {steps.map((s, idx) => {
            const Icon = s.icon;
            const isDone = currentIdx > idx;
            const isCurrent = currentIdx === idx;

            return (
              <div
                key={s.key}
                className={`p-2 rounded-xl border flex items-center gap-2 text-xs transition-all ${
                  isCurrent
                    ? 'bg-violet-950/60 border-violet-500/50 text-violet-200 font-semibold shadow-sm'
                    : isDone
                    ? 'bg-midnight-950 border-slate-800 text-slate-400'
                    : 'bg-midnight-950/40 border-slate-900 text-slate-600'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                ) : (
                  <Icon className={`w-3.5 h-3.5 shrink-0 ${isCurrent ? 'text-violet-400 animate-pulse' : 'text-slate-500'}`} />
                )}
                <span className="truncate text-[11px]">{s.label}</span>
              </div>
            );
          })}
        </div>

        {/* Message description */}
        <div className="p-2.5 rounded-xl bg-midnight-950/70 border border-slate-800/80 text-xs text-slate-300 flex items-center justify-between">
          <p className="truncate mr-2">{progress.message}</p>
        </div>

        {/* Subqueries if present */}
        {progress.queries && progress.queries.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {progress.queries.map((q, idx) => (
              <span
                key={idx}
                className="text-[10px] px-2 py-0.5 rounded-md bg-midnight-950 border border-violet-500/30 text-violet-300"
              >
                Vector: "{q}"
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
