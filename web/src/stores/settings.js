import { ref, computed } from 'vue'

const ttsKey = ref(localStorage.getItem('mimo_tts_key') || '')
const llmKey = ref(localStorage.getItem('mimo_llm_key') || '')
const systemPrompt = ref(localStorage.getItem('mimo_polish_prompt') || '')

const DEFAULT_PROMPT = `你是一个专业的语音合成音色描述润色专家。用户会给你一段音色描述文本，你需要将其润色为更具体、更生动、更专业的版本。

润色规则：
1. 保留用户原始的音色意图和核心特征
2. 补充缺失的维度信息（如性别、年龄、音色质感、情绪语气、语速节奏等）
3. 使用更具象、更专业的描述词汇
4. 避免矛盾的特征描述
5. 避免音质效果词（混响、回声等后期处理描述）
6. 控制在 1-4 句话，简洁有力
7. 使用与用户相同的语言（中文描述用中文润色，英文描述用英文润色）

只输出润色后的音色描述，不要输出解释或额外内容。`

const hasTtsKey = computed(() => Boolean(ttsKey.value?.trim()))
const hasLlmKey = computed(() => Boolean(llmKey.value?.trim()))

export function useSettings() {
  const loadFromStorage = () => {
    ttsKey.value = localStorage.getItem('mimo_tts_key') || ''
    llmKey.value = localStorage.getItem('mimo_llm_key') || ''
    systemPrompt.value = localStorage.getItem('mimo_polish_prompt') || DEFAULT_PROMPT
  }

  const saveAll = (tts, llm, prompt) => {
    ttsKey.value = tts
    llmKey.value = llm
    systemPrompt.value = prompt
    localStorage.setItem('mimo_tts_key', tts)
    localStorage.setItem('mimo_llm_key', llm)
    localStorage.setItem('mimo_polish_prompt', prompt)
  }

  return {
    ttsKey,
    llmKey,
    systemPrompt,
    hasTtsKey,
    hasLlmKey,
    defaultPrompt: DEFAULT_PROMPT,
    loadFromStorage,
    saveAll,
  }
}
