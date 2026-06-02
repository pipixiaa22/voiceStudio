<template>
  <div class="novel-outline-panel">
    <a-tabs v-model:activeKey="store.leftTab" size="small">
      <a-tab-pane key="outline" tab="大纲">
        <div class="outline-actions">
          <a-button size="small" @click="handleAddRoot">新增卷</a-button>
        </div>
        <a-tree
          v-if="treeData.length"
          :tree-data="treeData"
          :field-names="{ key: 'id', title: 'title', children: 'children' }"
          default-expand-all
          @select="handleOutlineSelect"
        />
        <a-empty v-else description="暂无大纲" />
      </a-tab-pane>

      <a-tab-pane key="chapters" tab="章节">
        <a-list :data-source="store.chapters" size="small">
          <template #renderItem="{ item }">
            <a-list-item
              :class="{ active: store.currentChapter?.id === item.id }"
              @click="handleChapterClick(item)"
            >
              <a-list-item-meta :title="item.title" :description="`${item.word_count || 0} 字`" />
            </a-list-item>
          </template>
        </a-list>
      </a-tab-pane>

      <a-tab-pane key="settings" tab="设定">
        <div class="settings-links">
          <a-button block @click="enterGraph('characters')">人物关系图</a-button>
          <a-button block @click="enterGraph('events')">事件因果图</a-button>
        </div>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

const treeData = computed(() => store.outlineTree)

const handleOutlineSelect = (selectedKeys) => {
  if (!selectedKeys.length) return
  const nodeId = selectedKeys[0]
  // Find the chapter associated with this outline node
  const chapter = store.chapters.find(c => c.outline_node_id === nodeId)
  if (chapter) {
    store.loadChapter(store.currentProject.id, chapter.id)
  }
}

const handleChapterClick = (chapter) => {
  if (store.currentProject) {
    store.loadChapter(store.currentProject.id, chapter.id)
  }
}

const handleAddRoot = async () => {
  if (!store.currentProject) return
  try {
    await store.createOutlineNode(store.currentProject.id, {
      title: '新卷',
      node_type: 'volume',
    })
    message.success('已新增')
  } catch {
    message.error('新增失败')
  }
}

const enterGraph = (type) => {
  store.graphType = type
  store.activeMode = 'graph'
}
</script>

<style scoped>
.novel-outline-panel {
  height: 100%;
}
.outline-actions {
  padding: 8px;
  display: flex;
  gap: 4px;
}
.settings-links {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
:deep(.ant-list-item) {
  cursor: pointer;
  padding: 8px 12px;
}
:deep(.ant-list-item:hover) {
  background: var(--surface-hover);
}
:deep(.ant-list-item.active) {
  background: var(--surface-active, #e6f7ff);
  border-left: 3px solid #1890ff;
}
</style>
