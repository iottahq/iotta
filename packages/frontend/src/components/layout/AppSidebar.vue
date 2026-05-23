<script setup lang="ts">
import { useRouter, useRoute } from "vue-router";
import { ref } from "vue";
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuItem,
    SidebarMenuButton,
    SidebarSeparator,
    useSidebar,
} from "@/components/ui/sidebar";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import {
    RiAddLine,
    RiSearchLine,
    RiLayoutLeftLine,
    RiLayoutRightLine,
    RiHome5Line,
    RiPrinterLine,
    RiSignalWifiLine,
    RiServerLine,
    RiPlugLine,
    RiBarChartLine,
    RiQuestionLine,
    RiSettings3Line,
    RiKeyLine,
    RiLogoutBoxLine,
} from "@remixicon/vue";
import type { Component } from "vue";
import { tokenStore } from "@/lib/api";
import { useNewDevice } from "@/composables/useNewDevice";

const router = useRouter();
const route = useRoute();
const { state, toggleSidebar } = useSidebar();
const { openDialog } = useNewDevice();

const isCollapsed = () => state.value === "collapsed";
const showSettingsMenu = ref(false);

const iconMap: Record<string, Component> = {
    RiPrinterLine,
    RiSignalWifiLine,
    RiServerLine,
    RiPlugLine,
    RiBarChartLine,
    RiQuestionLine,
    RiSettings3Line,
};

const devices = [
    { id: "1", name: "Demo", icon: "RiPrinterLine", online: true },
];

const footerItems = [
    { label: "Plugins", icon: "RiPlugLine", route: "/plugins" },
    { label: "Insights", icon: "RiBarChartLine", route: "/insights" },
    { label: "Help", icon: "RiQuestionLine", route: "/help" },
];

function navigate(path: string) {
    showSettingsMenu.value = false;
    router.push(path);
}

function logout() {
    tokenStore.clear();
    showSettingsMenu.value = false;
    router.replace("/login");
}

function toggleSettings() {
    showSettingsMenu.value = !showSettingsMenu.value;
}

function closeSettings() {
    showSettingsMenu.value = false;
}

async function handleAddDevice() {
    if (route.path !== "/") {
        await router.push("/");
    }
    openDialog();
}

const isSettingsActive = () =>
    route.path === "/settings" || route.path === "/credentials";
</script>

