import React from 'react';
import { CodeBlock } from '../ui/CodeBlock';
import { SearchResultItem } from '../../types';

interface MarkdownRendererProps {
  content: string;
  sources?: SearchResultItem[];
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, sources }) => {
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-3 leading-relaxed text-slate-200">
      {parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const firstLineEnd = part.indexOf('\n');
          const language = part.slice(3, firstLineEnd).trim();
          const code = part.slice(firstLineEnd + 1, -3);
          return <CodeBlock key={index} language={language} code={code} />;
        }

        const paragraphs = part.split(/\n\s*\n/);
        return (
          <React.Fragment key={index}>
            {paragraphs.map((p, pIdx) => {
              const trimmed = p.trim();
              if (!trimmed) return null;

              if (trimmed.startsWith('### ')) {
                return (
                  <h3 key={pIdx} className="text-base sm:text-lg font-bold text-slate-100 mt-4 mb-2">
                    {renderInlineFormatted(trimmed.slice(4), sources)}
                  </h3>
                );
              }
              if (trimmed.startsWith('## ')) {
                return (
                  <h2 key={pIdx} className="text-lg sm:text-xl font-bold text-slate-100 mt-5 mb-2 border-b border-slate-800/80 pb-1">
                    {renderInlineFormatted(trimmed.slice(3), sources)}
                  </h2>
                );
              }
              if (trimmed.startsWith('# ')) {
                return (
                  <h1 key={pIdx} className="text-xl sm:text-2xl font-bold text-cyan-400 mt-6 mb-3">
                    {renderInlineFormatted(trimmed.slice(2), sources)}
                  </h1>
                );
              }

              if (trimmed.startsWith('> ')) {
                return (
                  <blockquote
                    key={pIdx}
                    className="border-l-4 border-cyan-500/60 bg-midnight-900/60 px-4 py-2 rounded-r-lg my-2 text-slate-300 italic text-sm"
                  >
                    {renderInlineFormatted(trimmed.slice(2), sources)}
                  </blockquote>
                );
              }

              const lines = trimmed.split('\n');
              const isList = lines.every((line) => line.trim().startsWith('- ') || line.trim().startsWith('* ') || /^\d+\.\s/.test(line.trim()));

              if (isList) {
                return (
                  <ul key={pIdx} className="space-y-1.5 my-2 pl-4">
                    {lines.map((line, lIdx) => {
                      const cleanLine = line.replace(/^[-*]\s+|\d+\.\s+/, '').trim();
                      return (
                        <li key={lIdx} className="flex items-start gap-2 text-sm text-slate-200">
                          <span className="text-cyan-400 font-bold mt-1 shrink-0">•</span>
                          <span>{renderInlineFormatted(cleanLine, sources)}</span>
                        </li>
                      );
                    })}
                  </ul>
                );
              }

              return (
                <p key={pIdx} className="text-sm sm:text-base text-slate-200">
                  {renderInlineFormatted(trimmed, sources)}
                </p>
              );
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};

function renderInlineFormatted(text: string, sources?: SearchResultItem[]): React.ReactNode {
  // Matches inline code `code`, bold **text**, italics *text*, standard links [title](url), or citations [1]
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[\d+\]|\[[^\]]+\]\([^)]+\))/g);

  return tokens.map((token, i) => {
    if (token.startsWith('`') && token.endsWith('`') && token.length > 2) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 mx-0.5 rounded-md bg-midnight-950 border border-slate-700/50 text-cyan-300 font-mono text-xs"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    if (token.startsWith('**') && token.endsWith('**') && token.length > 4) {
      return (
        <strong key={i} className="font-semibold text-slate-100">
          {token.slice(2, -2)}
        </strong>
      );
    }
    if (token.startsWith('*') && token.endsWith('*') && token.length > 2) {
      return (
        <em key={i} className="italic text-slate-300">
          {token.slice(1, -1)}
        </em>
      );
    }

    // Numbered citation like [1], [2]
    const citationMatch = token.match(/^\[(\d+)\]$/);
    if (citationMatch) {
      const citeNum = parseInt(citationMatch[1], 10);
      const matchedSource = sources?.find((s) => (s.source_id || 0) === citeNum) || sources?.[citeNum - 1];

      if (matchedSource) {
        return (
          <a
            key={i}
            href={matchedSource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[10px] font-bold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 hover:border-cyan-400 align-baseline cursor-pointer transition-all shadow-sm"
            title={`${matchedSource.title} (${matchedSource.domain})`}
          >
            {token}
          </a>
        );
      } else {
        return (
          <span
            key={i}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 align-baseline"
          >
            {token}
          </span>
        );
      }
    }

    // Markdown link [Title](url)
    const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const linkText = linkMatch[1];
      const linkUrl = linkMatch[2];
      return (
        <a
          key={i}
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-400 hover:text-cyan-300 underline font-medium"
        >
          {linkText}
        </a>
      );
    }

    return token;
  });
}
