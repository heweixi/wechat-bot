import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

// ── AI Providers ──
export const providerApi = {
  list: () => http.get('/providers').then(r => r.data),
  create: (data: any) => http.post('/providers', data).then(r => r.data),
  update: (id: string, data: any) => http.put(`/providers/${id}`, data).then(r => r.data),
  remove: (id: string) => http.delete(`/providers/${id}`).then(r => r.data),
}

// ── Contacts ──
export const contactApi = {
  list: (params?: any) => http.get('/contacts', { params }).then(r => r.data),
  get: (id: string) => http.get(`/contacts/${id}`).then(r => r.data),
  setAi: (id: string, aiProviderId: string | null) =>
    http.put(`/contacts/${id}/ai`, { ai_provider_id: aiProviderId }).then(r => r.data),
  setAutoReply: (id: string, autoReply: boolean) =>
    http.put(`/contacts/${id}/auto_reply`, { auto_reply: autoReply }).then(r => r.data),
}

// ── Conversations ──
export const conversationApi = {
  list: (params?: any) => http.get('/conversations', { params }).then(r => r.data),
  get: (id: string) => http.get(`/conversations/${id}`).then(r => r.data),
  remove: (id: string) => http.delete(`/conversations/${id}`).then(r => r.data),
  searchMessages: (params: any) =>
    http.get('/conversations/search/messages', { params }).then(r => r.data),
}
