import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, LoaderCircle, Send, Sparkles } from "lucide-react";
import { chatApi, errorMessage } from "../api/client";
import type { ChatMessage, DocumentRecord } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  conversationId: string | null;
  messages: ChatMessage[];
  documents: DocumentRecord[];
  selectedDocumentIds: string[];
  onMessagesChange: (messages: ChatMessage[]) => void;
  onConversationCreated: (id: string) => void;
}

const suggestions = [
  "Summarize the key ideas in these documents.",
  "What conclusions are supported by the sources?",
  "Compare the main arguments and cite the relevant pages.",
];

export function ChatWindow({
  conversationId,
  messages,
  documents,
  selectedDocumentIds,
  onMessagesChange,
  onConversationCreated,
}: Props) {
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState<Record<string, 1 | -1>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const sendQuestion = async (event?: FormEvent) => {
    event?.preventDefault();
    const content = question.trim();
    if (!content || sending) return;

    const optimistic: ChatMessage = {
      id: `pending-${Date.now()}`,
      conversation_id: conversationId ?? "",
      role: "user",
      content,
      citations: [],
      latency_ms: null,
      created_at: new Date().toISOString(),
    };
    const nextMessages = [...messages, optimistic];
    onMessagesChange(nextMessages);
    setQuestion("");
    setSending(true);
    setError("");

    try {
      const response = await chatApi.send({
        question: content,
        conversation_id: conversationId ?? undefined,
        document_ids: selectedDocumentIds.length ? selectedDocumentIds : undefined,
      });
      if (!conversationId) onConversationCreated(response.conversation_id);
      onMessagesChange([
        ...nextMessages,
        {
          id: response.message_id,
          conversation_id: response.conversation_id,
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          latency_ms: response.latency_ms,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSending(false);
    }
  };

  const submitFeedback = async (messageId: string, rating: 1 | -1) => {
    setFeedback((current) => ({ ...current, [messageId]: rating }));
    try {
      await chatApi.feedback(messageId, rating);
    } catch (requestError) {
      setFeedback((current) => {
        const next = { ...current };
        delete next[messageId];
        return next;
      });
      setError(errorMessage(requestError));
    }
  };

  const completedDocuments = documents.filter((document) => document.status === "completed");

  return (
    <section className="flex min-h-[70vh] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-card">
      <header className="border-b border-slate-200 bg-white px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-brand-50 p-2 text-brand-600">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-bold text-ink">Grounded assistant</h2>
            <p className="text-xs text-slate-500">
              Searching {selectedDocumentIds.length || completedDocuments.length} ready document
              {(selectedDocumentIds.length || completedDocuments.length) === 1 ? "" : "s"}
            </p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        {messages.length === 0 ? (
          <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center py-10 text-center">
            <div className="mb-4 rounded-2xl bg-brand-100 p-4 text-brand-700">
              <Sparkles className="h-7 w-7" />
            </div>
            <h2 className="text-2xl font-bold text-ink">Ask your documents</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
              Answers are limited to retrieved evidence and include page-level source links.
            </p>
            <div className="mt-6 grid w-full gap-2">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setQuestion(suggestion)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                feedback={feedback[message.id]}
                onFeedback={submitFeedback}
              />
            ))}
            {sending && (
              <div className="flex items-center gap-3 text-sm text-slate-500">
                <div className="rounded-lg bg-brand-600 p-2 text-white">
                  <Bot className="h-4 w-4" />
                </div>
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Retrieving evidence and drafting an answer…
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={sendQuestion} className="border-t border-slate-200 bg-white p-4">
        {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
        <div className="flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void sendQuestion();
              }
            }}
            rows={1}
            placeholder={
              completedDocuments.length
                ? "Ask a question about your documents…"
                : "Upload and process a PDF before asking…"
            }
            disabled={!completedDocuments.length || sending}
            className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!question.trim() || !completedDocuments.length || sending}
            className="rounded-lg bg-brand-600 p-2.5 text-white transition hover:bg-brand-700 disabled:bg-slate-300"
            aria-label="Send question"
          >
            {sending ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-slate-400">
          Verify important details against the cited pages.
        </p>
      </form>
    </section>
  );
}
