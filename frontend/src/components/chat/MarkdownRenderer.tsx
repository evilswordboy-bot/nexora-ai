import React from 'react';
import { CodeBlock } from '../ui/CodeBlock';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  // Parse code blocks vs standard text
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

        // Render paragraphs, headings, bullet lists
        const paragraphs = part.split(/\n\s*\n/);
        return (
          <React.Fragment key={index}>
            {paragraphs.map((p, pIdx) => {
              const trimmed = p.trim();
              if (!trimmed) return null;

              // Headings
              if (trimmed.startsWith('### ')) {
                return (
                  <h3 key={pIdx} className="text-base sm:text-lg font-bold text-slate-100 mt-4 mb-2">
                    {renderInlineFormatted(trimmed.slice(4))}
                  </h3>
                );
              }
              if (trimmed.startsWith('## ')) {
                return (
                  <h2 key={pIdx} className="text-lg sm:text-xl font-bold text-slate-100 mt-5 mb-2 border-b border-slate-800/80 pb-1">
                    {renderInlineFormatted(trimmed.slice(3))}
                  </h2>
                );
              }
              if (trimmed.startsWith('# ')) {
                return (
                  <h1 key={pIdx} className="text-xl sm:text-2xl font-bold text-cyan-400 mt-6 mb-3">
                    {renderInlineFormatted(trimmed.slice(2))}
                  </h1>
                );
              }

              // Blockquotes
              if (trimmed.startsWith('> ')) {
                return (
                  <blockquote
                    key={pIdx}
                    className="border-l-4 border-cyan-500/60 bg-midnight-900/60 px-4 py-2 rounded-r-lg my-2 text-slate-300 italic text-sm"
                  >
                    {renderInlineFormatted(trimmed.slice(2))}
                  </blockquote>
                );
              }

              // Bullet lists
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
                          <span>{renderInlineFormatted(cleanLine)}</span>
                        </li>
                      );
                    })}
                  </ul>
                );
              }

              return (
                <p key={pIdx} className="text-sm sm:text-base text-slate-200">
                  {renderInlineFormatted(trimmed)}
                </p>
              );
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// Helper for bold, italic, inline code
function renderInlineFormatted(text: string): React.ReactNode {
  // Regex to split inline code, bold, italics
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g);

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
    return token;
  });
}
