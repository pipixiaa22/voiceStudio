<template>
  <aside class="analysis-panel">
    <template v-if="item">
      <div class="analysis-head">
        <div>
          <span class="source-label">{{ item.platformName }}</span>
          <h2>{{ item.title }}</h2>
        </div>
        <div class="head-actions">
          <a-tooltip :title="item.favorite ? '取消收藏' : '收藏'">
            <a-button class="icon-btn" @click="$emit('toggle-favorite', item.id)">
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
          <a-popconfirm
            title="确定删除此采集记录？"
            ok-text="删除"
            cancel-text="取消"
            @confirm="$emit('delete-item', item.id)"
          >
            <a-tooltip title="删除">
              <a-button class="icon-btn danger-btn">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </template>
              </a-button>
            </a-tooltip>
          </a-popconfirm>
        </div>
      </div>

      <a-tabs :active-key="activeTab" class="analysis-tabs" @change="$emit('tab-change', $event)">
        <a-tab-pane key="overview" tab="概览">
          <div class="overview-grid">
            <div><span>作者</span><strong>{{ item.author }}</strong></div>
            <div><span>时长</span><strong>{{ item.duration }}s</strong></div>
            <div><span>播放</span><strong>{{ formatMetric(item.stats?.views) }}</strong></div>
            <div><span>点赞</span><strong>{{ formatMetric(item.stats?.likes) }}</strong></div>
          </div>

          <div class="score-stack">
            <div v-for="score in scores" :key="score.label" class="score-line">
              <div>
                <span>{{ score.label }}</span>
                <strong>{{ score.value }}</strong>
              </div>
              <a-progress :percent="score.value" :show-info="false" size="small" />
            </div>
          </div>

          <section class="reason-box">
            <h3>命中原因</h3>
            <ul>
              <li v-for="reason in item.reason" :key="reason">{{ reason }}</li>
            </ul>
          </section>

          <div class="panel-actions">
            <a-button :loading="analyzing" @click="$emit('analyze', item.id)">分析结构</a-button>
            <a-button type="primary" @click="$emit('generate-script', item.id)">生成原创脚本</a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="structure" tab="热点结构">
          <div v-if="analyzing" class="step-progress">
            <div v-for="step in analysisSteps" :key="step"><span />{{ step }}</div>
          </div>
          <div v-else class="structure-list">
            <section v-for="block in structureBlocks" :key="block.label">
              <span>{{ block.label }}</span>
              <p>{{ block.value }}</p>
            </section>
          </div>
        </a-tab-pane>

        <a-tab-pane key="script" tab="原创脚本">
          <DiscoveryScriptEditor
            :draft="scriptDraft"
            :imported-text="importedText"
            :generating="generating"
            :importing="importing"
            @generate="$emit('generate-script', item.id, $event)"
            @update-draft="$emit('update-script', item.id, $event)"
            @import-text="$emit('import-text', item.id, $event)"
            @edit-text="$emit('edit-text', $event)"
            @open-video="$emit('open-video', $event)"
          />
        </a-tab-pane>

        <a-tab-pane key="video" tab="视频建议">
          <DiscoveryVideoSuggestion
            :prefill="videoPrefill"
            :can-open-video="Boolean(importedText)"
            @open-video="$emit('open-video', importedText)"
          />
        </a-tab-pane>

        <a-tab-pane key="source" tab="来源记录">
          <div class="source-record">
            <div><span>原始链接</span><a :href="item.sourceUrl" target="_blank">{{ item.sourceUrl }}</a></div>
            <div><span>采集时间</span><strong>{{ collectedAt }}</strong></div>
            <div><span>连接器</span><strong>{{ item.platform }} connector</strong></div>
            <div><span>素材说明</span><p>默认只保存来源和分析结果，不下载原视频、原音频或原字幕。</p></div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </template>

    <div v-else class="empty-analysis">
      <h2>等待选择样本</h2>
      <p>搜索热点后，选择一条候选视频查看结构分析和脚本建议。</p>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import DiscoveryScriptEditor from './DiscoveryScriptEditor.vue'
