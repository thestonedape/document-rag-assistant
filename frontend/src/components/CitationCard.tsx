import { ExternalLink, FileText } from "lucide-react";
import type { Citation } from "../types";

export function CitationCard({ citation }: { citation: Citation }) {
  const content = (
    <>
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-700">
          <FileText className="h-3.5 w-3.5" />
          [{citation.source_id}]
        </span>
        <span className="text-xs text-slate-500">
          Page {citation.page_number} · {Math.round(citation.similarity * 100)}%
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold text-slate-800">{citation.document_title}</p>
      <p className="mt-1 line-clamp-3 text-xs leading-5 text-slate-600">{citation.text}</p>
    </>
  );

  return citation.source_url ? (
    <a
      href={`${citation.source_url}#page=${citation.page_number}`}
      target="_blank"
      rel="noreferrer"
      className="block rounded-xl border border-slate-200 bg-white p-3 transition hover:border-brand-300 hover:shadow-sm"
    >
      {content}
      <span className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-600">
        Open source <ExternalLink className="h-3 w-3" />
      </span>
    </a>
  ) : (
    <div className="rounded-xl border border-slate-200 bg-white p-3">{content}</div>
  );
}
