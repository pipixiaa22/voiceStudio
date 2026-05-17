<template>
  <a-modal
    :open="open"
    title="生成视频"
    @update:open="$emit('update:open', $event)"
    :footer="null"
    width="500px"
  >
    <a-form layout="vertical">
      <a-form-item label="宽高比">
        <a-radio-group v-model:value="aspectRatio">
          <a-radio-button value="9:16">9:16 竖屏</a-radio-button>
          <a-radio-button value="16:9">16:9 横屏</a-radio-button>
          <a-radio-button value="1:1">1:1 方形</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <a-form-item label="背景图片">
        <a-upload
          :before-upload="handleImageUpload"
          :show-upload-list="false"
          accept="image/*"
        >
          <a-button>
            <template #icon>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
            </template>
            选择图片
          </a-button>
        </a-upload>
        <div v-if="imageFile" class="image-preview">
          <span>{{ imageFile.name }}</span>
          <a-button type="link" size="small" @click="imageFile = null">移除</a-button>
        </div>
      </a-form-item>

      <a-form-item label="音色描述">
        <a-textarea
          v-model:value="voiceDescription"
          placeholder="描述你想要的音色..."
          :rows="2"
        />
      </a-form-item>

      <a-form-item>
        <a-button
          type="primary"
          :loading="generating"
          :disabled="!canGenerate"
          @click="handleGenerate"
          block
        >
          {{ generating ? '正在生成...' : '生成视频' }}
        </a-button>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { videoApi } from '../api'
import { useSettings } from '../stores/settings'

const props = defineProps({
  open: Boolean,
  textId: { type: Number, required: true },
  textTitle: { type: String, default: '视频' },
})

const emit = defineEmits(['update:open'])

const { llmKey } = useSettings()

const aspectRatio = ref('9:16')
const imageFile = ref(null)
const voiceDescription = ref('温柔的女性声音')
const generating = ref(false)

const canGenerate = computed(() => {
  return imageFile.value && voiceDescription.value && llmKey.value
})

const handleImageUpload = (file) => {
  imageFile.value = file
  return false
}

const handleGenerate = async () => {
  if (!llmKey.value) {
    message.error('请先配置 API Key')
    return
  }

  if (!imageFile.value) {
    message.error('请上传背景图片')
    return
  }

  if (!voiceDescription.value) {
    message.error('请填写音色描述')
    return
  }

  generating.value = true
  try {
    const formData = new FormData()
    formData.append('text_id', props.textId)
    formData.append('image', imageFile.value)
    formData.append('aspect_ratio', aspectRatio.value)
    formData.append('api_key', llmKey.value)
    formData.append('voice_description', voiceDescription.value)

    const response = await videoApi.generate(formData)

    // 检查响应是否是 JSON 错误
    if (response.data.type === 'application/json') {
      const reader = new FileReader()
      reader.onload = () => {
        const errorData = JSON.parse(reader.result)
        message.error(errorData.error || '视频生成失败')
      }
      reader.readAsText(response.data)
      return
    }

    // 下载视频
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.textTitle}.mp4`
    link.click()
    window.URL.revokeObjectURL(url)

    message.success('视频生成成功')
    emit('update:open', false)
  } catch (error) {
    // 提取错误信息
    let errorMessage = '视频生成失败'
    if (error.response && error.response.data) {
      try {
        // 尝试从 blob 响应中解析 JSON
        if (error.response.data instanceof Blob) {
          const reader = new FileReader()
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result)
              message.error(errorData.error || errorMessage)
            } catch {
              message.error(errorMessage)
            }
          }
          reader.readAsText(error.response.data)
          return
        }
        // 直接是 JSON 响应
        if (error.response.data.error) {
          errorMessage = error.response.data.error
        }
      } catch (e) {
        console.error('解析错误信息失败:', e)
      }
    }
    message.error(errorMessage)
    console.error(error)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.image-preview {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
