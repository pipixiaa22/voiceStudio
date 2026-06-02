export const MEMORY_TYPE_COLORS = {
  character: 'blue',
  world_rule: 'purple',
  event: 'orange',
  foreshadowing: 'gold',
  relationship: 'cyan',
  style: 'green',
  summary: 'default',
}

export const MEMORY_TYPE_LABELS = {
  character: '人物',
  world_rule: '世界观',
  event: '事件',
  foreshadowing: '伏笔',
  relationship: '关系',
  style: '文风',
  summary: '摘要',
}

export function typeColor(type) {
  return MEMORY_TYPE_COLORS[type] || 'default'
}

export function typeLabel(type) {
  return MEMORY_TYPE_LABELS[type] || type
}
