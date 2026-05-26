import { ref, watch } from 'vue'

const STORAGE_KEY = 'model_settings'

const defaultSettings = {
  providers: [],
  defaults: {},
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
  } catch {}
  return { ...defaultSettings }
}

function saveToStorage(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

function migrateOldKeys(settings) {
  const oldTtsKey = localStorage.getItem('mimo_tts_key') || ''
  const oldLlmKey = localStorage.getItem('mimo_llm_key') || ''

  if (oldTtsKey || oldLlmKey) {
    const hasMimo = settings.providers.some(p => p.provider_key === 'mimo')
    if (!hasMimo) {
      settings.providers.push({
        provider_key: 'mimo',
        api_key: oldTtsKey || oldLlmKey,
        enabled: true,
      })
    }
  }
  return settings
}

const settings = ref(migrateOldKeys(loadFromStorage()))

watch(settings, (val) => {
  saveToStorage(val)
}, { deep: true })

export function useModelSettings() {
  const getProvider = (key) => {
    return settings.value.providers.find(p => p.provider_key === key)
  }

  const setProvider = (key, config) => {
    const idx = settings.value.providers.findIndex(p => p.provider_key === key)
    if (idx >= 0) {
      settings.value.providers[idx] = { ...settings.value.providers[idx], ...config }
    } else {
      settings.value.providers.push({ provider_key: key, ...config })
    }
  }

  const removeProvider = (key) => {
    settings.value.providers = settings.value.providers.filter(p => p.provider_key !== key)
  }

  const getProviderApiKey = (key) => {
    return getProvider(key)?.api_key || ''
  }

  const setUsageDefault = (usage, providerKey, modelKey) => {
    settings.value.defaults[usage] = { provider_key: providerKey, model_key: modelKey }
  }

  const getUsageDefault = (usage) => {
    return settings.value.defaults[usage] || null
  }

  const resolveUsage = (usage) => {
    const def = getUsageDefault(usage)
    if (!def) return null
    return {
      provider_key: def.provider_key,
      model_key: def.model_key,
      api_key: getProviderApiKey(def.provider_key),
    }
  }

  return {
    settings,
    getProvider,
    setProvider,
    removeProvider,
    getProviderApiKey,
    setUsageDefault,
    getUsageDefault,
    resolveUsage,
  }
}
