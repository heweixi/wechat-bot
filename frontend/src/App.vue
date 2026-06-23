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
          <el-button v-if="showScan" type="warning" size="small" :icon="ScanCode" @click="showQr = true">
            扫码登录
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

    <!-- QR 码弹窗 -->
    <el-dialog v-model="showQr" title="微信扫码登录" width="360px" :close-on-click-modal="false">
      <div style="text-align: center">
        <img :src="qrUrl" alt="微信登录二维码"
          style="width: 280px; height: 280px; border: 1px solid #dcdfe6; border-radius: 8px;"
          @error="qrError = true" />
        <p v-if="qrError" style="color: #999">
          QR 码尚未生成，请等待...
        </p>
        <p v-else style="color: #666; margin-top: 12px">
          请使用微信扫描二维码登录
        </p>
        <el-button v-if="qrError" type="primary" @click="refreshQr" :icon="Refresh" style="margin-top: 8px">
          刷新二维码
        </el-button>
      </div>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ScanCode, Refresh } from '@element-plus/icons-vue'
import { wechatApi } from './api'

const route = useRoute()
const showQr = ref(false)
const qrError = ref(false)
const wechatStatus = ref({ logged_in: false, qrcode_available: false, bridge_type: 'mock' })
let pollTimer: any = null

const showScan = computed(() =>
  !wechatStatus.value.logged_in && wechatStatus.value.bridge_type === 'itchat'
)

const statusTagType = computed(() => {
  if (!wechatStatus.value.bridge_type) return 'info'
  if (wechatStatus.value.logged_in) return 'success'
  return 'warning'
})

const statusText = computed(() => {
  if (!wechatStatus.value.bridge_type) return '未连接'
  if (wechatStatus.value.logged_in) return '微信已连接'
  return wechatStatus.value.bridge_type === 'itchat' ? '等待扫码' : '模拟模式'
})

const qrUrl = computed(() => wechatApi.qrcodeUrl())

async function pollStatus() {
  try {
    const res = await wechatApi.status()
    wechatStatus.value = res
    // 登录成功后关闭 QR 弹窗
    if (res.logged_in && showQr.value) {
      showQr.value = false
    }
  } catch { /* ignore */ }
}

function refreshQr() {
  qrError.value = false
  // 强制刷新
  wechatStatus.value.qrcode_available = false
  setTimeout(() => {
    wechatStatus.value.qrcode_available = true
  }, 500)
}

onMounted(() => {
  pollStatus()
  pollTimer = setInterval(pollStatus, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
