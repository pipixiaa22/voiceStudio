import { createRouter, createWebHistory } from 'vue-router'
const TextList = () => import('../views/TextList.vue')
const TextEdit = () => import('../views/TextEdit.vue')
const Import = () => import('../views/Import.vue')
const QuickGenerate = () => import('../views/QuickGenerate.vue')
const Discovery = () => import('../views/Discovery.vue')
const VoiceWorkflowList = () => import('../views/VoiceWorkflowList.vue')
const VoiceWorkflowView = () => import('../views/VoiceWorkflowView.vue')

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
