<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="header">
      <div class="logo">字幕生成器</div>
      <a-menu
        theme="dark"
        mode="horizontal"
        :selectedKeys="selectedKeys"
        @click="handleMenuClick"
      >
        <a-menu-item key="/">
          <FileTextOutlined />
          <span>文本列表</span>
        </a-menu-item>
        <a-menu-item key="/import">
          <ImportOutlined />
          <span>导入</span>
        </a-menu-item>
      </a-menu>
    </a-layout-header>
    <a-layout-content style="padding: 24px">
      <router-view />
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { FileTextOutlined, ImportOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()

const selectedKeys = computed(() => [route.path])

const handleMenuClick = ({ key }) => {
  router.push(key)
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  padding: 0 24px;
}
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
  white-space: nowrap;
}
</style>
