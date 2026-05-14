import { createRouter, createWebHistory } from 'vue-router'
import TextList from '../views/TextList.vue'
import TextEdit from '../views/TextEdit.vue'
import Import from '../views/Import.vue'

const routes = [
  { path: '/', component: TextList },
  { path: '/edit/:id?', component: TextEdit },
  { path: '/import', component: Import },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
