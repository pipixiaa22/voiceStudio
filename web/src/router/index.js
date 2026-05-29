import { createRouter, createWebHistory } from 'vue-router'
import TextList from '../views/TextList.vue'
import TextEdit from '../views/TextEdit.vue'
import Import from '../views/Import.vue'
import QuickGenerate from '../views/QuickGenerate.vue'
import Discovery from '../views/Discovery.vue'
import VoiceWorkflowList from '../views/VoiceWorkflowList.vue'
import VoiceWorkflowView from '../views/VoiceWorkflowView.vue'

const routes = [
  { path: '/', component: TextList },
  { path: '/discovery', component: Discovery },
  { path: '/edit/:id?', component: TextEdit },
  { path: '/import', component: Import },
  { path: '/quick-generate', component: QuickGenerate },
  { path: '/voice-workflows', component: VoiceWorkflowList },
  { path: '/voice-workflows/:id', component: VoiceWorkflowView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