<template>
    <TooltipProvider :delay-duration="100">
        <Sidebar collapsible="icon">
            <!-- Header -->
            <SidebarHeader class="px-2 py-2 gap-1">
                <div
                    :class="
                        isCollapsed()
                            ? 'flex flex-col items-center gap-1'
                            : 'flex items-center gap-1'
                    "
                >
                    <Tooltip v-if="isCollapsed()">
                        <TooltipTrigger as-child>
                            <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0" @click="handleAddDevice" aria-label="Add device">
                                <RiAddLine class="size-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="right">Add device</TooltipContent>
                    </Tooltip>
                    <Button v-else variant="ghost" size="icon" class="h-8 w-8 shrink-0" @click="handleAddDevice" aria-label="Add device">
                        <RiAddLine class="size-4" />
                    </Button>

                    <template v-if="!isCollapsed()">
                        <Button variant="ghost" size="icon" class="h-8 w-8" aria-label="Search">
                            <RiSearchLine class="size-4" />
                        </Button>
                    </template>
                    <template v-else>
                        <Tooltip>
                            <TooltipTrigger as-child>
                                <Button variant="ghost" size="icon" class="h-8 w-8" aria-label="Search">
                                    <RiSearchLine class="size-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent side="right">Search</TooltipContent>
                        </Tooltip>
                    </template>

                    <div v-if="!isCollapsed()" class="flex-1" />

                    <Tooltip v-if="isCollapsed()">
                        <TooltipTrigger as-child>
                            <Button variant="ghost" size="icon" class="h-8 w-8" @click="toggleSidebar" aria-label="Expand sidebar">
                                <RiLayoutRightLine class="size-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="right">Expand sidebar</TooltipContent>
                    </Tooltip>
                    <Button v-else variant="ghost" size="icon" class="h-8 w-8" @click="toggleSidebar" aria-label="Collapse sidebar">
                        <RiLayoutLeftLine class="size-4" />
                    </Button>
                </div>
            </SidebarHeader>

            <SidebarSeparator class="mx-0" />

            <!-- Main content -->
            <SidebarContent class="px-2 py-2">
                <SidebarMenu>
                    <SidebarMenuItem>
                        <Tooltip v-if="isCollapsed()">
                            <TooltipTrigger as-child>
                                <SidebarMenuButton :is-active="route.path === '/'" @click="navigate('/')" aria-label="Home">
                                    <RiHome5Line class="size-4" />
                                    <span>Home</span>
                                </SidebarMenuButton>
                            </TooltipTrigger>
                            <TooltipContent side="right">Home</TooltipContent>
                        </Tooltip>
                        <SidebarMenuButton v-else :is-active="route.path === '/'" @click="navigate('/')">
                            <RiHome5Line class="size-4" />
                            <span>Home</span>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>

                <SidebarSeparator class="my-2 mx-0" />

                <SidebarMenu>
                    <SidebarMenuItem v-for="device in devices" :key="device.id">
                        <Tooltip v-if="isCollapsed()">
                            <TooltipTrigger as-child>
                                <SidebarMenuButton
                                    :is-active="route.path === `/devices/${device.id}`"
                                    @click="navigate(`/devices/${device.id}`)"
                                    :aria-label="device.name"
                                >
                                    <span class="relative inline-flex">
                                        <component :is="iconMap[device.icon]" class="size-4" />
                                        <span class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full" :class="device.online ? 'bg-green-500' : 'bg-zinc-400'" />
                                    </span>
                                    <span>{{ device.name }}</span>
                                </SidebarMenuButton>
                            </TooltipTrigger>
                            <TooltipContent side="right">
                                {{ device.name }}
                                <span class="ml-1 text-xs" :class="device.online ? 'text-green-400' : 'text-zinc-400'">
                                    {{ device.online ? "online" : "offline" }}
                                </span>
                            </TooltipContent>
                        </Tooltip>
                        <SidebarMenuButton v-else
                            :is-active="route.path === `/devices/${device.id}`"
                            @click="navigate(`/devices/${device.id}`)"
                        >
                            <span class="relative inline-flex">
                                <component :is="iconMap[device.icon]" class="size-4" />
                                <span class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full" :class="device.online ? 'bg-green-500' : 'bg-zinc-400'" />
                            </span>
                            <span>{{ device.name }}</span>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>

                <div class="flex-1" />
            </SidebarContent>

            <SidebarSeparator class="mx-0" />

            <!-- Footer -->
            <SidebarFooter class="px-2 py-2">
                <SidebarMenu>
                    <SidebarMenuItem v-for="item in footerItems" :key="item.route">
                        <Tooltip v-if="isCollapsed()">
                            <TooltipTrigger as-child>
                                <SidebarMenuButton :is-active="route.path === item.route" @click="navigate(item.route)" :aria-label="item.label">
                                    <component :is="iconMap[item.icon]" class="size-4" />
                                    <span>{{ item.label }}</span>
                                </SidebarMenuButton>
                            </TooltipTrigger>
                            <TooltipContent side="right">{{ item.label }}</TooltipContent>
                        </Tooltip>
                        <SidebarMenuButton v-else :is-active="route.path === item.route" @click="navigate(item.route)">
                            <component :is="iconMap[item.icon]" class="size-4" />
                            <span>{{ item.label }}</span>
                        </SidebarMenuButton>
                    </SidebarMenuItem>

                    <!-- Settings with popover -->
                    <SidebarMenuItem class="relative">
                        <div v-if="showSettingsMenu" class="fixed inset-0 z-40" @click="closeSettings" />

                        <Tooltip v-if="isCollapsed()">
                            <TooltipTrigger as-child>
                                <SidebarMenuButton :is-active="isSettingsActive()" @click="toggleSettings" aria-label="Settings">
                                    <RiSettings3Line class="size-4" />
                                    <span>Settings</span>
                                </SidebarMenuButton>
                            </TooltipTrigger>
                            <TooltipContent side="right">Settings</TooltipContent>
                        </Tooltip>
                        <SidebarMenuButton v-else :is-active="isSettingsActive()" @click="toggleSettings">
                            <RiSettings3Line class="size-4" />
                            <span>Settings</span>
                        </SidebarMenuButton>

                        <Transition name="popup">
                            <div
                                v-if="showSettingsMenu"
                                class="absolute bottom-full left-0 mb-1 z-50 min-w-[160px] rounded-lg border border-border bg-popover shadow-lg py-1 overflow-hidden"
                            >
                                <button @click="navigate('/settings')" class="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-foreground hover:bg-muted/70 transition-colors" :class="route.path === '/settings' ? 'bg-muted/50 font-medium' : ''">
                                    <RiSettings3Line class="size-3.5 text-muted-foreground" />
                                    Settings
                                </button>
                                <button @click="navigate('/credentials')" class="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-foreground hover:bg-muted/70 transition-colors" :class="route.path === '/credentials' ? 'bg-muted/50 font-medium' : ''">
                                    <RiKeyLine class="size-3.5 text-muted-foreground" />
                                    Credentials
                                </button>
                                <div class="my-1 h-px bg-border mx-2" />
                                <button @click="logout" class="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-destructive hover:bg-destructive/10 transition-colors">
                                    <RiLogoutBoxLine class="size-3.5" />
                                    Logout
                                </button>
                            </div>
                        </Transition>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    </TooltipProvider>
</template>

<style scoped>
.popup-enter-active,
.popup-leave-active {
    transition: opacity 0.1s ease, transform 0.1s ease;
}
.popup-enter-from,
.popup-leave-to {
    opacity: 0;
    transform: translateY(4px);
}
</style>