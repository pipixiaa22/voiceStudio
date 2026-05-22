<template>
  <div class="voice-profile-selector">
    <!-- Current Profile Card -->
    <div v-if="selectedProfile" class="current-profile" @click="showDrawer = true">
      <div class="profile-info">
        <div class="profile-header">
          <span class="profile-name">{{ selectedProfile.name }}</span>
          <a-tag v-if="selectedProfile.is_builtin" size="small">系统预设</a-tag>
          <a-tag v-else size="small" color="blue">我的音色</a-tag>
        </div>
        <p class="profile-desc">{{ selectedProfile.description || selectedProfile.raw_description }}</p>
        <div class="profile-tags">
          <span v-if="selectedProfile.gender">{{ genderLabel(selectedProfile.gender) }}</span>
          <span v-if="selectedProfile.speed">{{ speedLabel(selectedProfile.speed) }}</span>
          <span v-if="selectedProfile.emotion">{{ selectedProfile.emotion }}</span>
          <span v-if="selectedProfile.accent">{{ selectedProfile.accent }}</span>
        </div>
      </div>
      <div class="profile-actions">
        <a-button size="small" @click.stop="showDrawer = true">切换</a-button>
        <a-button size="small" @click.stop="$emit('audition', selectedProfile)">试听</a-button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="empty-profile" @click="showDrawer = true">
      <span>点击选择音色档案</span>
    </div>

    <!-- Profile Drawer -->
    <a-drawer
      v-model:open="showDrawer"
      title="选择音色"
      placement="right"
      :width="400"
      :bodyStyle="{ padding: '16px' }"
    >
      <div class="drawer-content">
        <!-- Search -->
        <a-input
          v-model:value="searchQuery"
          placeholder="搜索音色..."
          class="search-input"
          allowClear
        >
          <template #prefix>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </template>
        </a-input>

        <!-- Filter Tabs -->
        <div class="filter-tabs">
          <button
            v-for="tab in filterTabs"
            :key="tab.value"
            class="filter-tab"
            :class="{ active: activeFilter === tab.value }"
            @click="activeFilter = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Profile List -->
        <div class="profile-list">
          <div
            v-for="profile in filteredProfiles"
            :key="profile.id"
            class="profile-card"
            :class="{ selected: selectedProfile?.id === profile.id }"
            @click="handleSelect(profile)"
          >
            <div class="card-header">
              <span class="card-name">{{ profile.name }}</span>
              <a-tag v-if="profile.is_builtin" size="small">系统预设</a-tag>
              <a-tag v-else size="small" color="blue">我的音色</a-tag>
            </div>
            <p class="card-desc">{{ profile.description || profile.raw_description }}</p>
            <div class="card-tags">
              <span v-if="profile.gender">{{ genderLabel(profile.gender) }}</span>
              <span v-if="profile.speed">{{ speedLabel(profile.speed) }}</span>
              <span v-if="profile.emotion">{{ profile.emotion }}</span>
            </div>
            <div class="card-actions">
              <a-button size="small" @click.stop="$emit('audition', profile)">试听</a-button>
              <a-button
                v-if="!profile.is_builtin"
                size="small"
                danger
                @click.stop="handleDelete(profile)"
              >
                删除
              </a-button>
            </div>
          </div>

          <div v-if="filteredProfiles.length === 0" class="empty-list">
            <span>{{ searchQuery ? '没有匹配的音色' : '暂无音色' }}</span>
          </div>
        </div>

        <!-- Create Button -->
        <div class="drawer-footer">
          <a-button type="primary" block @click="showCreateDrawer = true">
            新建音色
          </a-button>
        </div>
      </div>
    </a-drawer>

    <!-- Create/Edit Drawer -->
    <VoiceProfileDrawer
      v-model:open="showCreateDrawer"
      @created="handleCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { voiceProfilesApi } from '../api'
import VoiceProfileDrawer from './VoiceProfileDrawer.vue'

const props = defineProps({
  modelValue: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'audition'])

