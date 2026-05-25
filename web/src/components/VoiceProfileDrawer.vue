<template>
  <a-drawer
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="新建音色"
    placement="right"
    :width="480"
    :bodyStyle="{ padding: '16px' }"
  >
    <a-form layout="vertical" class="profile-form">
      <!-- 基础信息 -->
      <div class="form-section">
        <div class="section-title">基础信息</div>
        <a-form-item label="音色名称" required>
          <a-input v-model:value="form.name" placeholder="例如：我的课程旁白" />
        </a-form-item>
        <a-form-item label="音色来源">
          <a-radio-group v-model:value="form.source_type" button-style="solid" size="small">
            <a-radio-button value="voice_design">文本设计</a-radio-button>
            <a-radio-button value="voice_clone">音色复刻</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="使用场景">
          <a-select v-model:value="form.scene" placeholder="选择场景" allowClear>
            <a-select-option value="xianxia_character">修仙角色</a-select-option>
            <a-select-option value="short_video">短视频旁白</a-select-option>
            <a-select-option value="course">课程讲解</a-select-option>
            <a-select-option value="story">故事朗读</a-select-option>
            <a-select-option value="news">新闻资讯</a-select-option>
            <a-select-option value="business">商务介绍</a-select-option>
            <a-select-option value="ad">广告口播</a-select-option>
            <a-select-option value="vlog">vlog</a-select-option>
          </a-select>
        </a-form-item>
      </div>

      <!-- 授权样音 -->
      <div v-if="form.source_type === 'voice_clone'" class="form-section">
        <div class="section-title">授权样音</div>
        <a-form-item label="上传样音" required>
          <input
            type="file"
            accept="audio/wav,audio/mp3,audio/mpeg"
            @change="handleSampleChange"
          />
          <div v-if="form.voice_sample_filename" class="sample-file">
            {{ form.voice_sample_filename }} · {{ form.voice_sample_mime }}
          </div>
        </a-form-item>
        <a-form-item>
          <a-checkbox v-model:checked="form.consent_confirmed">
            我确认该样音已获得授权，可用于音色复刻
          </a-checkbox>
        </a-form-item>
      </div>

      <!-- 声音特征 -->
      <div class="form-section">
        <div class="section-title">声音特征</div>
        <a-form-item label="性别">
          <a-radio-group v-model:value="form.gender" button-style="solid" size="small">
            <a-radio-button value="female">女声</a-radio-button>
            <a-radio-button value="male">男声</a-radio-button>
            <a-radio-button value="neutral">中性</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="语速">
          <a-radio-group v-model:value="form.speed" button-style="solid" size="small">
            <a-radio-button value="slow">慢</a-radio-button>
            <a-radio-button value="medium_slow">中慢</a-radio-button>
            <a-radio-button value="medium">中速</a-radio-button>
            <a-radio-button value="medium_fast">中快</a-radio-button>
            <a-radio-button value="fast">快</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="情绪">
          <a-select v-model:value="form.emotion" placeholder="选择情绪" allowClear>
            <a-select-option value="gentle">温和</a-select-option>
            <a-select-option value="calm">稳重</a-select-option>
            <a-select-option value="lively">轻快</a-select-option>
            <a-select-option value="restrained">克制</a-select-option>
            <a-select-option value="healing">治愈</a-select-option>
            <a-select-option value="powerful">有力</a-select-option>
            <a-select-option value="natural">自然</a-select-option>
            <a-select-option value="professional">专业</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="音色质感">
          <a-input v-model:value="form.timbre" placeholder="例如：清澈、温暖、低沉" />
        </a-form-item>
        <a-form-item label="音频标签">
          <a-input v-model:value="form.style_tags" placeholder="例如：古风 清冷 凌厉 平静" />
        </a-form-item>
        <a-form-item label="口音">
          <a-input v-model:value="form.accent" placeholder="例如：标准普通话、台湾腔" />
        </a-form-item>
      </div>

      <!-- 描述 -->
      <div class="form-section">
        <div class="section-title">描述</div>
        <a-form-item label="我想要的声音" required>
          <a-textarea
            v-model:value="form.raw_description"
            placeholder="例如：像一位耐心的中文课程老师，咬字清晰，语气自然，不要太像播音腔。"
            :autoSize="{ minRows: 3, maxRows: 5 }"
          />
        </a-form-item>
        <a-form-item label="我不想要的声音">
          <a-textarea
            v-model:value="form.negative_prompt"
            placeholder="例如：不要儿童音，不要播音腔，不要情绪太夸张"
            :autoSize="{ minRows: 2, maxRows: 3 }"
          />
        </a-form-item>
        <a-form-item label="试听文案">
          <a-textarea
            v-model:value="form.audition_text"
            placeholder="例如：（古风 清冷）跪下。你既入我玄霜峰，便该知道修仙一途，从无侥幸二字。"
            :autoSize="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
      </div>
    </a-form>

    <template #footer>
      <div class="drawer-footer">
        <a-button @click="$emit('update:open', false)">取消</a-button>
        <a-button
          type="primary"
          :loading="saving"
          :disabled="!canSave"
          @click="handleSave"
        >
          保存并试听
        </a-button>
      </div>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { message } from 'ant-design-vue'
