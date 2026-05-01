import { createRouter, createWebHistory } from 'vue-router'
import { state } from './stores/authStore'
import LoginView from './views/LoginView.vue'
import RegisterView from './views/RegisterView.vue'
import HomeView from './views/HomeView.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: { guest: true }
  },
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { requiresAuth: true }
  },
  {
    path: '/papers',
    name: 'papers',
    component: () => import('./views/PaperListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/papers/:id',
    name: 'paperDetail',
    component: () => import('./views/PaperDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const isAuth = !!state.token

  if (to.meta.requiresAuth && !isAuth) {
    return next('/login')
  }

  if (to.meta.guest && isAuth) {
    return next('/')
  }

  next()
})

export default router
