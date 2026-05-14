import { createRouter, createWebHistory } from "vue-router";
import { api, tokenStore, ApiError } from "@/lib/api";
import HomeView from "@/views/HomeView.vue";

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
      component: HomeView,
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
//
// Flow:
//  1. Public routes (/setup, /login) are always accessible.
//  2. If no local token → check if setup is done:
//       - not configured → redirect to /setup
//       - configured     → redirect to /login
//  3. If a token exists → verify it with /auth/me:
//       - valid   → allow
//       - invalid → clear token, redirect to /login
//  4. If the user is already logged in and visits /login or /setup → redirect to /

router.beforeEach(async (to) => {
  const isPublic = !!to.meta.public;

  // Already have a token – verify it
  if (tokenStore.has()) {
    try {
      await api.auth.me();
      // Token is valid
      if (to.name === "login" || to.name === "setup") {
        return { name: "home" };
      }
      return true;
    } catch (e) {
      // Token expired or invalid – clear it
      if (e instanceof ApiError && e.status === 401) {
        tokenStore.clear();
      }
    }
  }

  // No valid token
  if (isPublic) return true;

  // Check if setup has been done
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
