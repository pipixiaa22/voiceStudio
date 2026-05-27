<template>
  <section class="discovery-search">
    <div class="search-title">
      <div>
        <h1>热点采集</h1>
        <p>从热门样本提取结构，生成自己的修仙短视频脚本</p>
      </div>
      <div class="title-actions">
        <a-button class="config-entry-btn" @click="$emit('configure-search')">
          平台配置
        </a-button>
        <a-alert
          class="guardrail"
          type="info"
          message="默认只保存来源和分析结果，不下载原视频、原音频或原字幕。"
          show-icon
        />
      </div>
    </div>

    <a-alert
      v-if="configWarning"
      class="config-warning"
      type="warning"
      :message="configWarning.message"
      :description="configWarning.description"
      show-icon
    >
      <template #action>
        <a-button size="small" type="link" @click="$emit('configure-search')">去配置</a-button>
      </template>
    </a-alert>

    <div class="search-grid">
      <a-select v-model:value="local.platform" class="platform-select" aria-label="平台">
        <a-select-option value="all">全部平台</a-select-option>
        <a-select-option value="manual">手动链接</a-select-option>
        <a-select-option value="youtube">YouTube</a-select-option>
        <a-select-option value="douyin">抖音</a-select-option>
        <a-select-option value="kuaishou">快手</a-select-option>
        <a-select-option value="bilibili">B 站</a-select-option>
      </a-select>

      <a-input
        v-model:value="local.query"
        class="keyword-input"
        allow-clear
        placeholder="搜索：修仙小说 一张图 / 仙帝重生 有声小说"
        @pressEnter="handleSearch"
      >
        <template #prefix>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="input-icon">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </template>
      </a-input>

      <a-select v-model:value="local.timeRange" class="compact-select" aria-label="时间范围">
        <a-select-option value="7">近 7 天</a-select-option>
        <a-select-option value="30">近 30 天</a-select-option>
        <a-select-option value="90">近 90 天</a-select-option>
        <a-select-option value="all">全部</a-select-option>
      </a-select>

      <a-select v-model:value="local.durationRange" class="compact-select" aria-label="时长">
        <a-select-option value="all">全部时长</a-select-option>
        <a-select-option value="short">30 秒内</a-select-option>
        <a-select-option value="medium">30 秒-2 分钟</a-select-option>
        <a-select-option value="long">2-8 分钟</a-select-option>
      </a-select>

      <a-select v-model:value="local.sortBy" class="compact-select" aria-label="排序">
        <a-select-option value="recommended">综合推荐</a-select-option>
        <a-select-option value="latest">最新</a-select-option>
        <a-select-option value="hot">热度</a-select-option>
        <a-select-option value="relevance">相关性</a-select-option>
      </a-select>

      <a-button type="primary" :loading="loading" class="search-btn" @click="handleSearch">
        搜索热点
      </a-button>
    </div>

    <div class="link-row">
      <a-input
        v-model:value="manualUrl"
        allow-clear
        placeholder="粘贴视频链接，适合抖音/快手/B站等手动样本"
        @pressEnter="handleResolve"
      >
        <template #prefix>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="input-icon">
            <path d="M10 13a5 5 0 0 0 7.07 0l2.83-2.83a5 5 0 0 0-7.07-7.07L11.5 4.43" />
            <path d="M14 11a5 5 0 0 0-7.07 0L4.1 13.83a5 5 0 0 0 7.07 7.07l1.33-1.33" />
          </svg>
        </template>
      </a-input>
      <a-button :loading="loading" @click="handleResolve">解析链接</a-button>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  loading: Boolean,
  query: { type: String, default: '' },
  platform: { type: String, default: 'all' },
  timeRange: { type: String, default: '30' },
  durationRange: { type: String, default: 'all' },
  sortBy: { type: String, default: 'recommended' },
  configWarning: { type: Object, default: null },
})

const emit = defineEmits(['search', 'resolve-url', 'configure-search'])

const manualUrl = ref('')
const local = reactive({
  query: props.query,
  platform: props.platform,
  timeRange: props.timeRange,
  durationRange: props.durationRange,
  sortBy: props.sortBy,
})

watch(() => props.query, value => { local.query = value })

const handleSearch = () => {
  emit('search', { ...local })
}

const handleResolve = () => {
  if (!manualUrl.value.trim()) return
  emit('resolve-url', manualUrl.value.trim())
  manualUrl.value = ''
}
</script>

<style scoped>
.discovery-search {
  background: var(--surface);
  border-bottom: 1px solid var(--surface-border);
  padding: var(--space-lg);
}

.search-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-lg);
  margin-bottom: var(--space-md);
}

.search-title h1 {
  margin: 0 0 4px;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 650;
  letter-spacing: 0;
}

.search-title p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}

.guardrail {
  max-width: 430px;
  padding: 6px 10px;
  font-size: 12px;
}

.title-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-sm);
}

.config-entry-btn {
  flex: 0 0 auto;
  height: 32px;
}

.config-warning {
  margin-bottom: var(--space-sm);
}

.search-grid {
  display: grid;
  grid-template-columns: 124px minmax(260px, 1fr) 104px 126px 112px 104px;
  gap: var(--space-sm);
  align-items: center;
}

.link-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}

.input-icon {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
}

.keyword-input,
.platform-select,
.compact-select,
.search-btn {
  height: 36px;
}

@media (max-width: 1180px) {
  .search-grid {
    grid-template-columns: 132px minmax(280px, 1fr) 1fr 1fr;
  }

  .search-btn {
    grid-column: span 1;
  }
}

@media (max-width: 760px) {
  .discovery-search {
    padding: var(--space-md);
  }

  .search-title {
    flex-direction: column;
  }

  .title-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .guardrail {
    max-width: none;
  }

  .search-grid,
  .link-row {
    grid-template-columns: 1fr;
  }
}
</style>
