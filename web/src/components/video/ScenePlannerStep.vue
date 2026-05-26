<template>
  <div class="scene-step">
    <h4>分镜设置</h4>
    <p class="hint">上传多张图片按顺序分配到分镜，或只上传一张图片用于整条视频。</p>

    <div class="scene-list">
      <div v-for="(scene, index) in localScenes" :key="index" class="scene-item">
        <div class="scene-header">
          <span class="scene-label">Scene {{ String(index + 1).padStart(2, '0') }}</span>
          <a-button
            v-if="localScenes.length > 1"
            type="text"
            size="small"
            danger
            @click="removeScene(index)"
          >
            移除
          </a-button>
        </div>

        <div class="scene-content">
          <a-upload
            :before-upload="(file) => handleSceneImage(file, index)"
            :show-upload-list="false"
            accept="image/*"
          >
            <a-button size="small">
              {{ scene.imageFile ? '更换图片' : '上传图片' }}
            </a-button>
          </a-upload>
          <span v-if="scene.imageFile" class="file-name">{{ scene.imageFile.name }}</span>
        </div>

        <div class="scene-motion">
          <span class="motion-label">动效:</span>
          <a-select v-model:value="scene.motion" size="small" style="width: 140px">
            <a-select-option value="slow_zoom_in">慢推近</a-select-option>
            <a-select-option value="slow_zoom_out">慢拉远</a-select-option>
            <a-select-option value="pan_left_right">左右平移</a-select-option>
            <a-select-option value="breathing_zoom">呼吸缩放</a-select-option>
            <a-select-option value="shake">轻微震动</a-select-option>
          </a-select>
        </div>
      </div>
    </div>

    <a-button type="dashed" block @click="addScene" style="margin-top: 12px">
      + 添加分镜
    </a-button>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  scenes: { type: Array, default: () => [] },
  subtitleCount: { type: Number, default: 0 },
})

const emit = defineEmits(['update:scenes', 'prev', 'next'])

const localScenes = ref(props.scenes.length > 0 ? [...props.scenes] : [createEmptyScene()])

function createEmptyScene() {
  return {
    imageFile: null,
    motion: 'slow_zoom_in',
  }
}

watch(() => props.scenes, (val) => {
  if (val.length > 0 && localScenes.value.length === 1 && !localScenes.value[0].imageFile) {
    localScenes.value = [...val]
  }
})

const addScene = () => {
  localScenes.value.push(createEmptyScene())
}

const removeScene = (index) => {
  localScenes.value.splice(index, 1)
}

const handleSceneImage = (file, index) => {
  localScenes.value[index].imageFile = file
  return false
}

const handleNext = () => {
  emit('update:scenes', localScenes.value)
  emit('next')
}
</script>

<style scoped>
.scene-step h4 {
  margin-bottom: 8px;
}

.hint {
  color: var(--text-secondary, #999);
  font-size: 13px;
  margin-bottom: 16px;
}

.scene-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scene-item {
  border: 1px solid var(--border-color, #e8e8e8);
  border-radius: 8px;
  padding: 12px;
}

.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.scene-label {
  font-weight: 500;
  font-size: 13px;
}

.scene-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-name {
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.scene-motion {
  display: flex;
  align-items: center;
  gap: 8px;
}

.motion-label {
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