import DiscoveryVideoSuggestion from './DiscoveryVideoSuggestion.vue'
import { buildVideoPrefill, formatMetric } from '../../utils/discovery'

const props = defineProps({
  item: Object,
  activeTab: { type: String, default: 'overview' },
  scriptDraft: Object,
  importedText: Object,
  analyzing: Boolean,
  generating: Boolean,
  importing: Boolean,
})

defineEmits([
  'tab-change',
  'analyze',
  'generate-script',
  'update-script',
  'import-text',
  'edit-text',
  'open-video',
  'toggle-favorite',
  'delete-item',
])

const scores = computed(() => props.item ? [
  { label: '修仙相关', value: props.item.xianxiaScore },
  { label: '热度', value: props.item.hotScore },
  { label: '单图形态', value: props.item.formatScore },
] : [])

const structureBlocks = computed(() => {
  const structure = props.item?.structure || {}
  return [
    { label: '标题套路', value: structure.titlePattern },
    { label: '前 3 秒钩子', value: structure.hook },
    { label: '冲突来源', value: structure.conflict },
    { label: '主角设定', value: structure.protagonist },
    { label: '爽点设计', value: structure.powerPoint },
    { label: '悬念断点', value: structure.cliffhanger },
    { label: '字幕节奏', value: structure.subtitleRhythm },
  ].filter(block => block.value)
})

const videoPrefill = computed(() => props.item ? buildVideoPrefill(props.item) : {})

const collectedAt = computed(() => new Date().toLocaleString('zh-CN', {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
}))

const analysisSteps = ['读取元数据', '计算相关性', '识别视频形态', '提取热点结构', '生成原创建议']
</script>

<style scoped>
.analysis-panel {
  background: var(--surface);
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.analysis-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-lg);
  border-bottom: 1px solid var(--surface-border);
}

.source-label {
  color: var(--text-muted);
  font-size: 12px;
}

.analysis-head h2 {
  margin: 4px 0 0;
  color: var(--text-primary);
  font-size: 18px;
  line-height: 1.45;
}

.head-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.icon-btn {
  width: 32px !important;
  height: 32px !important;
  padding: 0 !important;
}

.icon-btn svg {
  width: 14px;
  height: 14px;
}

.danger-btn:hover {
  color: var(--danger, #e74c3c) !important;
  border-color: var(--danger, #e74c3c) !important;
}

.analysis-tabs {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.analysis-tabs :deep(.ant-tabs-nav) {
  margin: 0;
  padding: 0 var(--space-lg);
}

.analysis-tabs :deep(.ant-tabs-content-holder) {
  padding: var(--space-lg);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-sm);
}

.overview-grid > div {
  padding: 12px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  background: var(--paper-soft);
}

.overview-grid span,
.score-line span,
.reason-box h3,
.structure-list span,
.source-record span {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.overview-grid strong,
.score-line strong {
  color: var(--text-primary);
  font-size: 14px;
}

.score-stack,
.reason-box,
.structure-list,
.source-record {
  margin-top: var(--space-md);
}

.score-line + .score-line {
  margin-top: 12px;
}

.score-line > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.reason-box {
  padding: 12px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
}

.reason-box ul {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.8;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-md);
}

.structure-list {
  display: grid;
  gap: var(--space-sm);
}

.structure-list section,
.source-record > div {
  padding: 12px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  background: var(--paper-soft);
}

.structure-list p,
.source-record p,
.source-record strong,
.source-record a {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

.source-record {
  display: grid;
  gap: var(--space-sm);
}

.step-progress {
  display: grid;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.step-progress div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-progress span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-primary);
}

.empty-analysis {
  margin: auto;
  max-width: 280px;
  padding: var(--space-xl);
  text-align: center;
}

.empty-analysis h2 {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-size: 18px;
}

.empty-analysis p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
}
</style>
