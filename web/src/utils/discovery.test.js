import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildOriginalScriptDraft,
  buildVideoPrefill,
  filterDiscoveryItems,
  formatMetric,
  getScoreLevel,
  normalizeDiscoveryAnalysis,
  normalizeDiscoveryItem,
  sortDiscoveryItems,
} from './discovery.js'

const ITEMS = [
  {
    id: 'yt-1',
    platform: 'youtube',
    title: '仙帝重生后，一张图讲完宗门逆袭',
    author: '玄影说书',
    xianxiaScore: 92,
    hotScore: 81,
    formatScore: 87,
    status: 'analyzed',
    favorite: true,
    stats: { views: 126000, likes: 8120, comments: 312, shares: 86 },
    structure: {
      hook: '废柴弟子被逐出山门，却在后山觉醒万古剑骨。',
      conflict: '宗门长老压迫主角，逼他交出机缘。',
      protagonist: '被轻视的外门弟子',
      powerPoint: '万古剑骨首次显形',
      cliffhanger: '师尊发现他的剑意来自失传禁地。',
    },
  },
  {
    id: 'bi-1',
    platform: 'bilibili',
    title: '都市职场沟通技巧合集',
    author: '效率研究所',
    xianxiaScore: 12,
    hotScore: 66,
    formatScore: 22,
    status: 'new',
    favorite: false,
    stats: { views: 90000, likes: 1200 },
  },
  {
    id: 'dy-1',
    platform: 'douyin',
    title: '开局被逐出宗门，女帝竟替我挡下天劫',
    author: '云上短剧',
    xianxiaScore: 88,
    hotScore: 93,
    formatScore: 76,
    status: 'scripted',
    favorite: false,
    stats: { views: 450000, likes: 36000, comments: 1900, shares: 6200 },
  },
]

test('getScoreLevel maps score bands to semantic levels', () => {
  assert.equal(getScoreLevel(91), 'high')
  assert.equal(getScoreLevel(50), 'mid')
  assert.equal(getScoreLevel(49), 'low')
})

test('formatMetric displays compact Chinese counts and missing values', () => {
  assert.equal(formatMetric(126000), '12.6w')
  assert.equal(formatMetric(9000), '9,000')
  assert.equal(formatMetric(null), '--')
})

test('filterDiscoveryItems filters by platform, query, favorite, and status', () => {
  const results = filterDiscoveryItems(ITEMS, {
    platform: 'youtube',
    query: '仙帝 宗门',
    favoriteOnly: true,
    statusFilter: 'analyzed',
  })

  assert.deepEqual(results.map(item => item.id), ['yt-1'])
})

test('sortDiscoveryItems orders by composite score by default', () => {
  const results = sortDiscoveryItems(ITEMS, 'recommended')
  assert.deepEqual(results.map(item => item.id), ['dy-1', 'yt-1', 'bi-1'])
})

test('buildOriginalScriptDraft creates an editable original draft from structure', () => {
  const draft = buildOriginalScriptDraft(ITEMS[0], { length: 'short', style: '热血' })

  assert.match(draft.title, /剑骨|宗门|天劫/)
  assert.match(draft.content, /【旁白】/)
  assert.match(draft.content, /万古剑骨/)
  assert.notEqual(draft.title, ITEMS[0].title)
})

test('buildVideoPrefill maps discovery analysis to video generation defaults', () => {
  const prefill = buildVideoPrefill(ITEMS[0])

  assert.equal(prefill.template_key, 'xianxia_narration')
  assert.equal(prefill.subtitle_options.max_chars, 18)
  assert.equal(prefill.audio_options.ambient_key, 'wind')
  assert.deepEqual(prefill.source_context, {
    discovery_item_id: 'yt-1',
    platform: 'youtube',
    source_url: undefined,
  })
})

test('normalizeDiscoveryItem maps backend snake_case fields to UI item fields', () => {
  const item = normalizeDiscoveryItem({
    id: 12,
    platform_key: 'youtube',
    source_url: 'https://youtube.com/watch?v=abc',
    title: '修仙小说 有声',
    author_name: '测试频道',
    cover_url: 'https://example.com/cover.jpg',
    published_at: '2026-05-27T10:00:00+08:00',
    duration: 120,
    stats: { views: 50000, likes: 2000 },
    tags: ['修仙'],
    is_favorited: true,
    xianxia_score: 83,
    hot_score: 72,
    format_score: 68,
    analysis: {
      score_reasons: ['标题命中修仙'],
      generated_title: '原创标题',
      generated_content: '原创正文',
      recommended_template: 'xianxia_narration',
      recommended_voice_desc: '沉稳男声',
      recommended_max_chars: 16,
      analysis: {
        title_pattern: '身份反转',
        hook: '开局危机',
      },
    },
  })

  assert.equal(item.id, 12)
  assert.equal(item.platform, 'youtube')
  assert.equal(item.platformName, 'YouTube')
  assert.equal(item.sourceUrl, 'https://youtube.com/watch?v=abc')
  assert.equal(item.author, '测试频道')
  assert.equal(item.favorite, true)
  assert.equal(item.status, 'scripted')
  assert.equal(item.structure.titlePattern, '身份反转')
  assert.equal(item.structure.hook, '开局危机')
  assert.deepEqual(item.scriptDraft, { title: '原创标题', content: '原创正文' })
})

test('normalizeDiscoveryAnalysis merges analyze response into an existing item', () => {
  const item = normalizeDiscoveryItem({
    id: 9,
    platform_key: 'manual',
    source_url: 'https://example.com/video',
    title: '手动链接',
  })
  const merged = normalizeDiscoveryAnalysis(item, {
    xianxia_score: 91,
    hot_score: 61,
    format_score: 77,
    score_reasons: ['手动链接导入'],
    generated_title: '后山剑骨',
    generated_content: '【旁白】他醒了。',
    recommended_template: 'xianxia_narration',
    recommended_voice_desc: '冷峻男声',
    recommended_max_chars: 18,
    analysis: {
      plot_skeleton: '少年被逐出宗门后觉醒剑骨',
      subtitle_rhythm: '短句优先',
    },
  })

  assert.equal(merged.xianxiaScore, 91)
  assert.equal(merged.status, 'scripted')
  assert.equal(merged.reason[0], '手动链接导入')
  assert.equal(merged.structure.plotSkeleton, '少年被逐出宗门后觉醒剑骨')
  assert.equal(merged.scriptDraft.content, '【旁白】他醒了。')
  assert.equal(merged.videoRecommendation.recommendedMaxChars, 18)
})
