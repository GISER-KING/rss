import { AuthResponse, User } from "@/types";

const API_BASE_URL = "http://localhost:8006";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: HeadersInit = {
    // "Content-Type": "application/json",  <-- Removed default here
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  // Default content type if not specified and body is string
  if (!headers["Content-Type"] && typeof options.body === "string" && !options.body.includes("username=")) {
       // @ts-ignore
       headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    const errorMessage = typeof error.detail === 'string' 
      ? error.detail 
      : JSON.stringify(error.detail || error);
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  login: (data: any) => request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
    headers: { "Content-Type": "application/json" }
  }),
  
  updateConfig: (data: any) => request<User>("/auth/config", {
    method: "POST",
    body: JSON.stringify(data)
  }),

  uploadPdf: async (userId: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("token");
    const response = await fetch(`${API_BASE_URL}/upload/pdf?user_id=${userId}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!response.ok) throw new Error("Upload failed");
    return response.json();
  },

  getConversations: (userId: number) => request<any[]>(`/chat/conversations?user_id=${userId}`),
  
  getMessages: (conversationId: number) => request<any[]>(`/chat/conversations/${conversationId}/messages`),

  deleteConversation: (id: number) => request<{ ok: boolean }>(`/chat/conversations/${id}`, {
    method: "DELETE"
  }),

  updateConversationTitle: (id: number, title: string) => request<{ id: number; title: string }>(`/chat/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ title })
  }),

  sendMessage: (data: { user_id: number; conversation_id?: number; content: string; mode?: "chat" | "agent" }) => 
    request<{ conversation_id: number; message_id: number }>("/chat/send", {
      method: "POST",
      body: JSON.stringify(data)
    }),
};

export const SSE_URL = `${API_BASE_URL}/chat/stream`;
