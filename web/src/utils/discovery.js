export const getScoreLevel = (score = 0) => {
  if (score >= 80) return 'high'
  if (score >= 50) return 'mid'
  return 'low'
}

export const formatMetric = (value) => {
  if (value === null || value === undefined || value === '') return '--'
  const number = Number(value)
  if (!Number.isFinite(number)) return '--'
  if (number >= 10000) {
    const compact = number / 10000
    return `${compact.toFixed(compact >= 100 ? 0 : 1).replace(/\.0$/, '')}w`
  }
  return number.toLocaleString('en-US')
}

export const getCompositeScore = (item) => {
  return Math.round(
    (Number(item.xianxiaScore || 0) * 0.4) +
    (Number(item.hotScore || 0) * 0.35) +
    (Number(item.formatScore || 0) * 0.25)
  )
}

export const PLATFORM_NAMES = {
  manual: '手动链接',
  youtube: 'YouTube',
  douyin: '抖音',
  kuaishou: '快手',
  bilibili: 'B 站',
}

const normalizeStructure = (analysis = {}) => ({
  titlePattern: analysis.title_pattern || analysis.titlePattern || '待分析',
  hook: analysis.hook || '待分析',
  plotSkeleton: analysis.plot_skeleton || analysis.plotSkeleton || '',
  conflict: analysis.conflict || analysis.plot_skeleton || analysis.plotSkeleton || '',
  protagonist: analysis.protagonist || '',
  powerPoint: analysis.power_point || analysis.powerPoint || '',
  cliffhanger: analysis.cliffhanger || '',
  subtitleRhythm: analysis.subtitle_rhythm || analysis.subtitleRhythm || '',
})

export const normalizeDiscoveryAnalysis = (item, analysisResponse = {}) => {
  const analysis = analysisResponse.analysis || {}
  const generatedTitle = analysisResponse.generated_title || ''
  const generatedContent = analysisResponse.generated_content || ''

  return {
    ...item,
    xianxiaScore: Math.round(Number(analysisResponse.xianxia_score ?? item.xianxiaScore ?? 0)),
    hotScore: Math.round(Number(analysisResponse.hot_score ?? item.hotScore ?? 0)),
    formatScore: Math.round(Number(analysisResponse.format_score ?? item.formatScore ?? 0)),
    reason: analysisResponse.score_reasons || item.reason || [],
    structure: {
      ...(item.structure || {}),
      ...normalizeStructure(analysis),
    },
    scriptDraft: generatedContent
      ? { title: generatedTitle || item.title || '未命名原创脚本', content: generatedContent }
      : item.scriptDraft,
    videoRecommendation: {
      recommendedTemplate: analysisResponse.recommended_template || item.videoRecommendation?.recommendedTemplate,
      recommendedVoiceDesc: analysisResponse.recommended_voice_desc || item.videoRecommendation?.recommendedVoiceDesc,
      recommendedMaxChars: analysisResponse.recommended_max_chars || item.videoRecommendation?.recommendedMaxChars,
    },
    status: generatedContent ? 'scripted' : 'analyzed',
  }
}

export const normalizeDiscoveryItem = (raw = {}) => {
  const analysis = raw.analysis || null
  const platform = raw.platform_key || raw.platform || 'manual'
  const item = {
    id: raw.id,
    queryId: raw.query_id,
    platform,
    platformName: PLATFORM_NAMES[platform] || platform,
    title: raw.title || '未命名样本',
    author: raw.author_name || raw.author || '未知作者',
    coverUrl: raw.cover_url,
    coverTone: platform === 'bilibili' ? 'library' : platform === 'douyin' ? 'thunder' : platform === 'kuaishou' ? 'portrait' : 'mountain',
    sourceUrl: raw.source_url,
    sourceId: raw.source_id,
    publishedAt: raw.published_at,
    duration: raw.duration || 0,
    stats: raw.stats || {},
    tags: raw.tags || [],
    favorite: Boolean(raw.is_favorited ?? raw.favorite),
    xianxiaScore: Math.round(Number(raw.xianxia_score || analysis?.xianxia_score || 0)),
    hotScore: Math.round(Number(raw.hot_score || analysis?.hot_score || 0)),
    formatScore: Math.round(Number(raw.format_score || analysis?.format_score || 0)),
    reason: analysis?.score_reasons || raw.score_reasons || raw.reason || [],
    structure: normalizeStructure(analysis?.analysis || {}),
    status: analysis?.generated_content ? 'scripted' : analysis ? 'analyzed' : 'new',
    scriptDraft: analysis?.generated_content
      ? { title: analysis.generated_title || raw.title || '未命名原创脚本', content: analysis.generated_content }
      : null,
    videoRecommendation: analysis ? {
      recommendedTemplate: analysis.recommended_template,
      recommendedVoiceDesc: analysis.recommended_voice_desc,
      recommendedMaxChars: analysis.recommended_max_chars,
    } : {},
    raw,
  }

  if (!analysis && (raw.xianxia_score || raw.hot_score || raw.format_score)) {
    item.status = 'analyzed'
  }

  return item
}

