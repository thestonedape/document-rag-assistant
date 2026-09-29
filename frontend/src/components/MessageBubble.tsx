import { Bot, Clock3, ThumbsDown, ThumbsUp, UserRound } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";
import { CitationCard } from "./CitationCard";

interface Props {
  message: ChatMessage;
  feedback?: 1 | -1;
  onFeedback: (messageId: string, rating: 1 | -1) => void;
}

function linkCitations(content: string, message: ChatMessage): string {
  return content.replace(/\[(S\d+)]/g, (token, sourceId: string) => {
    const citation = message.citations.find((item) => item.source_id === sourceId);
    return citation?.source_url
      ? `[${token}](${citation.source_url}#page=${citation.page_number})`
      : token;
  });
}

export function MessageBubble({ message, feedback, onFeedback }: Props) {
  const isUser = message.role === "user";
  return (
    <article className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div className={`max-w-[88%] ${isUser ? "order-first" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "rounded-br-md bg-brand-600 text-white"
              : "rounded-bl-md border border-slate-200 bg-white text-slate-700 shadow-sm"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-headings:text-ink prose-a:font-semibold prose-a:text-brand-600">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{ a: ({ ...props }) => <a {...props} target="_blank" rel="noreferrer" /> }}
              >
                {linkCitations(message.content, message)}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && message.citations.length > 0 && (
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {message.citations.map((citation) => (
              <CitationCard key={citation.chunk_id} citation={citation} />
            ))}
          </div>
        )}

        {!isUser && (
          <div className="mt-2 flex items-center gap-1 text-slate-400">
            {message.latency_ms !== null && (
              <span className="mr-2 inline-flex items-center gap-1 text-xs">
                <Clock3 className="h-3 w-3" />
                {(message.latency_ms / 1000).toFixed(1)}s
              </span>
            )}
            <button
              onClick={() => onFeedback(message.id, 1)}
              aria-label="Helpful answer"
              className={`rounded p-1.5 hover:bg-emerald-50 hover:text-emerald-600 ${
                feedback === 1 ? "bg-emerald-50 text-emerald-600" : ""
              }`}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => onFeedback(message.id, -1)}
              aria-label="Unhelpful answer"
              className={`rounded p-1.5 hover:bg-red-50 hover:text-red-600 ${
                feedback === -1 ? "bg-red-50 text-red-600" : ""
              }`}
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-600">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </article>
  );
}
