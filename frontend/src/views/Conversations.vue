<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-input v-model="search" placeholder="搜索会话内容" clearable @input="loadList">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </el-col>
      <el-col :span="6">
        <el-select v-model="contactFilter" placeholder="按联系人筛选" clearable filterable @change="loadList">
          <el-option v-for="c in contacts" :key="c.id" :label="c.nickname || c.wx_id" :value="c.id" />
        </el-select>
      </el-col>
      <el-col :span="6" style="text-align: right">
        <el-button :icon="Refresh" @click="loadList">刷新</el-button>
      </el-col>
    </el-row>

    <el-table :data="conversations" v-loading="loading" stripe @row-click="goDetail" style="cursor: pointer">
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column label="联系人" min-width="140">
        <template #default="{ row }">
          <el-tag>{{ row.contact_id?.slice(0, 8) }}...</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="AI 配置" width="120">
        <template #default="{ row }">{{ row.ai_provider_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="message_count" label="消息数" width="80" />
      <el-table-column label="预览" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.messages?.slice(-1)?.[0]?.content?.slice(0, 60) || '' }}
        </template>
      </el-table-column>
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column width="60">
        <template #default="{ row }">
          <el-popconfirm title="确认删除?" @confirm="removeConv(row.id)">
            <template #reference>
              <el-button text type="danger" :icon="Delete" @click.stop />
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Search, Delete } from '@element-plus/icons-vue'
import { conversationApi, contactApi } from '../api'

const router = useRouter()
const search = ref('')
const contactFilter = ref('')
const loading = ref(false)
const conversations = ref<any[]>([])
const contacts = ref<any[]>([])

onMounted(async () => {
  contacts.value = await contactApi.list()
  loadList()
})

async function loadList() {
  loading.value = true
  try {
    conversations.value = await conversationApi.list({
      search: search.value,
      contact_id: contactFilter.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

function goDetail(row: any) {
  router.push(`/conversations/${row.id}`)
}

async function removeConv(id: string) {
  await conversationApi.remove(id)
  loadList()
}

function formatTime(t: string) {
  return t?.slice(0, 16).replace('T', ' ')
}
</script>
