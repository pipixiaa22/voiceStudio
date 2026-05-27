<template>
  <div class="video-suggestion">
    <div class="suggestion-grid">
      <div>
        <span>推荐模板</span>
        <strong>{{ templateName }}</strong>
      </div>
      <div>
        <span>字幕长度</span>
        <strong>{{ prefill.subtitle_options?.max_chars }} 字</strong>
      </div>
      <div>
        <span>BGM</span>
        <strong>{{ prefill.audio_options?.bgm_enabled ? `${Math.round(prefill.audio_options.bgm_volume * 100)}%` : '关闭' }}</strong>
      </div>
      <div>
        <span>环境音</span>
        <strong>{{ ambientName }}</strong>
      </div>
    </div>

    <section class="suggestion-block">
      <h4>声线建议</h4>
      <p>{{ prefill.voice_description }}</p>
    </section>

    <section class="suggestion-block">
      <h4>场景图关键词</h4>
      <div class="keyword-row">
        <a-tag v-for="keyword in prefill.scene_keywords" :key="keyword">{{ keyword }}</a-tag>
      </div>
    </section>

    <a-alert
      type="info"
      message="平台素材只作为灵感来源，不会放入视频素材包。"
      show-icon
    />

    <div class="action-row">
      <a-button type="primary" :disabled="!canOpenVideo" @click="$emit('open-video')">应用到视频生成</a-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  prefill: { type: Object, required: true },
  canOpenVideo: Boolean,
})

defineEmits(['open-video'])

const templateName = computed(() => ({
  xianxia_narration: '修仙旁白',
  character_monologue: '角色独白',
  battle_transition: '战斗转场',
})[props.prefill.template_key] || props.prefill.template_key)

const ambientName = computed(() => ({
  wind: '风声',
  rain: '雨声',
  thunder: '雷声',
  sword: '剑鸣',
  bell: '钟声',
  fire: '火焰声',
})[props.prefill.audio_options?.ambient_key] || '关闭')
</script>

<style scoped>
.video-suggestion {
  display: grid;
  gap: var(--space-md);
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-sm);
}

.suggestion-grid > div,
.suggestion-block {
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  background: var(--paper-soft);
  padding: 12px;
}

.suggestion-grid span,
.suggestion-block h4 {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 520;
  margin: 0 0 6px;
}

.suggestion-grid strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 650;
}

.suggestion-block p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.keyword-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-row {
  display: flex;
  justify-content: flex-end;
}
</style>
