<script setup lang="ts">
import {
    SidebarProvider,
    SidebarInset,
    SidebarTrigger,
    useSidebar,
} from "@/components/ui/sidebar";
import AppSidebar from "./AppSidebar.vue";
</script>

<template>
    <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
            <header
                class="flex items-center gap-2 px-3 py-2 md:hidden border-b border-border"
            >
                <SidebarTrigger />
            </header>
            <RouterView />
        </SidebarInset>
    </SidebarProvider>
</template>
