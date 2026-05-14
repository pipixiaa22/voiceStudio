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
          <a-menu-item key="/import">
            <template #icon>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </template>
            <span>导入</span>
          </a-menu-item>
        </a-menu>
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
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const selectedKeys = computed(() => [route.path])

const handleMenuClick = ({ key }) => {
  router.push(key)
}
</script>

<style scoped>
.app-header {
  background: linear-gradient(180deg, var(--ink-deep) 0%, var(--ink-black) 100%) !important;
  border-bottom: 1px solid var(--surface-border);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(20px);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-xl);
  height: 64px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.logo-icon {
  width: 40px;
  height: 40px;
  color: var(--gold);
  filter: drop-shadow(0 0 10px var(--gold-glow));
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--gold);
  letter-spacing: 4px;
  text-shadow: 0 0 30px var(--gold-glow);
}

.logo-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 6px;
  margin-top: 2px;
}

.main-menu {
  border: none !important;
  line-height: 62px;
}

.main-menu :deep(.ant-menu-item) {
  padding: 0 20px !important;
  font-size: 14px;
  letter-spacing: 1px;
}

.main-menu :deep(.ant-menu-item svg) {
  width: 18px;
  height: 18px;
  margin-right: 8px;
  vertical-align: -3px;
}

.app-content {
  padding: var(--space-2xl);
  min-height: calc(100vh - 64px);
  background: radial-gradient(
    ellipse at 50% 0%,
    rgba(212, 168, 83, 0.03) 0%,
    transparent 60%
  );
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
