<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="app-header">
      <div class="header-content">
        <div class="logo-section">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 4L36 12V28L20 36L4 28V12L20 4Z" stroke="currentColor" stroke-width="2" fill="none"/>
              <path d="M20 8L32 14V26L20 34L8 26V14L20 8Z" fill="currentColor" opacity="0.3"/>
              <circle cx="20" cy="20" r="6" fill="currentColor"/>
            </svg>
          </div>
          <div class="logo-text">
            <span class="logo-title">墨 · 影</span>
            <span class="logo-subtitle">字幕工坊</span>
          </div>
        </div>
        <div class="header-right">
          <a-menu
            theme="dark"
            mode="horizontal"
            :selectedKeys="selectedKeys"
            @click="handleMenuClick"
            class="main-menu"
          >
            <a-menu-item key="/">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
              </template>
              <span>文本库</span>
            </a-menu-item>
            <a-menu-item key="/discovery">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="7"/>
                  <path d="M21 21l-4.35-4.35"/>
                  <path d="M8 11h6"/>
                  <path d="M11 8v6"/>
                </svg>
              </template>
              <span>热点采集</span>
            </a-menu-item>
            <a-menu-item key="/voice-workflows">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18V5l12-2v13"/>
                  <circle cx="6" cy="18" r="3"/>
                  <circle cx="18" cy="16" r="3"/>
                </svg>
              </template>
              <span>配音工作台</span>
            </a-menu-item>
            <a-menu-item key="/novels">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
              </template>
              <span>剧情续写</span>
            </a-menu-item>
          </a-menu>
          <a-tooltip title="设置">
            <a-button type="text" class="settings-btn" @click="openDefaultSettings">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </template>
            </a-button>
          </a-tooltip>
        </div>
        <SettingsDrawer v-model:open="settingsOpen" :initial-tab="settingsInitialTab" />
      </div>
    </a-layout-header>
    <a-layout-content class="app-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SettingsDrawer from './components/settings/SettingsDrawer.vue'

const router = useRouter()
const route = useRoute()

const settingsOpen = ref(false)
const settingsInitialTab = ref('providers')

const handleOpenSettings = (event) => {
  settingsInitialTab.value = event?.detail?.tab || 'providers'
  settingsOpen.value = true
}

const openDefaultSettings = () => {
  settingsInitialTab.value = 'providers'
  settingsOpen.value = true
}

onMounted(() => {
  window.addEventListener('open-settings', handleOpenSettings)
})

onUnmounted(() => {
  window.removeEventListener('open-settings', handleOpenSettings)
})

const selectedKeys = computed(() => {
  if (route.path.startsWith('/discovery')) return ['/discovery']
  if (route.path.startsWith('/voice-workflows')) return ['/voice-workflows']
  if (route.path.startsWith('/novels')) return ['/novels']
  if (route.path === '/' || route.path.startsWith('/edit')) return ['/']
  return [route.path]
})

const handleMenuClick = ({ key }) => {
  router.push(key)
}
</script>

<style scoped>
.app-header {
  background: rgba(247, 247, 245, 0.86) !important;
  border-bottom: 1px solid var(--surface-border);
  box-shadow: none;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(16px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-lg);
  height: 64px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--text-primary);
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 650;
  color: var(--text-primary);
  letter-spacing: 0;
}

.logo-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0;
  margin-top: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.main-menu {
  border: none !important;
  line-height: 62px;
}

.main-menu :deep(.ant-menu-item) {
  padding: 0 16px !important;
  font-size: 14px;
  letter-spacing: 0;
}

.main-menu :deep(.ant-menu-item svg) {
  width: 18px;
  height: 18px;
  margin-right: 8px;
  vertical-align: -3px;
}

.settings-btn {
  color: var(--text-secondary);
}

.settings-btn:hover {
  color: var(--text-primary);
}

.settings-btn svg {
  width: 18px;
  height: 18px;
}

.app-content {
  padding: 0;
  min-height: calc(100vh - 64px);
  background: var(--paper);
}

/* Page Transitions */
.page-enter-active {
  animation: pageEnter 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.page-leave-active {
  animation: pageLeave 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes pageEnter {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pageLeave {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}
</style>
