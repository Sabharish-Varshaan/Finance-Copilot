import api from "@/services/api";
import type { ChatMessage, ChatResponse } from "@/types";

export async function sendMessage(query: string) {
  const response = await api.post<ChatResponse>("/chat", { query });
  return response.data;
}

export async function getChatHistory(limit = 50) {
  const response = await api.get<ChatMessage[]>("/chat/history", { params: { limit } });
  return response.data;
}
