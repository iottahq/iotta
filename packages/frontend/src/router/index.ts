import { createRouter, createWebHistory } from "vue-router";
import { api, tokenStore, ApiError } from "@/lib/api";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // ── Public ──────────────────────────────────────────────────────────────────
    {
      path: "/setup",
      name: "setup",
      component: () => import("@/views/SetupView.vue"),
      meta: { public: true },
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { public: true },
    },

    // ── Protected ───────────────────────────────────────────────────────────────
    {
      path: "/",
      name: "home",
      component: () => import("@/views/home/view.vue"),
    },
    {
      path: "/devices/:id",
      name: "device",
      component: () => import("@/views/DeviceView.vue"),
    },
    {
      path: "/plugins",
      name: "plugins",
      component: () => import("@/views/PluginsView.vue"),
    },
    {
      path: "/insights",
      name: "insights",
      component: () => import("@/views/InsightsView.vue"),
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/views/SettingsView.vue"),
    },
  ],
});

// ── Navigation guard ───────────────────────────────────────────────────────────

router.beforeEach(async (to) => {
  const isPublic = !!to.meta.public;

  if (tokenStore.has()) {
    try {
      await api.auth.me();
      if (to.name === "login" || to.name === "setup") {
        return { name: "home" };
      }
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        tokenStore.clear();
      }
    }
  }

  if (isPublic) return true;

  try {
    const status = await api.auth.setupStatus();
    if (!status.configured) {
      return { name: "setup" };
    }
  } catch {
    // Backend unreachable – still try login
  }

  return { name: "login", query: { redirect: to.fullPath } };
});

export default router;
