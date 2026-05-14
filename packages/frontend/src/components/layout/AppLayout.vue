<script setup lang="ts">
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import AppSidebar from "./AppSidebar.vue";
</script>

<template>
    <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
            <RouterView />
        </SidebarInset>
    </SidebarProvider>
</template>