const showDrawer = ref(false)
const showCreateDrawer = ref(false)
const searchQuery = ref('')
const activeFilter = ref('all')
const profiles = ref([])

const filterTabs = [
  { label: '全部', value: 'all' },
  { label: '系统预设', value: 'builtin' },
  { label: '我的音色', value: 'custom' },
]

const selectedProfile = computed(() => props.modelValue)

const filteredProfiles = computed(() => {
  let list = profiles.value

  if (activeFilter.value === 'builtin') {
    list = list.filter(p => p.is_builtin)
  } else if (activeFilter.value === 'custom') {
    list = list.filter(p => !p.is_builtin)
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      p.name.toLowerCase().includes(q) ||
      (p.description || '').toLowerCase().includes(q) ||
      (p.raw_description || '').toLowerCase().includes(q)
    )
  }

  return list
})

const genderLabel = (gender) => {
  const map = { female: '女声', male: '男声', neutral: '中性' }
  return map[gender] || gender
}

const speedLabel = (speed) => {
  const map = { slow: '慢速', medium_slow: '中慢', medium: '中速', medium_fast: '中快', fast: '快速' }
  return map[speed] || speed
}

const fetchProfiles = async () => {
  try {
    const { data } = await voiceProfilesApi.list({ active: 1 })
    profiles.value = data
  } catch {
    // Ignore errors silently
  }
}

onMounted(fetchProfiles)

const handleSelect = (profile) => {
  emit('update:modelValue', profile)
  showDrawer.value = false
}

const handleDelete = async (profile) => {
  try {
    await voiceProfilesApi.delete(profile.id)
    profiles.value = profiles.value.filter(p => p.id !== profile.id)
    if (selectedProfile.value?.id === profile.id) {
      emit('update:modelValue', null)
    }
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}

const handleCreated = async (profile) => {
  await fetchProfiles()
  emit('update:modelValue', profile)
  showCreateDrawer.value = false
  showDrawer.value = false
}
</script>

<style scoped>
.voice-profile-selector {
  width: 100%;
}

/* Current Profile */
.current-profile {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.current-profile:hover {
  border-color: var(--surface-border-strong);
}

.profile-info {
  flex: 1;
  min-width: 0;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: 4px;
}

.profile-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.profile-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0 0 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-tags {
  display: flex;
  gap: var(--space-xs);
  font-size: 12px;
  color: var(--text-subtle);
}

.profile-tags span {
  background: var(--surface-muted);
  padding: 1px 6px;
  border-radius: 4px;
}

.profile-actions {
  display: flex;
  gap: var(--space-xs);
  flex-shrink: 0;
}

/* Empty State */
.empty-profile {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
  background: var(--paper-soft);
  border: 1px dashed var(--surface-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-muted);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.empty-profile:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

/* Drawer */
.drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.search-input {
  margin-bottom: var(--space-md);
}

.filter-tabs {
  display: flex;
  gap: 2px;
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  padding: 2px;
  margin-bottom: var(--space-md);
}

.filter-tab {
  flex: 1;
  padding: 6px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-body);
}

.filter-tab:hover {
  color: var(--text-secondary);
}

.filter-tab.active {
  background: var(--surface);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

/* Profile List */
.profile-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.profile-card {
  padding: var(--space-md);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.profile-card:hover {
  border-color: var(--surface-border-strong);
}

.profile-card.selected {
  border-color: var(--text-primary);
  box-shadow: var(--shadow-focus);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: 4px;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  gap: var(--space-xs);
  font-size: 11px;
  color: var(--text-subtle);
  margin-bottom: 8px;
}

.card-tags span {
  background: var(--surface-muted);
  padding: 1px 6px;
  border-radius: 4px;
}

.card-actions {
  display: flex;
  gap: var(--space-xs);
}

.empty-list {
  text-align: center;
  padding: var(--space-xl);
  color: var(--text-muted);
  font-size: 14px;
}

/* Drawer Footer */
.drawer-footer {
  padding-top: var(--space-md);
  border-top: 1px solid var(--surface-border);
  margin-top: var(--space-md);
}
</style>
