import { AlertCircle, CheckCircle2, FileText, LoaderCircle, Trash2 } from "lucide-react";
import type { DocumentRecord } from "../types";

interface Props {
  documents: DocumentRecord[];
  loading: boolean;
  deletingId: string | null;
  onDelete: (document: DocumentRecord) => void;
}

const statusStyle = {
  processing: "bg-amber-50 text-amber-700",
  completed: "bg-emerald-50 text-emerald-700",
  failed: "bg-red-50 text-red-700",
};

function StatusIcon({ status }: { status: DocumentRecord["status"] }) {
  if (status === "processing") return <LoaderCircle className="h-3.5 w-3.5 animate-spin" />;
  if (status === "completed") return <CheckCircle2 className="h-3.5 w-3.5" />;
  return <AlertCircle className="h-3.5 w-3.5" />;
}

export function DocumentList({ documents, loading, deletingId, onDelete }: Props) {
  if (loading && documents.length === 0) {
    return (
      <div className="flex min-h-52 items-center justify-center rounded-2xl border border-slate-200 bg-white">
        <LoaderCircle className="h-7 w-7 animate-spin text-brand-600" />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white px-6 text-center">
        <FileText className="mb-3 h-10 w-10 text-slate-300" />
        <h3 className="font-semibold text-slate-700">No documents yet</h3>
        <p className="mt-1 text-sm text-slate-500">Upload your first PDF to build the knowledge base.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((document) => (
        <article
          key={document.id}
          className="group flex items-start gap-4 rounded-xl border border-slate-200 bg-white p-4 transition hover:border-brand-200 hover:shadow-card"
        >
          <div className="rounded-lg bg-brand-50 p-2.5 text-brand-600">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate font-semibold text-slate-800">{document.title}</h3>
                <p className="mt-0.5 truncate text-xs text-slate-500">{document.original_filename}</p>
              </div>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusStyle[document.status]}`}
              >
                <StatusIcon status={document.status} />
                {document.status}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
              {document.page_count !== null && <span>{document.page_count} pages</span>}
              {document.file_size !== null && (
                <span>{(document.file_size / 1024 / 1024).toFixed(2)} MB</span>
              )}
              <span>{new Date(document.created_at).toLocaleDateString()}</span>
            </div>
            {document.error_message && (
              <p className="mt-2 rounded-md bg-red-50 px-2.5 py-2 text-xs text-red-700">
                {document.error_message}
              </p>
            )}
          </div>
          <button
            onClick={() => onDelete(document)}
            disabled={deletingId === document.id}
            aria-label={`Delete ${document.title}`}
            className="rounded-lg p-2 text-slate-400 opacity-100 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40 sm:opacity-0 sm:group-hover:opacity-100"
          >
            {deletingId === document.id ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </button>
        </article>
      ))}
    </div>
  );
}
