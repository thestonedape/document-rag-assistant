import { useRef, useState, type DragEvent } from "react";
import { FileUp, LoaderCircle, UploadCloud } from "lucide-react";
import { documentApi, errorMessage } from "../api/client";
import type { DocumentRecord } from "../types";

interface Props {
  onUploaded: (documentId: string) => void;
}

// Must match the backend MAX_PDF_SIZE_MB (10 on the Render free tier).
const MAX_PDF_SIZE_MB = Number(import.meta.env.VITE_MAX_PDF_SIZE_MB ?? 25);

export function DocumentUpload({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const chooseFile = (next: File | undefined) => {
    setError("");
    if (!next) return;
    if (next.type !== "application/pdf" && !next.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    if (next.size > MAX_PDF_SIZE_MB * 1024 * 1024) {
      setError(`PDF exceeds the ${MAX_PDF_SIZE_MB} MB limit.`);
      return;
    }
    setFile(next);
    if (!title) setTitle(next.name.replace(/\.pdf$/i, ""));
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const response = await documentApi.upload(file, title);
      onUploaded(response.document_id);
      setFile(null);
      setTitle("");
      if (inputRef.current) inputRef.current.value = "";
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setUploading(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <div className="mb-5">
        <p className="text-sm font-semibold text-brand-600">Add knowledge</p>
        <h2 className="mt-1 text-xl font-bold text-ink">Upload a PDF</h2>
        <p className="mt-1 text-sm text-slate-500">
          Text is indexed page by page so every answer can point back to its source.
        </p>
      </div>

      <div
        className={`flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 text-center transition ${
          dragging
            ? "border-brand-500 bg-brand-50"
            : "border-slate-300 bg-slate-50 hover:border-brand-400 hover:bg-brand-50/50"
        }`}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(event) => chooseFile(event.target.files?.[0])}
        />
        {file ? (
          <>
            <FileUp className="mb-3 h-9 w-9 text-brand-600" />
            <p className="max-w-full truncate font-semibold text-slate-800">{file.name}</p>
            <p className="mt-1 text-xs text-slate-500">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </>
        ) : (
          <>
            <UploadCloud className="mb-3 h-9 w-9 text-brand-600" />
            <p className="font-semibold text-slate-800">Drop a PDF here</p>
            <p className="mt-1 text-sm text-slate-500">or click to browse</p>
          </>
        )}
      </div>

      <label className="mt-4 block text-sm font-medium text-slate-700">
        Document title
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Optional custom title"
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
      </label>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <button
        onClick={upload}
        disabled={!file || uploading}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-3 font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {uploading ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <FileUp className="h-5 w-5" />}
        {uploading ? "Uploading…" : "Upload and process"}
      </button>
    </section>
  );
}
