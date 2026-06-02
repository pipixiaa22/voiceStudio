"""Long-term memory document type definitions."""

MEMORY_TYPES = (
    'world_rule',      # 世界观规则
    'character',       # 人物设定
    'relationship',    # 人物关系
    'event',           # 事件
    'foreshadowing',   # 伏笔
    'style',           # 文风
    'summary',         # 摘要
)

SOURCE_TYPES = (
    'project',      # 项目级设定
    'chapter',      # 章节
    'outline',      # 大纲
    'entity',       # 人物/实体
    'event',        # 事件
    'manual_note',  # 手动笔记
    'ai_extract',   # AI 抽取
)

VECTOR_STATUS = ('pending', 'indexed', 'failed')
MEMORY_STATUS = ('active', 'archived', 'superseded')
CHANGE_STATUS = ('pending', 'confirmed', 'rejected')
