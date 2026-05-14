<script setup lang="ts">
import { onMounted } from "vue";
import AppLayout from "@/components/layout/AppLayout.vue";

onMounted(() => {
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const applyTheme = (e: MediaQueryListEvent | MediaQueryList) => {
    document.documentElement.classList.toggle("dark", e.matches);
  };
  applyTheme(mediaQuery);
  mediaQuery.addEventListener("change", applyTheme);
});
</script>

<template>
  <AppLayout />
</template>
