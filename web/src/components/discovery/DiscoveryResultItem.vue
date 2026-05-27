<template>
  <article class="result-item" :class="{ active }" @click="$emit('select', item.id)">
    <div class="cover" :class="item.coverTone">
      <span class="cover-platform">{{ platformShort }}</span>
      <strong>{{ coverTitle }}</strong>
    </div>

    <div class="item-main">
      <div class="item-title-row">
        <h2>{{ item.title }}</h2>
        <a-tag class="status-tag">{{ statusLabel }}</a-tag>
      </div>
      <div class="meta-row">
        <span>{{ item.author }}</span>
        <span>{{ item.platformName }}</span>
        <span>{{ durationText }}</span>
        <span>{{ dateText }}</span>
      </div>
      <div class="metric-row">
        <span>播放 {{ formatMetric(item.stats?.views) }}</span>
        <span>点赞 {{ formatMetric(item.stats?.likes) }}</span>
        <span>评论 {{ formatMetric(item.stats?.comments) }}</span>
        <span>分享 {{ formatMetric(item.stats?.shares) }}</span>
      </div>
      <div class="score-row">
        <DiscoveryScoreBadge label="相关" :score="item.xianxiaScore" />
        <DiscoveryScoreBadge label="热度" :score="item.hotScore" />
        <DiscoveryScoreBadge label="形态" :score="item.formatScore" />
      </div>
    </div>

    <div class="item-actions" @click.stop>
      <a-tooltip :title="item.favorite ? '取消收藏' : '收藏'">
        <a-button class="icon-btn" @click="$emit('favorite', item.id)">
          <template #icon>
            <svg viewBox="0 0 24 24" :fill="item.favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </template>
        </a-button>
      </a-tooltip>
      <a-tooltip title="打开原链接">
        <a-button class="icon-btn" :href="item.sourceUrl" target="_blank">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </template>
        </a-button>
      </a-tooltip>
      <a-button size="small" @click="$emit('analyze', item.id)">分析</a-button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import DiscoveryScoreBadge from './DiscoveryScoreBadge.vue'
import { formatMetric } from '../../utils/discovery'

const props = defineProps({
  item: { type: Object, required: true },
  active: Boolean,
})

defineEmits(['select', 'favorite', 'analyze'])

const statusMap = {
  new: '未分析',
  analyzed: '已分析',
  scripted: '已生成脚本',
  imported: '已导入文本',
}

const statusLabel = computed(() => statusMap[props.item.status] || '未分析')
const coverTitle = computed(() => (props.item.title || '').slice(0, 8))
const platformShort = computed(() => ({
  youtube: 'YT',
  douyin: 'DY',
  kuaishou: 'KS',
  bilibili: 'B站',
}[props.item.platform] || 'URL'))

const durationText = computed(() => {
  const seconds = Number(props.item.duration || 0)
  const min = Math.floor(seconds / 60)
  const sec = Math.floor(seconds % 60)
  return min ? `${min}:${String(sec).padStart(2, '0')}` : `${sec}s`
})

const dateText = computed(() => {
  if (!props.item.publishedAt) return '--'
  return new Date(props.item.publishedAt).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
})
</script>

<style scoped>
.result-item {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 92px;
  gap: var(--space-md);
  padding: 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.result-item:hover,
.result-item.active {
  background: var(--surface);
  border-color: var(--surface-border);
}

.result-item.active {
  border-color: var(--surface-border-strong);
  box-shadow: var(--shadow-sm);
}

.cover {
  position: relative;
  width: 72px;
  height: 112px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #1f1f1f;
  color: #fff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.cover::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(145deg, rgba(255,255,255,0.18), transparent 42%),
    repeating-linear-gradient(0deg, rgba(255,255,255,0.05), rgba(255,255,255,0.05) 1px, transparent 1px, transparent 7px);
}

.cover.mountain { background: linear-gradient(160deg, #18231f, #647066); }
.cover.thunder { background: linear-gradient(160deg, #151515, #65605d); }
.cover.library { background: linear-gradient(160deg, #27221d, #817362); }
.cover.portrait { background: linear-gradient(160deg, #2b2426, #7a686d); }
.cover.plain { background: linear-gradient(160deg, #343434, #8a8a84); }
.cover.manual { background: linear-gradient(160deg, #222, #77736c); }

.cover-platform,
.cover strong {
  position: relative;
  z-index: 1;
}

.cover-platform {
  font-size: 11px;
  opacity: 0.78;
}

.cover strong {
  font-size: 13px;
  line-height: 1.45;
}

.item-main {
  min-width: 0;
}

.item-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
}

.item-title-row h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 650;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.status-tag {
  margin: 0;
  white-space: nowrap;
}

.meta-row,
.metric-row,
.score-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.meta-row {
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 12px;
}

.metric-row {
  margin-top: 8px;
  color: var(--text-subtle);
  font-size: 11px;
}

.score-row {
  margin-top: 10px;
}

.item-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 8px;
}

.icon-btn {
  width: 30px !important;
  height: 30px !important;
  padding: 0 !important;
}

.icon-btn svg {
  width: 14px;
  height: 14px;
}

@media (max-width: 760px) {
  .result-item {
    grid-template-columns: 64px minmax(0, 1fr);
  }

  .cover {
    width: 64px;
    height: 100px;
  }

  .item-actions {
    grid-column: 1 / -1;
    flex-direction: row;
    justify-content: flex-end;
  }
}
</style>
