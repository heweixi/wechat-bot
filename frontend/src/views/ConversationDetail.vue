<template>
  <div>
    <el-button text :icon="ArrowLeft" @click="$router.back()" style="margin-bottom: 12px">返回</el-button>

    <el-card v-if="conv" style="margin-bottom: 16px">
      <template #header>
        <span>{{ conv.title }}</span>
        <el-tag style="margin-left: 8px" size="small">{{ conv.ai_provider_name }}</el-tag>
      </template>
    </el-card>

    <div class="message-list" ref="msgListRef">
      <div v-for="msg in messages" :key="msg.id" class="message-item"
        :class="{ 'message-user': msg.role === 'user', 'message-ai': msg.role === 'assistant' }">
        <div class="message-role">
          <el-tag :type="msg.role === 'user' ? 'info' : 'success'" size="small" round>
            {{ msg.role === 'user' ? '我' : 'AI' }}
          </el-tag>
        </div>
        <div class="message-content">{{ msg.content }}</div>
        <div class="message-meta" v-if="msg.ai_model">
          <small>{{ msg.ai_model }} · {{ msg.created_at?.slice(0, 16).replace('T', ' ') }}</small>
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && messages.length === 0" description="暂无消息" />

    <el-affix position="bottom" :offset="20" style="text-align: center">
      <el-input v-model="keyword" placeholder="搜索消息内容..." clearable style="max-width: 400px; margin: 0 auto"
        @keyup.enter="searchInConv">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </el-affix>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Search } from '@element-plus/icons-vue'
import { conversationApi } from '../api'

const route = useRoute()
const conv = ref<any>(null)
const messages = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const msgListRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  loading.value = true
  try {
    const data = await conversationApi.get(route.params.id as string)
    conv.value = data
    messages.value = data.messages || []
  } finally {
    loading.value = false
  }
})

async function searchInConv() {
  if (!keyword.value) return
  const results = await conversationApi.searchMessages({
    keyword: keyword.value,
  })
  messages.value = results
}
</script>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 80px;
}
.message-item {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 8px;
}
.message-user {
  align-self: flex-start;
  background: #f0f0f0;
}
.message-ai {
  align-self: flex-end;
  background: #e6f7ff;
}
.message-role {
  margin-bottom: 4px;
}
.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}
.message-meta {
  margin-top: 4px;
  opacity: 0.6;
}
</style>
