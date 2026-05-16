<template>
  <a-dropdown :trigger="['click']" placement="bottomRight">
    <a-button type="text" size="small" class="more-btn" @click.stop>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="1"/>
        <circle cx="19" cy="12" r="1"/>
        <circle cx="5" cy="12" r="1"/>
      </svg>
    </a-button>
    <template #overlay>
      <a-menu @click="({ key }) => $emit('action', key)">
        <a-menu-item key="add-child">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="menu-icon">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            <line x1="12" y1="11" x2="12" y2="17"/>
            <line x1="9" y1="14" x2="15" y2="14"/>
          </svg>
          创建子文件夹
        </a-menu-item>
        <a-menu-item key="rename">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="menu-icon">
            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>
          </svg>
          重命名
        </a-menu-item>
        <a-menu-divider />
        <a-menu-item key="delete" danger>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="menu-icon">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          删除文件夹
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>

<script setup>
defineEmits(['action'])
</script>

<style scoped>
.more-btn {
  color: var(--text-muted) !important;
  width: 24px;
  height: 24px;
  padding: 0 !important;
  transition: all var(--transition-fast) !important;
}

.more-btn:hover {
  color: var(--text-primary) !important;
}

.more-btn svg {
  width: 14px;
  height: 14px;
}

.menu-icon {
  width: 14px;
  height: 14px;
  margin-right: 8px;
  vertical-align: -2px;
}
</style>
