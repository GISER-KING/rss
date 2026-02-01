export interface User {
  id: number;
  username: string;
  role: string;
  api_base_url?: string;
  api_key?: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  mode: "chat" | "agent";
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  metadata?: any;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
