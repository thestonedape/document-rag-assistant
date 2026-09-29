import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { documentApi, errorMessage } from "../api/client";
import { DocumentList } from "../components/DocumentList";
import { DocumentUpload } from "../components/DocumentUpload";
import type { DocumentRecord } from "../types";

interface Props {
  documents: DocumentRecord[];
  setDocuments: (documents: DocumentRecord[]) => void;
}

export function DocumentsPage({ documents, setDocuments }: Props) {
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      setDocuments(await documentApi.list());
      setError("");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!documents.some((document) => document.status === "processing")) return;
    const timer = window.setInterval(() => void load(true), 3000);
    return () => window.clearInterval(timer);
  }, [documents]);

  const remove = async (document: DocumentRecord) => {
    if (!window.confirm(`Delete “${document.title}” and all of its indexed content?`)) return;
    setDeletingId(document.id);
    try {
      await documentApi.remove(document.id);
      setDocuments(documents.filter((item) => item.id !== document.id));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-brand-600">Knowledge base</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Documents</h1>
          <p className="mt-2 text-sm text-slate-500">
            Upload searchable PDFs and track their indexing status.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:border-brand-300 hover:text-brand-600"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-[minmax(280px,0.8fr)_minmax(420px,1.2fr)]">
        <DocumentUpload
          onUploaded={() => void load()}
        />
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-ink">Library</h2>
            <span className="text-xs font-medium text-slate-500">{documents.length} total</span>
          </div>
          <DocumentList
            documents={documents}
            loading={loading}
            deletingId={deletingId}
            onDelete={remove}
          />
        </section>
      </div>
    </div>
  );
}
