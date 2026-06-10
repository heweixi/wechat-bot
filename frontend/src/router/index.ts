import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Contacts',
    component: () => import('../views/Contacts.vue'),
    meta: { title: '联系人管理' },
  },
  {
    path: '/conversations',
    name: 'Conversations',
    component: () => import('../views/Conversations.vue'),
    meta: { title: '会话记录' },
  },
  {
    path: '/conversations/:id',
    name: 'ConversationDetail',
    component: () => import('../views/ConversationDetail.vue'),
    meta: { title: '会话详情' },
  },
  {
    path: '/providers',
    name: 'Providers',
    component: () => import('../views/Providers.vue'),
    meta: { title: 'AI 配置管理' },
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
