<template>
  <div class="app-wrapper">
    <!-- 主题切换悬浮按钮 -->
    <el-button 
      class="theme-toggle-btn" 
      circle 
      size="large"
      @click="toggleTheme"
    >
      {{ isDark ? '🌙' : '☀️' }}
    </el-button>

    <!-- 路由页面展示区 -->
    <router-view></router-view>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const isDark = ref(false)

// 切换暗黑/明亮主题
const toggleTheme = () => {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// 默认跟随系统的亮暗模式
onMounted(() => {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
})
</script>

<style scoped>
.app-wrapper {
  width: 100vw;
  height: 100vh;
  position: relative;
  /* 使用 CSS 变量让背景色平滑过渡 */
  background-color: var(--el-bg-color-page); 
  color: var(--el-text-color-primary);
  transition: background-color 0.3s, color 0.3s;
}

.theme-toggle-btn {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  font-size: 20px;
}
</style>