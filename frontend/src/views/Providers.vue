<template>
  <div>
    <el-row style="margin-bottom: 16px">
      <el-col :span="12">
        <el-button type="primary" :icon="Plus" @click="showDialog = true">添加 AI 配置</el-button>
      </el-col>
    </el-row>

    <el-table :data="providers" v-loading="loading" stripe>
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="provider_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.provider_type === 'openai' ? 'primary' : 'warning'" size="small">
            {{ { openai: 'OpenAI', claude: 'Claude', custom: '自定义' }[row.provider_type] || row.provider_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="model" label="模型" width="180" />
      <el-table-column prop="base_url" label="API 地址" min-width="200" show-overflow-tooltip />
      <el-table-column label="默认" width="70">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="70">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="(v: boolean) => toggleEnabled(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button text type="primary" @click="editProvider(row)">编辑</el-button>
          <el-popconfirm title="确认删除?" @confirm="deleteProvider(row.id)">
            <template #reference>
              <el-button text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="editing ? '编辑 AI 配置' : '添加 AI 配置'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：我的 OpenAI" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.provider_type">
            <el-option label="OpenAI 兼容" value="openai" />
            <el-option label="Anthropic Claude" value="claude" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password
            :placeholder="editing ? '留空则保持不变' : 'sk-...'" />
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input v-model="form.base_url" placeholder="如：https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="form.model" placeholder="如：gpt-4o-mini" />
        </el-form-item>
        <el-form-item label="System Prompt">
          <el-input v-model="form.system_prompt" type="textarea" :rows="3"
            placeholder="角色设定提示词（可选）" />
        </el-form-item>
        <el-form-item label="温度">
          <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="最大Token">
          <el-input-number v-model="form.max_tokens" :min="256" :max="8192" :step="256" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProvider" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { providerApi } from '../api'

const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editing = ref(false)
const providers = ref<any[]>([])

const emptyForm = () => ({
  name: '',
  provider_type: 'openai',
  api_key: '',
  base_url: '',
  model: '',
  system_prompt: '',
  temperature: 0.7,
  max_tokens: 2048,
  is_default: false,
})

const form = reactive(emptyForm())

onMounted(() => loadProviders())

async function loadProviders() {
  loading.value = true
  try {
    providers.value = await providerApi.list()
  } finally {
    loading.value = false
  }
}

function editProvider(row: any) {
  editing.value = true
  Object.assign(form, { ...row })
  showDialog.value = true
}

async function saveProvider() {
  saving.value = true
  try {
    if (editing.value) {
      await providerApi.update(form.id, form)
    } else {
      await providerApi.create({ ...form })
    }
    showDialog.value = false
    loadProviders()
  } finally {
    saving.value = false
  }
}

async function deleteProvider(id: string) {
  await providerApi.remove(id)
  loadProviders()
}

async function toggleEnabled(row: any, v: boolean) {
  await providerApi.update(row.id, { enabled: v })
  row.enabled = v
}
</script>
