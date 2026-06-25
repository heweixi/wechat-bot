import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

// ── TypeScript 接口 ──

export interface AIProvider {
  id: string
  name: string
  provider_type: string
  has_key: boolean
  base_url: string
  model: string
  system_prompt: string
  temperature: number
  max_tokens: number
  is_default: boolean
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface Contact {
  id: string
  wx_id: string
  nickname: string
  remark: string
  is_group: boolean
  avatar: string
  ai_provider_id: string | null
  auto_reply: boolean
  tags: string[]
  created_at: string
  updated_at: string
  conversation_count: number
}

export interface ConversationSummary {
  id: string
  contact_id: string
  title: string
  ai_provider_name: string
  message_count: number
  created_at: string
  updated_at: string
  contact_name: string
  contact_wx_id: string
}

export interface MessageItem {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  raw_content: string
  ai_model: string
  tokens_used: number
  cost: number
  created_at: string
}

export interface WeChatStatus {
  logged_in: boolean
  connected: boolean
  bridge_type: 'itchat' | 'mock' | null
  qrcode_available: boolean
  qrcode_age?: number
  qrcode_expired?: boolean
}

// ── AI Providers ──
export const providerApi = {
  list: (): Promise<AIProvider[]> => http.get('/providers').then(r => r.data),
  get: (id: string): Promise<AIProvider> => http.get(`/providers/${id}`).then(r => r.data),
  create: (data: Partial<AIProvider>): Promise<AIProvider> => http.post('/providers', data).then(r => r.data),
  update: (id: string, data: Partial<AIProvider>): Promise<AIProvider> => http.put(`/providers/${id}`, data).then(r => r.data),
  remove: (id: string): Promise<void> => http.delete(`/providers/${id}`).then(r => r.data),
}

// ── Contacts ──
export const contactApi = {
  list: (params?: { search?: string; group_only?: boolean; page?: number; page_size?: number }): Promise<Contact[]> =>
    http.get('/contacts', { params }).then(r => r.data),
  get: (id: string): Promise<Contact> => http.get(`/contacts/${id}`).then(r => r.data),
  setAi: (id: string, aiProviderId: string | null): Promise<void> =>
    http.put(`/contacts/${id}/ai`, { ai_provider_id: aiProviderId }).then(r => r.data),
  setAutoReply: (id: string, autoReply: boolean): Promise<void> =>
    http.put(`/contacts/${id}/auto_reply`, { auto_reply: autoReply }).then(r => r.data),
}

// ── Conversations ──
export const conversationApi = {
  list: (params?: { search?: string; contact_id?: string; page?: number; page_size?: number }): Promise<ConversationSummary[]> =>
    http.get('/conversations', { params }).then(r => r.data),
  get: (id: string): Promise<{ conversation: ConversationSummary; messages: MessageItem[] }> =>
    http.get(`/conversations/${id}`).then(r => r.data),
  remove: (id: string): Promise<void> => http.delete(`/conversations/${id}`).then(r => r.data),
  searchMessages: (params: { keyword: string; contact_id?: string; role?: string }): Promise<MessageItem[]> =>
    http.get('/conversations/search/messages', { params }).then(r => r.data),
}

// ── WeChat ──
export const wechatApi = {
  status: (): Promise<WeChatStatus> => http.get('/wechat/status').then(r => r.data),
  login: (): Promise<{ ok: boolean; message: string }> => http.post('/wechat/login').then(r => r.data),
  refreshQrcode: (): Promise<{ ok: boolean }> => http.post('/wechat/refresh-qrcode').then(r => r.data),
  qrcodeUrl: (): string => `/api/wechat/qrcode?t=${Date.now()}`,
}
