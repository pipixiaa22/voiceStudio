<!-- web/src/views/NovelProjectList.vue -->
<template>
  <div class="novel-project-list">
    <div class="page-header">
      <div>
        <h1 class="page-title">剧情续写</h1>
        <p class="page-subtitle">{{ store.projects.length }} 个小说工程</p>
      </div>
      <a-button type="primary" @click="showCreateModal = true">新建工程</a-button>
    </div>

    <div class="list-tools">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索小说标题"
        allow-clear
        style="max-width: 320px"
      />
      <a-select v-model:value="statusFilter" placeholder="状态" allow-clear style="width: 120px">
        <a-select-option value="draft">草稿</a-select-option>
        <a-select-option value="active">进行中</a-select-option>
        <a-select-option value="completed">已完成</a-select-option>
      </a-select>
    </div>

    <a-empty v-if="!store.projects.length && !store.projectsLoading" description="还没有小说工程">
      <a-button type="primary" @click="showCreateModal = true">新建工程</a-button>
    </a-empty>

    <a-empty v-else-if="!filteredProjects.length" description="没有匹配的工程" />

    <a-spin v-else-if="store.projectsLoading" />

    <div v-else class="project-grid">
      <article
        v-for="project in filteredProjects"
        :key="project.id"
        class="project-item"
      >
        <button class="project-main" @click="$router.push(`/novels/${project.id}`)">
          <strong>{{ project.title || '未命名小说' }}</strong>
          <span class="project-genre">{{ project.genre }}</span>
          <span class="project-progress">
            {{ project.stats?.chapter_count || 0 }} / {{ project.target_chapters }} 章
            · {{ formatWords(project.stats?.total_words || 0) }} / {{ formatWords(project.target_total_words) }}
          </span>
          <span class="project-meta">{{ project.knowledge_update_mode }} · {{ formatDate(project.updated_at) }}</span>
        </button>
        <div class="project-actions">
          <a-button size="small" @click="$router.push(`/novels/${project.id}`)">打开</a-button>
          <a-popconfirm
            title="删除这个工程？所有章节和图谱数据将被永久删除。"
            ok-text="删除"
            cancel-text="取消"
            @confirm="handleDelete(project)"
          >
            <a-button size="small" danger>删除</a-button>
          </a-popconfirm>
        </div>
      </article>
    </div>

    <!-- Create Project Modal -->
    <a-modal
      v-model:open="showCreateModal"
      title="新建小说工程"
      ok-text="创建"
      cancel-text="取消"
      :confirm-loading="creating"
      @ok="handleCreate"
      width="560px"
    >
      <a-form layout="vertical">
        <a-form-item label="小说标题" required>
          <a-input v-model:value="newProject.title" placeholder="例：长夜剑骨" />
        </a-form-item>
        <a-form-item label="类型">
          <a-select v-model:value="newProject.genre" style="width: 100%">
            <a-select-option v-for="g in genres" :key="g" :value="g">{{ g }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="一句话创意">
          <a-textarea v-model:value="newProject.premise" placeholder="一句话描述你的小说创意..." :autoSize="{ minRows: 2, maxRows: 4 }" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="目标总字数">
              <a-input-number v-model:value="newProject.target_total_words" :min="10000" :step="100000" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="目标章节数">
              <a-input-number v-model:value="newProject.target_chapters" :min="10" :step="50" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="每章字数">
              <a-input-number v-model:value="newProject.words_per_chapter" :min="500" :step="500" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../stores/novels'

const store = useNovelsStore()
const keyword = ref('')
const statusFilter = ref(undefined)
const showCreateModal = ref(false)
const creating = ref(false)

const genres = ['玄幻', '仙侠', '都市', '悬疑', '言情', '科幻', '历史', '末世', '轻小说']

const newProject = ref({
  title: '',
  genre: '玄幻',
  premise: '',
  target_total_words: 300000,
  target_chapters: 100,
  words_per_chapter: 3000,
})

onMounted(() => store.fetchProjects())

const filteredProjects = computed(() => {
  let list = store.projects
  const q = keyword.value.trim().toLowerCase()
  if (q) list = list.filter(p => (p.title || '').toLowerCase().includes(q))
  if (statusFilter.value) list = list.filter(p => p.status === statusFilter.value)
  return list
})

const formatWords = (n) => {
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`
  return `${n}`
}

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN')
}

const handleCreate = async () => {
  if (!newProject.value.title.trim()) {
    message.warning('请填写小说标题')
    return
  }
  creating.value = true
  try {
    await store.createProject(newProject.value)
    showCreateModal.value = false
    newProject.value = { title: '', genre: '玄幻', premise: '', target_total_words: 300000, target_chapters: 100, words_per_chapter: 3000 }
    message.success('工程创建成功')
  } catch (e) {
    message.error('创建失败: ' + (e.response?.data?.error || e.message))
  } finally {
    creating.value = false
  }
}

const handleDelete = async (project) => {
  try {
    await store.deleteProject(project.id)
    message.success('已删除')
  } catch (e) {
    message.error('删除失败')
  }
}
</script>

<style scoped>
.novel-project-list {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-lg);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-lg);
}
.page-title {
  font-size: 24px;
  font-weight: 650;
  margin: 0;
}
.page-subtitle {
  color: var(--text-muted);
  margin: 4px 0 0;
}
.list-tools {
  display: flex;
  gap: 12px;
  margin-bottom: var(--space-lg);
}
.project-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.project-item {
  display: flex;
  align-items: center;
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  background: var(--surface-card);
  overflow: hidden;
}
.project-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 16px;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
}
.project-main:hover { background: var(--surface-hover); }
.project-main strong { font-size: 15px; }
.project-genre {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.project-progress {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.project-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.project-actions {
  display: flex;
  gap: 8px;
  padding: 16px;
}
</style>