import { voiceProfilesApi } from '../api'

const props = defineProps({
  open: Boolean,
})

const emit = defineEmits(['update:open', 'created'])

const saving = ref(false)

const form = reactive({
  name: '',
  source_type: 'voice_design',
  scene: undefined,
  gender: undefined,
  speed: undefined,
  emotion: undefined,
  timbre: '',
  accent: '',
  style_tags: '',
  raw_description: '',
  negative_prompt: '',
  audition_text: '（古风 叙事）云海翻涌，仙门将启。你若踏上这条修行路，便再无回头之日。',
  voice_sample_data_uri: '',
  voice_sample_mime: '',
  voice_sample_filename: '',
  consent_confirmed: false,
})

const canSave = computed(() => {
  if (!form.name || !form.raw_description) return false
  if (form.source_type !== 'voice_clone') return true
  return Boolean(form.voice_sample_data_uri && form.consent_confirmed)
})

const handleSampleChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  if (!['audio/wav', 'audio/mp3', 'audio/mpeg'].includes(file.type)) {
    message.error('只支持 mp3 或 wav 样音')
    event.target.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    form.voice_sample_data_uri = reader.result
    form.voice_sample_mime = file.type
    form.voice_sample_filename = file.name
  }
  reader.onerror = () => message.error('读取样音失败')
  reader.readAsDataURL(file)
}

const handleSave = async () => {
  saving.value = true
  try {
    const { data } = await voiceProfilesApi.create({
      name: form.name,
      scene: form.scene,
      gender: form.gender,
      speed: form.speed,
      emotion: form.emotion,
      timbre: form.timbre,
      accent: form.accent,
      style_tags: form.style_tags,
      raw_description: form.raw_description,
      negative_prompt: form.negative_prompt,
      audition_text: form.audition_text,
      source_type: form.source_type,
      voice_sample_data_uri: form.voice_sample_data_uri,
      voice_sample_mime: form.voice_sample_mime,
      voice_sample_filename: form.voice_sample_filename,
      consent_confirmed: form.consent_confirmed,
    })
    message.success('音色已创建')
    emit('created', data)
    // Reset form
    Object.assign(form, {
      name: '',
      source_type: 'voice_design',
      scene: undefined,
      gender: undefined,
      speed: undefined,
      emotion: undefined,
      timbre: '',
      accent: '',
      style_tags: '',
      raw_description: '',
      negative_prompt: '',
      audition_text: '（古风 叙事）云海翻涌，仙门将启。你若踏上这条修行路，便再无回头之日。',
      voice_sample_data_uri: '',
      voice_sample_mime: '',
      voice_sample_filename: '',
      consent_confirmed: false,
    })
  } catch (e) {
    message.error(e.response?.data?.error || '创建失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.form-section {
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid var(--surface-border);
}

.form-section:last-child {
  border-bottom: none;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-md);
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}

.sample-file {
  margin-top: var(--space-sm);
  font-size: 12px;
  color: var(--text-muted);
}
</style>
