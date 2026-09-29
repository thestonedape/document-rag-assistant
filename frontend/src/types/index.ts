export type DocumentStatus = "processing" | "completed" | "failed";

export interface DocumentRecord {
  id: string;
  title: string;
  original_filename: string;
  file_size: number | null;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
}

export interface Citation {
  source_id: string;
  document_id: string;
  document_title: string;
  page_number: number;
  chunk_id: string;
  text: string;
  similarity: number;
  source_url: string | null;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  latency_ms: number;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  citations: Citation[];
  latency_ms: number | null;
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  status: DocumentStatus;
  message: string;
}
