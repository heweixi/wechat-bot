<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-input v-model="search" placeholder="搜索昵称/备注/微信号" clearable @input="loadContacts">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </el-col>
      <el-col :span="6">
        <el-switch v-model="groupOnly" active-text="仅群聊" @change="loadContacts" />
      </el-col>
      <el-col :span="6" style="text-align: right">
        <el-button type="primary" :icon="Refresh" @click="loadContacts">刷新</el-button>
      </el-col>
    </el-row>

    <el-table :data="contacts" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="nickname" label="昵称" min-width="140" />
      <el-table-column prop="remark" label="备注" min-width="120" />
      <el-table-column prop="wx_id" label="微信号" min-width="180" show-overflow-tooltip />
      <el-table-column label="群聊" width="70">
        <template #default="{ row }">
          <el-tag v-if="row.is_group" size="small">群</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="自动回复" width="100">
        <template #default="{ row }">
          <el-switch :model-value="row.auto_reply" @change="(v: boolean) => toggleAutoReply(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="AI 配置" min-width="160">
        <template #default="{ row }">
          <el-select :model-value="row.ai_provider_id" placeholder="默认" clearable size="small"
            @change="(v: string | null) => setAiProvider(row, v)">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="会话数" width="80">
        <template #default="{ row }">{{ row.conversation_count }}</template>
      </el-table-column>
      <el-table-column label="最近更新" width="160">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { contactApi, providerApi } from '../api'

const search = ref('')
const groupOnly = ref(false)
const loading = ref(false)
const contacts = ref<any[]>([])
const providers = ref<any[]>([])

onMounted(async () => {
  providers.value = await providerApi.list()
  loadContacts()
})

async function loadContacts() {
  loading.value = true
  try {
    contacts.value = await contactApi.list({ search: search.value, group_only: groupOnly.value })
  } finally {
    loading.value = false
  }
}

async function toggleAutoReply(row: any, v: boolean) {
  await contactApi.setAutoReply(row.id, v)
  row.auto_reply = v
}

async function setAiProvider(row: any, providerId: string | null) {
  await contactApi.setAi(row.id, providerId)
  row.ai_provider_id = providerId
}

function formatTime(t: string) {
  return t?.slice(0, 16).replace('T', ' ')
}
</script>
