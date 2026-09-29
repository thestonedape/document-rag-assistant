import { useEffect, useState } from "react";
import { BookOpenText, FileStack, MessageSquareText } from "lucide-react";
import { documentApi } from "./api/client";
import { ChatPage } from "./pages/ChatPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import type { DocumentRecord } from "./types";

type Page = "documents" | "chat";

export default function App() {
  const [page, setPage] = useState<Page>("documents");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);

  useEffect(() => {
    void documentApi.list().then(setDocuments).catch(() => undefined);
  }, []);

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <button onClick={() => setPage("documents")} className="flex items-center gap-3 text-left">
            <span className="rounded-xl bg-brand-600 p-2.5 text-white shadow-sm">
              <BookOpenText className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-sm font-bold leading-tight text-ink">Document Intelligence</span>
              <span className="hidden text-[11px] text-slate-500 sm:block">Grounded RAG workspace</span>
            </span>
          </button>

          <nav className="flex items-center rounded-xl bg-slate-100 p-1 lg:hidden">
            <button
              onClick={() => setPage("documents")}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                page === "documents" ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <FileStack className="h-4 w-4" />
              <span className="hidden sm:inline">Documents</span>
            </button>
            <button
              onClick={() => setPage("chat")}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                page === "chat" ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <MessageSquareText className="h-4 w-4" />
              <span className="hidden sm:inline">Chat</span>
            </button>
          </nav>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl lg:grid-cols-[210px_minmax(0,1fr)]">
        <aside className="sticky top-[65px] hidden h-[calc(100vh-65px)] border-r border-slate-200 px-4 py-7 lg:block">
          <p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">
            Workspace
          </p>
          <nav className="space-y-1">
            <button
              onClick={() => setPage("documents")}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                page === "documents"
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-500 hover:bg-white hover:text-slate-800"
              }`}
            >
              <FileStack className="h-4 w-4" />
              Documents
            </button>
            <button
              onClick={() => setPage("chat")}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                page === "chat"
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-500 hover:bg-white hover:text-slate-800"
              }`}
            >
              <MessageSquareText className="h-4 w-4" />
              Chat
            </button>
          </nav>
          <div className="mt-8 rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-xs font-semibold text-slate-700">Knowledge status</p>
            <p className="mt-1 text-2xl font-bold text-brand-700">
              {documents.filter((document) => document.status === "completed").length}
            </p>
            <p className="text-[11px] text-slate-400">documents ready to search</p>
          </div>
        </aside>

        <main className="min-w-0 px-4 py-8 sm:px-6 lg:px-8">
          {page === "documents" ? (
            <DocumentsPage documents={documents} setDocuments={setDocuments} />
          ) : (
            <ChatPage documents={documents} />
          )}
        </main>
      </div>
    </div>
  );
}
