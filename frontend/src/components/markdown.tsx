import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders the agent's Markdown answers in the Sentinel design language:
 * monochrome, flat, motion-free. Element styling lives here; code-block vs
 * inline-code handling is finished in globals.css (.md-body pre code reset).
 */
const components: Components = {
  h1: ({ children }) => (
    <h2 className="mb-2 mt-4 text-[15px] font-semibold text-[var(--color-text)] first:mt-0">
      {children}
    </h2>
  ),
  h2: ({ children }) => (
    <h3 className="mb-2 mt-4 text-[14px] font-semibold text-[var(--color-text)] first:mt-0">
      {children}
    </h3>
  ),
  h3: ({ children }) => (
    <h4 className="mb-1.5 mt-3 text-[13px] font-semibold uppercase tracking-wide text-[var(--color-muted)] first:mt-0">
      {children}
    </h4>
  ),
  p: ({ children }) => (
    <p className="my-2 leading-relaxed text-[var(--color-text)] first:mt-0 last:mb-0">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="my-2 flex flex-col gap-1 pl-4 [list-style:disc] marker:text-[var(--color-faint)]">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 flex flex-col gap-1 pl-4 [list-style:decimal] marker:text-[var(--color-faint)]">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-[var(--color-text)]">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[var(--color-accent)] underline underline-offset-2"
    >
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code className="rounded bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[12.5px] text-[var(--color-text)]">
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="my-3 overflow-x-auto rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] p-3 font-mono text-[12.5px] leading-relaxed text-[var(--color-text)]">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-[var(--color-border)] pl-3 text-[var(--color-muted)]">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-[var(--color-border)]" />,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-[var(--color-border)] px-2 py-1 text-left font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-[var(--color-border)] px-2 py-1">{children}</td>
  ),
};

export function Markdown({ children }: { children: string }) {
  return (
    <div className="md-body text-[15px] text-[var(--color-text)]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