export const filterDiscoveryItems = (items, filters = {}) => {
  const {
    platform = 'all',
    query = '',
    favoriteOnly = false,
    statusFilter = 'all',
  } = filters
  const queryParts = String(query)
    .toLowerCase()
    .split(/\s+/)
    .map(part => part.trim())
    .filter(Boolean)

  return items.filter((item) => {
    if (platform !== 'all' && item.platform !== platform) return false
    if (favoriteOnly && !item.favorite) return false
    if (statusFilter !== 'all' && item.status !== statusFilter) return false

    if (queryParts.length) {
      const haystack = [
        item.title,
        item.author,
        item.description,
        ...(item.tags || []),
      ].join(' ').toLowerCase()
      if (!queryParts.every(part => haystack.includes(part))) return false
    }

    return true
  })
}

export const sortDiscoveryItems = (items, sortBy = 'recommended') => {
  const sorted = [...items]
  const sorters = {
    recommended: (a, b) => {
      const scoreDelta = getCompositeScore(b) - getCompositeScore(a)
      if (Math.abs(scoreDelta) <= 1) return Number(b.hotScore || 0) - Number(a.hotScore || 0)
      return scoreDelta
    },
    hot: (a, b) => Number(b.hotScore || 0) - Number(a.hotScore || 0),
    relevance: (a, b) => Number(b.xianxiaScore || 0) - Number(a.xianxiaScore || 0),
    latest: (a, b) => new Date(b.publishedAt || 0) - new Date(a.publishedAt || 0),
  }
  return sorted.sort(sorters[sortBy] || sorters.recommended)
}

export const buildOriginalScriptDraft = (item, options = {}) => {
  const length = options.length || 'medium'
  const style = options.style || '爽文'
  const structure = item.structure || {}
  const protagonist = structure.protagonist || '被轻视的外门弟子'
  const hook = structure.hook || '他被逐出宗门当天，在后山听见了万剑齐鸣。'
  const conflict = structure.conflict || '昔日同门要夺走他的最后一件遗物。'
  const powerPoint = structure.powerPoint || '沉寂多年的剑骨在体内苏醒。'
  const cliffhanger = structure.cliffhanger || '天劫落下时，一道神秘女声叫出了他的真名。'
  const title = style === '冷峻'
    ? '被逐出宗门那夜，我听见万剑向我俯首'
    : '开局被逐出宗门，我在后山觉醒万古剑骨'

  const endings = {
    short: '下一刻，他抬手一指，满山断剑同时出鞘。',
    medium: '可他还没来得及问清真相，禁地石门忽然裂开，里面传来一句：少主，你终于回来了。',
    long: '从这一夜开始，所有曾经轻视他的人都会发现，被赶下山门的不是废物，而是宗门最后一条生路。',
  }

  const content = [
    `【旁白】${hook}`,
    `【旁白】所有人都以为，${protagonist}已经没有翻身的机会。`,
    `【旁白】${conflict}`,
    `【旁白】可就在他低头捡起断剑的瞬间，${powerPoint}`,
    `【旁白】山门钟声连响九次，连闭关百年的长老都被惊醒。`,
    `【旁白】${cliffhanger}`,
    `【旁白】${endings[length] || endings.medium}`,
  ].join('\n')

  return { title, content }
}

export const buildVideoPrefill = (item) => {
  const isBattle = /战|天劫|剑|雷|逆袭/.test(item.title || '')
  const recommendation = item.videoRecommendation || {}
  return {
    template_key: recommendation.recommendedTemplate || (isBattle ? 'xianxia_narration' : 'xianxia_narration'),
    voice_description: recommendation.recommendedVoiceDesc || '沉稳、有故事感的男声，节奏略慢，适合修仙旁白',
    subtitle_options: {
      max_chars: recommendation.recommendedMaxChars || 18,
      gap: 0.3,
    },
    audio_options: {
      bgm_enabled: true,
      bgm_volume: 0.16,
      bgm_fade_in: 1.0,
      bgm_fade_out: 1.5,
      ambient_enabled: true,
      ambient_key: isBattle ? 'wind' : 'wind',
      ambient_volume: 0.12,
    },
    scene_keywords: ['云海山门', '雷劫', '古殿', '剑修背影'],
    source_context: {
      discovery_item_id: item.id,
      platform: item.platform,
      source_url: item.sourceUrl,
    },
  }
}
