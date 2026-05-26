<template>
  <div class="audio-step">
    <h4>音频设置</h4>

    <a-form layout="vertical">
      <a-divider orientation="left">背景音乐 (BGM)</a-divider>

      <a-form-item>
        <a-switch v-model:checked="localOptions.bgm_enabled" checked-children="开启" un-checked-children="关闭" />
      </a-form-item>

      <template v-if="localOptions.bgm_enabled">
        <a-form-item label="BGM 文件">
          <a-upload
            :before-upload="handleBgmUpload"
            :show-upload-list="false"
            accept="audio/*"
          >
            <a-button>
              {{ bgmFile ? '更换 BGM' : '上传 BGM' }}
            </a-button>
          </a-upload>
          <span v-if="bgmFile" class="file-name">{{ bgmFile.name }}</span>
        </a-form-item>

        <a-form-item label="BGM 音量">
          <a-slider
            v-model:value="localOptions.bgm_volume"
            :min="0"
            :max="1"
            :step="0.01"
            :tip-formatter="(v) => `${Math.round(v * 100)}%`"
          />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="淡入">
              <a-input-number v-model:value="localOptions.bgm_fade_in" :min="0" :max="5" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="淡出">
              <a-input-number v-model:value="localOptions.bgm_fade_out" :min="0" :max="5" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </template>

      <a-divider orientation="left">环境音</a-divider>

      <a-form-item>
        <a-switch v-model:checked="localOptions.ambient_enabled" checked-children="开启" un-checked-children="关闭" />
      </a-form-item>

      <template v-if="localOptions.ambient_enabled">
        <a-form-item label="环境音类型">
          <a-select v-model:value="localOptions.ambient_key" style="width: 100%">
            <a-select-option value="wind">风声</a-select-option>
            <a-select-option value="rain">雨声</a-select-option>
            <a-select-option value="thunder">雷声</a-select-option>
            <a-select-option value="sword">剑鸣</a-select-option>
            <a-select-option value="bell">钟声</a-select-option>
            <a-select-option value="fire">火焰声</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="环境音音量">
          <a-slider
            v-model:value="localOptions.ambient_volume"
            :min="0"
            :max="1"
            :step="0.01"
            :tip-formatter="(v) => `${Math.round(v * 100)}%`"
          />
        </a-form-item>
      </template>
    </a-form>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  audioOptions: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:audioOptions', 'prev', 'next'])

const localOptions = ref({ ...props.audioOptions })
const bgmFile = ref(null)

watch(() => props.audioOptions, (val) => {
  localOptions.value = { ...val }
})

const handleBgmUpload = (file) => {
  bgmFile.value = file
  return false
}

const handleNext = () => {
  emit('update:audioOptions', localOptions.value)
  emit('next')
}
</script>

<style scoped>
.audio-step h4 {
  margin-bottom: 16px;
}

.file-name {
  margin-left: 8px;
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
