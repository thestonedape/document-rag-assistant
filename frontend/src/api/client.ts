import axios from "axios";
import type {
  ChatMessage,
  ChatResponse,
  Conversation,
  DocumentRecord,
  UploadResponse,
} from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

if (import.meta.env.PROD && API_URL.includes("localhost")) {
  console.error("Production build is missing VITE_API_URL.");
}

export const api = axios.create({
  baseURL: API_URL.replace(/\/$/, ""),
  timeout: 120_000,
});

// Render's free tier spins the backend down after 15 idle minutes and
// cold starts take up to a minute. Ping /health as soon as the app
// loads so the instance is already waking while the user reads the UI.
api.get("/health", { timeout: 90_000 }).catch(() => {
  /* wake-up ping only — errors are irrelevant */
});

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item: { msg?: string }) => item.msg ?? "Invalid input").join(", ");
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}

export const documentApi = {
  list: async (): Promise<DocumentRecord[]> =>
    (await api.get<DocumentRecord[]>("/api/documents")).data,
  upload: async (file: File, title: string): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    if (title.trim()) form.append("title", title.trim());
    return (
      await api.post<UploadResponse>("/api/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
    ).data;
  },
  remove: async (id: string): Promise<void> => {
    await api.delete(`/api/documents/${id}`);
  },
};

export const conversationApi = {
  list: async (): Promise<Conversation[]> =>
    (await api.get<Conversation[]>("/api/conversations")).data,
  create: async (title = "New conversation"): Promise<Conversation> =>
    (await api.post<Conversation>("/api/conversations", { title })).data,
  messages: async (id: string): Promise<ChatMessage[]> =>
    (await api.get<ChatMessage[]>(`/api/conversations/${id}/messages`)).data,
  remove: async (id: string): Promise<void> => {
    await api.delete(`/api/conversations/${id}`);
  },
};

export interface SendChatInput {
  question: string;
  conversation_id?: string;
  document_ids?: string[];
}

export const chatApi = {
  send: async (input: SendChatInput): Promise<ChatResponse> =>
    (await api.post<ChatResponse>("/api/chat", input)).data,
  feedback: async (messageId: string, rating: 1 | -1): Promise<void> => {
    await api.post("/api/feedback", {
      message_id: messageId,
      rating: rating === 1 ? "positive" : "negative",
    });
  },
};
