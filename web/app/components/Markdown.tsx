"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

// One renderer for everything that contains prose or math: the agent's replies
// and the research write-up. Markdown becomes real formatting, and $...$ /
// $$...$$ become real typeset math instead of literal dollar signs.
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false }]]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
