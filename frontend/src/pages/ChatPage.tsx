import { useEffect, useState } from "react";
import {
  Check,
  FileText,
  LoaderCircle,
  MessageSquarePlus,
  MessagesSquare,
  Trash2,
} from "lucide-react";
import { conversationApi, errorMessage } from "../api/client";
import { ChatWindow } from "../components/ChatWindow";
import type { ChatMessage, Conversation, DocumentRecord } from "../types";

interface Props {
  documents: DocumentRecord[];
}

export function ChatPage({ documents }: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState("");

  const completedDocuments = documents.filter((document) => document.status === "completed");

  const loadConversations = async () => {
    try {
      setConversations(await conversationApi.list());
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  };

  useEffect(() => {
    void loadConversations();
  }, []);

  // Drop selections that no longer point at a completed document
  // (e.g. the document was deleted on the Documents page).
  useEffect(() => {
    setSelectedDocumentIds((current) => {
      const next = current.filter((id) =>
        documents.some(
          (document) => document.id === id && document.status === "completed",
        ),
      );
      return next.length === current.length ? current : next;
    });
  }, [documents]);

  const openConversation = async (id: string) => {
    setActiveId(id);
    setLoadingMessages(true);
    setError("");
    try {
      setMessages(await conversationApi.messages(id));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoadingMessages(false);
    }
  };

  const newConversation = () => {
    setActiveId(null);
    setMessages([]);
    setError("");
  };

  const removeConversation = async (id: string) => {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await conversationApi.remove(id);
      setConversations((current) => current.filter((item) => item.id !== id));
      if (activeId === id) newConversation();
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  };

  const toggleDocument = (id: string) => {
    setSelectedDocumentIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  return (
    <div>
      <div className="mb-7">
        <p className="text-sm font-semibold text-brand-600">Evidence-first answers</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Chat</h1>
        <p className="mt-2 text-sm text-slate-500">
          Ask questions across all documents or select a focused set.
        </p>
      </div>

      {error && <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <div className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <section className="rounded-xl border border-slate-200 bg-white p-3">
            <button
              onClick={newConversation}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <MessageSquarePlus className="h-4 w-4" />
              New conversation
            </button>
            <div className="mt-3 max-h-56 space-y-1 overflow-y-auto">
              {conversations.length === 0 ? (
                <p className="px-2 py-5 text-center text-xs text-slate-400">No conversation history</p>
              ) : (
                conversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className={`group flex items-center rounded-lg ${
                      activeId === conversation.id ? "bg-brand-50" : "hover:bg-slate-50"
                    }`}
                  >
                    <button
                      onClick={() => void openConversation(conversation.id)}
                      className={`min-w-0 flex-1 truncate px-2.5 py-2 text-left text-xs font-medium ${
                        activeId === conversation.id ? "text-brand-700" : "text-slate-600"
                      }`}
                    >
                      <MessagesSquare className="mr-1.5 inline h-3.5 w-3.5" />
                      {conversation.title || "Untitled conversation"}
                    </button>
                    <button
                      onClick={() => void removeConversation(conversation.id)}
                      aria-label="Delete conversation"
                      className="p-2 text-slate-400 opacity-0 hover:text-red-600 group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-slate-500">
                <FileText className="h-3.5 w-3.5" />
                Search scope
              </h2>
              {selectedDocumentIds.length > 0 && (
                <button
                  onClick={() => setSelectedDocumentIds([])}
                  className="text-[11px] font-semibold text-brand-600"
                >
                  Use all
                </button>
              )}
            </div>
            <p className="mb-2 text-[11px] leading-4 text-slate-400">
              {selectedDocumentIds.length === 0
                ? "All ready documents are selected."
                : `${selectedDocumentIds.length} document(s) selected.`}
            </p>
            <div className="max-h-48 space-y-1 overflow-y-auto">
              {completedDocuments.map((document) => {
                const selected = selectedDocumentIds.includes(document.id);
                return (
                  <button
                    key={document.id}
                    onClick={() => toggleDocument(document.id)}
                    className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs ${
                      selected ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <span
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                        selected ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300"
                      }`}
                    >
                      {selected && <Check className="h-3 w-3" />}
                    </span>
                    <span className="truncate">{document.title}</span>
                  </button>
                );
              })}
            </div>
          </section>
        </aside>

        {loadingMessages ? (
          <div className="flex min-h-[70vh] items-center justify-center rounded-2xl border border-slate-200 bg-white">
            <LoaderCircle className="h-7 w-7 animate-spin text-brand-600" />
          </div>
        ) : (
          <ChatWindow
            conversationId={activeId}
            messages={messages}
            documents={documents}
            selectedDocumentIds={selectedDocumentIds}
            onMessagesChange={setMessages}
            onConversationCreated={(id) => {
              setActiveId(id);
              void loadConversations();
            }}
          />
        )}
      </div>
    </div>
  );
}
