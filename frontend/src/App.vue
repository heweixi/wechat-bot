<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="background: #304156">
      <div style="padding: 20px; color: #fff; font-size: 18px; font-weight: bold; text-align: center">
        🤖 微信机器人
      </div>
      <el-menu
        :default-active="route.path"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/">
          <el-icon><ChatDotSquare /></el-icon>
          <span>联系人</span>
        </el-menu-item>
        <el-menu-item index="/conversations">
          <el-icon><Message /></el-icon>
          <span>会话记录</span>
        </el-menu-item>
        <el-menu-item index="/providers">
          <el-icon><Setting /></el-icon>
          <span>AI 配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background: #fff; border-bottom: 1px solid #dcdfe6; display: flex; align-items: center; justify-content: space-between">
        <h2 style="margin: 0; font-size: 16px">{{ route.meta.title || '微信机器人' }}</h2>
        <div>
          <el-button v-if="showStartBtn" type="primary" size="small" :icon="Refresh" @click="startBridge" :loading="starting">
            启动桥接
          </el-button>
          <el-tag :type="statusTagType" size="small" style="margin-left: 8px">
            {{ statusText }}
          </el-tag>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { wechatApi, type WeChatStatus } from './api'

const route = useRoute()
const wechatStatus = ref<WeChatStatus>({ logged_in: false, connected: false, bridge_type: null })
let pollTimer: any = null

const showStartBtn = computed(() =>
  !wechatStatus.value.connected && !wechatStatus.value.logged_in
)

const starting = ref(false)

async function startBridge() {
  starting.value = true
  try {
    await wechatApi.login()
    setTimeout(pollStatus, 3000)
  } catch { /* ignore */ }
  finally { starting.value = false }
}

const statusTagType = computed(() => {
  if (starting.value) return 'warning'
  if (!wechatStatus.value.connected) return 'info'
  if (wechatStatus.value.logged_in) return 'success'
  return 'warning'
})

const statusText = computed(() => {
  if (starting.value) return '启动中...'
  if (!wechatStatus.value.connected) return '未连接'
  if (wechatStatus.value.logged_in) {
    const t = wechatStatus.value.bridge_type
    return t === 'wkteam' ? '微信已连接 (iPad)' : t === 'mock' ? '模拟模式' : '已连接'
  }
  return '等待连接...'
})

async function pollStatus() {
  try {
    wechatStatus.value = await wechatApi.status()
  } catch { /* ignore */ }
}

onMounted(() => {
  pollStatus()
  pollTimer = setInterval(pollStatus, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
