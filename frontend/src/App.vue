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
        <el-tag :type="status.online ? 'success' : 'danger'" size="small">
          {{ status.online ? '微信已连接' : '微信未连接' }}
        </el-tag>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const status = ref({ online: false })

onMounted(async () => {
  try {
    const res = await axios.get('/api/status')
    status.value.online = res.data.wechat_logged_in
  } catch { /* ignore */ }
})
</script>
