<script setup lang="ts">
import { useRouter, useRoute } from "vue-router";
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
} from "@remixicon/vue";
import type { Component } from "vue";

const router = useRouter();
const route = useRoute();
const { state, toggleSidebar } = useSidebar();

const isCollapsed = () => state.value === "collapsed";

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
    { label: "Settings", icon: "RiSettings3Line", route: "/settings" },
];

function navigate(path: string) {
    router.push(path);
}
</script>

<template>
    <TooltipProvider :delay-duration="100">
        <Sidebar collapsible="icon">
        <!-- Header: + Search Collapse -->
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
                        <Button
                            variant="ghost"
                            size="icon"
                            class="h-8 w-8 shrink-0"
                            @click="navigate('/')"
                            aria-label="Add device"
                        >
                            <RiAddLine class="size-4" />
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent side="right">Add device</TooltipContent>
                </Tooltip>
                <Button
                    v-else
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8 shrink-0"
                    @click="navigate('/')"
                    aria-label="Add device"
                >
                    <RiAddLine class="size-4" />
                </Button>
        
                <template v-if="!isCollapsed()">
                    <Button
                        variant="ghost"
                        size="icon"
                        class="h-8 w-8"
                        aria-label="Search"
                    >
                        <RiSearchLine class="size-4" />
                    </Button>
                </template>
                <template v-else>
                    <Tooltip>
                        <TooltipTrigger as-child>
                            <Button
                                variant="ghost"
                                size="icon"
                                class="h-8 w-8"
                                aria-label="Search"
                            >
                                <RiSearchLine class="size-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="right">Search</TooltipContent>
                    </Tooltip>
                </template>
        
                <div v-if="!isCollapsed()" class="flex-1" />
        
                <Tooltip v-if="isCollapsed()">
                    <TooltipTrigger as-child>
                        <Button
                            variant="ghost"
                            size="icon"
                            class="h-8 w-8"
                            @click="toggleSidebar"
                            aria-label="Expand sidebar"
                        >
                            <RiLayoutRightLine class="size-4" />
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent side="right">Expand sidebar</TooltipContent>
                </Tooltip>
                <Button v-else
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8"
                    @click="toggleSidebar"
                    aria-label="Collapse sidebar"
                >
                    <RiLayoutLeftLine class="size-4" />
                </Button>
            </div>
        </SidebarHeader>
    
        <SidebarSeparator class="mx-0" />
    
        <!-- Main content: Home + Devices -->
        <SidebarContent class="px-2 py-2">
            <!-- Home -->
            <SidebarMenu>
                <SidebarMenuItem>
                    <Tooltip v-if="isCollapsed()">
                        <TooltipTrigger as-child>
                            <SidebarMenuButton
                                :is-active="route.path === '/'"
                                @click="navigate('/')"
                                aria-label="Home"
                            >
                                <RiHome5Line class="size-4" />
                                <span>Home</span>
                            </SidebarMenuButton>
                        </TooltipTrigger>
                        <TooltipContent side="right">Home</TooltipContent>
                    </Tooltip>
                    <SidebarMenuButton
                        v-else
                        :is-active="route.path === '/'"
                        @click="navigate('/')"
                    >
                        <RiHome5Line class="size-4" />
                        <span>Home</span>
                    </SidebarMenuButton>
                </SidebarMenuItem>
            </SidebarMenu>
    
            <SidebarSeparator class="my-2 mx-0" />
    
            <!-- Devices -->
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
                                <span
                                    class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full"
                                    :class="device.online ? 'bg-green-500' : 'bg-zinc-400'"
                                />
                            </span>
                            <span>{{ device.name }}</span>
                            </SidebarMenuButton>
                        </TooltipTrigger>
                        <TooltipContent side="right">
                            {{ device.name }}
                            <span
                                class="ml-1 text-xs"
                                :class="device.online ? 'text-green-400' : 'text-zinc-400'"
                            >
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
                            <span
                                class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full"
                                :class="device.online ? 'bg-green-500' : 'bg-zinc-400'"
                            />
                        </span>
                        <span>{{ device.name }}</span>
                    </SidebarMenuButton>
                </SidebarMenuItem>
            </SidebarMenu>
    
            <!-- Spacer -->
            <div class="flex-1" />
        </SidebarContent>
    
        <!-- Footer: Plugins, Insights, Help, Settings -->
        <SidebarSeparator class="mx-0" />
        <SidebarFooter class="px-2 py-2">
            <SidebarMenu>
                <SidebarMenuItem v-for="item in footerItems" :key="item.route">
                    <Tooltip v-if="isCollapsed()">
                        <TooltipTrigger as-child>
                            <SidebarMenuButton
                                :is-active="route.path === item.route"
                                @click="navigate(item.route)"
                                :aria-label="item.label"
                            >
                                <component :is="iconMap[item.icon]" class="size-4" />
                                <span>{{ item.label }}</span>
                            </SidebarMenuButton>
                        </TooltipTrigger>
                        <TooltipContent side="right">{{ item.label }}</TooltipContent>
                    </Tooltip>
                    <SidebarMenuButton
                        v-else
                        :is-active="route.path === item.route"
                        @click="navigate(item.route)"
                    >
                        <component :is="iconMap[item.icon]" class="size-4" />
                        <span>{{ item.label }}</span>
                    </SidebarMenuButton>
                </SidebarMenuItem>
            </SidebarMenu>
        </SidebarFooter>
        </Sidebar>
    </TooltipProvider>
</template>
