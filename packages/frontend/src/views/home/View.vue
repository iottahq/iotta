<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useNewDevice } from "@/composables/useNewDevice";
import { useRouter } from "vue-router";
import { api, type Device, type Group, ApiError, fetchAssetBlobUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { RiAlertLine } from "@remixicon/vue";
import NewGroupDialog from "./group/NewDialog.vue";
import EditGroupDialog from "./group/EditDialog.vue";
import DeleteGroupDialog from "./group/DeleteDialog.vue";
import TokenSheet from "./group/TokenSheet.vue";
import NewDeviceDialog from "./device/NewDialog.vue";
import EditDeviceDialog from "./device/EditDialog.vue";
import NewCredentialDialog from "@/views/credentials/NewDialog.vue";
import ContextMenu from "./ContextMenu.vue";
import type { ContextMenuItem } from "./ContextMenu.vue";
import {
    RiAddLine,
    RiArrowDownSLine,
    RiArrowRightSLine,
    RiDeleteBinLine,
    RiDraggable,
    RiExternalLinkLine,
    RiGroupLine,
    RiLayoutGridLine,
    RiListCheck2,
    RiLoader4Line,
    RiErrorWarningLine,
    RiPencilLine,
    RiPlugLine,
    RiShieldLine,
    RiPrinterLine,
    RiSearchLine,
    RiServerLine,
} from "@remixicon/vue";

import type { Component } from "vue";

const router = useRouter();
const { open: newDeviceOpen, targetGroupId: newDeviceComposableGroupId, closeDialog: closeNewDeviceComposable } = useNewDevice();

interface DeviceWithStatus extends Device {
    online?: boolean | null;
}

interface GroupSection {
    group: Group;
    devices: DeviceWithStatus[];
    collapsed: boolean;
}

const viewMode = ref<"grid" | "list">("grid");
const search = ref("");
const loading = ref(true);
const error = ref<string | null>(null);

const devices = ref<DeviceWithStatus[]>([]);
const groups = ref<Group[]>([]);
const sections = ref<GroupSection[]>([]);

const dragging = ref<string | null>(null);
const dragOverGroup = ref<string | null>(null);
const hoveredSection = ref<number | null>(null);
const contextMenu = ref<{ x: number; y: number; items: ContextMenuItem[] } | null>(null);

const deleteDeviceTarget = ref<DeviceWithStatus | null>(null);
const deletingDevice = ref(false);
const deleteDeviceError = ref<string | null>(null);

const showNewGroup = ref(false);
const newGroupName = ref("");
const savingGroup = ref(false);
const groupError = ref<string | null>(null);

const showNewDevice = ref(false);
const showEditDevice = ref(false);
const editDeviceTarget = ref<DeviceWithStatus | null>(null);
const newDeviceTargetGroup = ref<string | null>(null);
const newDeviceName = ref("");
const newDevicePlugin = ref("");
const newDeviceCredential = ref("");
const savingDevice = ref(false);
const deviceError = ref<string | null>(null);

const creatingGroupInline = ref(false);
const createGroupInlineError = ref<string | null>(null);

const plugins = ref<{ id: string; name: string }[]>([]);
const credentials = ref<{ id: string; name: string }[]>([]);

const showNewCredential = ref(false);
const credentialTemplates = ref<{ id: string; name: string; fields: { field: string; type: string; label: string }[] }[]>([]);
const creatingCredential = ref(false);
const credentialError = ref<string | null>(null);

const editGroup = ref<Group | null>(null);
const editGroupName = ref("");
const savingGroupName = ref(false);
const deletingGroup = ref(false);
const deleteGroupTarget = ref<Group | null>(null);
const editGroupError = ref<string | null>(null);
const confirmDeleteGroup = ref(false);
const showTokenSheet = ref(false);
const tokenSheetGroup = ref<Group | null>(null);
const coveredDeviceIds = ref<Set<string>>(new Set());

const pluginIconMap: Record<string, Component> = {
    "bambu-lab-a1": RiPrinterLine,
};

function getFallbackIcon(pluginId: string): Component {
    return pluginIconMap[pluginId] ?? RiServerLine;
}

const pluginBlobIcons = ref<Map<string, string>>(new Map());

async function loadPluginIcons(pluginIds: string[]) {
    pluginBlobIcons.value.forEach((url) => URL.revokeObjectURL(url));
    const map = new Map<string, string>();
    await Promise.allSettled(
        pluginIds.map(async (id) => {
            try {
                map.set(id, await fetchAssetBlobUrl(`/plugins/devices/${id}/assets/icon`));
            } catch { /* no icon */ }
        }),
    );
    pluginBlobIcons.value = map;
}

onUnmounted(() => {
    pluginBlobIcons.value.forEach((url) => URL.revokeObjectURL(url));
});

async function load() {
    loading.value = true;
    error.value = null;
    try {
        const [devList, grpList] = await Promise.all([
            api.devices.list(),
            api.groups.list(),
        ]);
        groups.value = grpList;
        devices.value = devList.map((d) => ({ ...d, online: null }));
        buildSections();
        pingAll();
        const uniquePluginIds = [...new Set(devList.map((d) => d.plugin_id))];
        loadPluginIcons(uniquePluginIds);
        loadCoveredDevices(grpList.map((g) => g.id));
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to load";
    } finally {
        loading.value = false;
    }
}

async function loadCoveredDevices(groupIds: string[]) {
    const results = await Promise.allSettled(groupIds.map((id) => api.tokens.list(id)));
    const ids = new Set<string>();
    for (const r of results) {
        if (r.status === "fulfilled") {
            for (const token of r.value) {
                for (const td of token.devices) ids.add(td.device_id);
            }
        }
    }
    coveredDeviceIds.value = ids;
}

function buildSections() {
    const grouped: Record<string, DeviceWithStatus[]> = {};
    for (const d of devices.value) {
        if (!grouped[d.group_id]) grouped[d.group_id] = [];
        grouped[d.group_id].push(d);
    }
    const result: GroupSection[] = [];
    for (const g of groups.value) {
        const existing = sections.value.find((s) => s.group.id === g.id);
        result.push({ group: g, devices: grouped[g.id] ?? [], collapsed: existing?.collapsed ?? false });
    }
    sections.value = result;
}

async function pingAll() {
    for (const d of devices.value) {
        try {
            const result = await api.devices.ping(d.id);
            const dev = devices.value.find((x) => x.id === d.id);
            if (dev) dev.online = result.online;
            buildSections();
        } catch {
            const dev = devices.value.find((x) => x.id === d.id);
            if (dev) dev.online = false;
        }
    }
}

onMounted(async () => {
    await load();
    try {
        const [p, c] = await Promise.all([
            api.plugins.devices.list(),
            api.credentials.list(),
        ]);
        plugins.value = p.items.map((x) => ({ id: x.id, name: x.name }));
        credentials.value = c.map((x) => ({ id: x.id, name: x.name }));

        const templateList: typeof credentialTemplates.value = [];
        for (const plugin of p.items) {
            const detail = await api.plugins.devices.get(plugin.id).catch(() => null);
            if (!detail) continue;
            const credFields = (detail as any)._credentials;
            if (Array.isArray(credFields) && credFields.length > 0) {
                templateList.push({ id: plugin.id, name: plugin.name, fields: credFields });
            }
        }
        credentialTemplates.value = templateList;
    } catch {}
});

watch(newDeviceOpen, (val) => {
    if (val) {
        const groupId = newDeviceComposableGroupId.value;
        closeNewDeviceComposable();
        openNewDevice(groupId);
    }
});

const filteredSections = computed(() => {
    const q = search.value.toLowerCase().trim();
    if (!q) return sections.value;
    return sections.value
        .map((s) => {
            const groupMatches = s.group.name.toLowerCase().includes(q);
            const matchedDevices = groupMatches
                ? s.devices
                : s.devices.filter((d) => d.name.toLowerCase().includes(q));
            if (!groupMatches && matchedDevices.length === 0) return null;
            return { ...s, devices: matchedDevices, collapsed: false };
        })
        .filter((s): s is GroupSection => s !== null);
});

function toggleSection(idx: number) {
    sections.value[idx].collapsed = !sections.value[idx].collapsed;
}

function onGroupContextMenu(e: MouseEvent, section: GroupSection) {
    const group = section.group;
    contextMenu.value = {
        x: e.clientX, y: e.clientY,
        items: [
            { label: "Edit", icon: RiPencilLine, action: () => openEditGroup(group) },
            { label: "Tokens", icon: RiShieldLine, action: () => { tokenSheetGroup.value = group; showTokenSheet.value = true; } },
            { label: "", separator: true, action: () => {} },
            { label: "Delete", icon: RiDeleteBinLine, variant: "destructive", action: () => { deleteGroupTarget.value = group; } },
        ],
    };
}

function onDeviceContextMenu(e: MouseEvent, device: DeviceWithStatus) {
    e.preventDefault();
    e.stopPropagation();
    contextMenu.value = {
        x: e.clientX, y: e.clientY,
        items: [
            { label: "Open", icon: RiExternalLinkLine, action: () => router.push(`/devices/${device.id}`) },
            { label: "Edit", icon: RiPencilLine, action: () => openEditDevice(device) },
            { label: "", separator: true, action: () => { } },
            { label: "Delete", icon: RiDeleteBinLine, variant: "destructive", action: () => { deleteDeviceTarget.value = device; } },
        ],
    };
}

async function confirmDeleteDevice() {
    if (!deleteDeviceTarget.value) return;
    deletingDevice.value = true;
    deleteDeviceError.value = null;
    try {
        await api.devices.delete(deleteDeviceTarget.value.id);
        devices.value = devices.value.filter((d) => d.id !== deleteDeviceTarget.value!.id);
        buildSections();
        deleteDeviceTarget.value = null;
    } catch (e) {
        deleteDeviceError.value = e instanceof ApiError ? e.detail : "Failed to delete";
    } finally {
        deletingDevice.value = false;
    }
}

async function createGroup() {
    if (!newGroupName.value.trim()) return;
    savingGroup.value = true;
    groupError.value = null;
    try {
        const g = await api.groups.create({ name: newGroupName.value.trim() });
        groups.value.push({ id: g.id, name: g.name });
        buildSections();
        showNewGroup.value = false;
        newGroupName.value = "";
        newDeviceTargetGroup.value = g.id;
    } catch (e) {
        groupError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        savingGroup.value = false;
    }
}

async function createGroupInline(name: string) {
    creatingGroupInline.value = true;
    createGroupInlineError.value = null;
    try {
        const g = await api.groups.create({ name });
        groups.value.push({ id: g.id, name: g.name });
        buildSections();
        newDeviceTargetGroup.value = g.id;
    } catch (e) {
        createGroupInlineError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        creatingGroupInline.value = false;
    }
}

function openNewGroupFromDevice() {
    newGroupName.value = "";
    groupError.value = null;
    showNewGroup.value = true;
}

function openNewCredentialFromDevice() {
    credentialError.value = null;
    showNewCredential.value = true;
}

async function createCredential(name: string, data: Record<string, string>) {
    creatingCredential.value = true;
    credentialError.value = null;
    try {
        const cred = await api.credentials.create({ name, data });
        credentials.value.push({ id: cred.id, name: cred.name });
        newDeviceCredential.value = cred.id;
        showNewCredential.value = false;
    } catch (e) {
        credentialError.value = e instanceof ApiError ? e.detail : "Failed to create credential";
    } finally {
        creatingCredential.value = false;
    }
}

function openEditGroup(group: Group) {
    editGroup.value = group;
    editGroupName.value = group.name;
    editGroupError.value = null;
}

function openEditDevice(device: DeviceWithStatus) {
    editDeviceTarget.value = device;
    newDeviceTargetGroup.value = device.group_id;
    newDeviceName.value = device.name;
    newDevicePlugin.value = device.plugin_id;
    newDeviceCredential.value = device.credential_id ?? credentials.value[0]?.id ?? "";
    deviceError.value = null;
    createGroupInlineError.value = null;
    showEditDevice.value = true;
}

function closeEditGroup() {
    editGroup.value = null;
    confirmDeleteGroup.value = false;
}

async function saveGroupName() {
    if (!editGroup.value || !editGroupName.value.trim()) return;
    savingGroupName.value = true;
    editGroupError.value = null;
    try {
        const updated = await api.groups.update(editGroup.value.id, { name: editGroupName.value.trim() });
        const g = groups.value.find((x) => x.id === updated.id);
        if (g) g.name = updated.name;
        editGroup.value = { ...editGroup.value, name: updated.name };
        buildSections();
    } catch (e) {
        editGroupError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        savingGroupName.value = false;
    }
}

async function deleteGroup() {
    const target = deleteGroupTarget.value ?? editGroup.value;
    if (!target) return;
    deletingGroup.value = true;
    try {
        const groupDevices = devices.value.filter((d) => d.group_id === target.id);
        await Promise.all(groupDevices.map((d) => api.devices.delete(d.id)));
        devices.value = devices.value.filter((d) => d.group_id !== target.id);
        await api.groups.delete(target.id);
        groups.value = groups.value.filter((g) => g.id !== target.id);
        buildSections();
        deleteGroupTarget.value = null;
        closeEditGroup();
    } catch (e) {
        editGroupError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        deletingGroup.value = false;
    }
}

function openNewDevice(groupId: string | null) {
    newDeviceTargetGroup.value = groupId ?? (groups.value[0]?.id ?? null);
    newDeviceName.value = "";
    newDevicePlugin.value = plugins.value[0]?.id ?? "";
    newDeviceCredential.value = credentials.value[0]?.id ?? "";
    deviceError.value = null;
    createGroupInlineError.value = null;
    showNewDevice.value = true;
}

async function createDevice() {
    if (!newDeviceName.value.trim() || !newDevicePlugin.value || !newDeviceCredential.value || !newDeviceTargetGroup.value) return;
    savingDevice.value = true;
    deviceError.value = null;
    try {
        const d = await api.devices.create({
            name: newDeviceName.value.trim(),
            plugin_id: newDevicePlugin.value,
            credential_id: newDeviceCredential.value,
            group_id: newDeviceTargetGroup.value,
        });
        devices.value.push({ ...d, online: null });
        buildSections();
        showNewDevice.value = false;
        try {
            const result = await api.devices.ping(d.id);
            const dev = devices.value.find((x) => x.id === d.id);
            if (dev) { dev.online = result.online; buildSections(); }
        } catch {}
    } catch (e) {
        deviceError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        savingDevice.value = false;
    }
}

async function updateDevice() {
    if (!editDeviceTarget.value || !newDeviceName.value.trim() || !newDevicePlugin.value || !newDeviceCredential.value || !newDeviceTargetGroup.value) return;
    savingDevice.value = true;
    deviceError.value = null;
    try {
        const updated = await api.devices.update(editDeviceTarget.value.id, {
            name: newDeviceName.value.trim(),
            plugin_id: newDevicePlugin.value,
            credential_id: newDeviceCredential.value,
            group_id: newDeviceTargetGroup.value,
        });
        const dev = devices.value.find((d) => d.id === updated.id);
        if (dev) Object.assign(dev, updated);
        buildSections();
        showEditDevice.value = false;
        editDeviceTarget.value = null;
    } catch (e) {
        deviceError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        savingDevice.value = false;
    }
}

function onDragStart(deviceId: string) { dragging.value = deviceId; }
function onDragOver(e: DragEvent, groupId: string) { e.preventDefault(); dragOverGroup.value = groupId; }
function onDragLeave() { dragOverGroup.value = null; }
async function onDrop(e: DragEvent, groupId: string) {
    e.preventDefault();
    dragOverGroup.value = null;
    if (!dragging.value) return;
    const deviceId = dragging.value;
    dragging.value = null;
    const dev = devices.value.find((d) => d.id === deviceId);
    if (!dev || dev.group_id === groupId) return;
    const old = dev.group_id;
    dev.group_id = groupId;
    buildSections();
    try { await api.devices.update(deviceId, { group_id: groupId }); }
    catch { dev.group_id = old; buildSections(); }
}
function onDragEnd() { dragging.value = null; dragOverGroup.value = null; }
function sectionKey(s: GroupSection) { return s.group.id; }
function isDragTarget(s: GroupSection) {
    return dragOverGroup.value === s.group.id && dragging.value !== null;
}
</script>

<template>
    <div class="flex flex-col h-full">
        <div class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border">
            <div>
                <h1 class="text-sm font-semibold">Devices</h1>
                <p class="text-xs text-muted-foreground mt-0.5">Manage your connected devices</p>
            </div>
            <div class="flex items-center gap-px bg-muted rounded-md p-0.5">
                <button @click="viewMode = 'grid'" :class="['flex items-center justify-center w-7 h-7 rounded text-xs transition-colors', viewMode === 'grid' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground']" aria-label="Grid view">
                    <RiLayoutGridLine class="size-3.5" />
                </button>
                <button @click="viewMode = 'list'" :class="['flex items-center justify-center w-7 h-7 rounded text-xs transition-colors', viewMode === 'list' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground']" aria-label="List view">
                    <RiListCheck2 class="size-3.5" />
                </button>
            </div>
        </div>

        <div class="relative flex items-center px-6 py-3 border-b border-border">
            <div class="flex-1" />
            <div class="relative w-64">
                <RiSearchLine class="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
                <Input v-model="search" placeholder="Search…" class="pl-7 h-7 text-xs w-full" />
            </div>
            <div class="flex-1 flex items-center justify-end gap-2">
                <Button variant="outline" size="sm" class="gap-1.5" @click="showNewGroup = true">
                    <RiGroupLine class="size-3.5" />
                    New group
                </Button>
            </div>
        </div>

        <div class="flex-1 overflow-auto px-6 py-4 flex flex-col gap-4">
            <div v-if="loading" class="flex items-center justify-center py-16 text-muted-foreground">
                <RiLoader4Line class="size-5 animate-spin mr-2" />
                <span class="text-xs">Loading devices…</span>
            </div>

            <div v-else-if="error" class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs">
                <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
                {{ error }}
            </div>

            <template v-else>
                <div
                    v-for="(section, idx) in filteredSections"
                    :key="sectionKey(section)"
                    class="flex flex-col gap-2"
                    @mouseenter="hoveredSection = idx"
                    @mouseleave="hoveredSection = null"
                    @dragover="onDragOver($event, section.group.id)"
                    @dragleave="onDragLeave"
                    @drop="onDrop($event, section.group.id)"
                >
                    <div
                        class="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50 select-none"
                        :class="isDragTarget(section) ? 'bg-primary/10 ring-1 ring-primary/30' : ''"
                        @contextmenu.prevent="onGroupContextMenu($event, section)"
                    >
                        <button class="flex items-center gap-1.5 text-xs font-medium text-foreground min-w-0 flex-1" @click="toggleSection(idx)" @contextmenu.prevent.stop="onGroupContextMenu($event, section)">
                            <component :is="section.collapsed ? RiArrowRightSLine : RiArrowDownSLine" class="size-3.5 text-muted-foreground shrink-0" />
                            <span class="truncate">{{ section.group.name }}</span>
                            <span class="text-muted-foreground font-normal tabular-nums">{{ section.devices.length }}</span>
                        </button>
                        <div class="flex items-center gap-0.5 shrink-0" :style="{ opacity: hoveredSection === idx ? '1' : '0', transition: 'opacity 0.15s ease' }">
                            <Button variant="ghost" size="icon" class="size-6" @click.stop="openEditGroup(section.group)">
                                <RiPencilLine class="size-3.5" />
                            </Button>
                            <Button variant="ghost" size="icon" class="size-6" @click="openNewDevice(section.group.id)">
                                <RiAddLine class="size-3.5" />
                            </Button>
                        </div>
                    </div>

                    <div
                        v-if="!section.collapsed"
                        :class="[viewMode === 'grid' ? 'grid gap-2' : 'flex flex-col gap-1.5']"
                        :style="viewMode === 'grid' ? 'grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))' : ''"
                    >
                        <div
                            v-if="section.devices.length === 0"
                            :class="['flex items-center justify-center rounded-lg border border-dashed border-border text-xs text-muted-foreground transition-colors', viewMode === 'grid' ? 'h-24 col-span-full' : 'h-12', isDragTarget(section) ? 'border-primary/50 bg-primary/5 text-primary' : '']"
                        >
                            {{ isDragTarget(section) ? "Drop here" : "No devices" }}
                        </div>

                        <div
                            v-for="device in section.devices"
                            :key="device.id"
                            :draggable="true"
                            @dragstart="onDragStart(device.id)"
                            @dragend="onDragEnd"
                            @click="router.push(`/devices/${device.id}`)"
                            @contextmenu="onDeviceContextMenu($event, device)"
                            :class="['group flex cursor-pointer rounded-lg border border-border bg-card transition-all hover:border-primary/40 hover:shadow-sm', dragging === device.id ? 'opacity-40 scale-95' : '', viewMode === 'grid' ? 'flex-col overflow-hidden' : 'flex-row items-center gap-3 px-3 py-2']"
                        >
                            <div v-if="viewMode === 'grid'" class="flex items-center justify-center h-28 bg-muted/30 border-b border-border relative">
                                <img v-if="pluginBlobIcons.get(device.plugin_id)" :src="pluginBlobIcons.get(device.plugin_id)" class="size-16 object-contain" />
                                <component v-else :is="getFallbackIcon(device.plugin_id)" class="size-10 text-muted-foreground/40" />
                                <div class="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground cursor-grab">
                                    <RiDraggable class="size-3.5" />
                                </div>
                                <span class="absolute top-2 right-2 block size-2 rounded-full" :class="device.online === null ? 'bg-muted-foreground/30 animate-pulse' : device.online ? 'bg-emerald-500' : 'bg-zinc-400'" />
                            </div>
                            <div v-if="viewMode === 'grid'" class="flex items-center gap-1.5 px-3 py-2.5">
                                <div class="flex flex-col gap-0.5 flex-1 min-w-0">
                                    <span class="text-xs font-semibold text-foreground truncate">{{ device.name }}</span>
                                    <span class="text-[10px] text-muted-foreground font-mono truncate">{{ device.plugin_id }}</span>
                                </div>
                                <TooltipProvider v-if="!coveredDeviceIds.has(device.id)" :delay-duration="100">
                                    <Tooltip>
                                        <TooltipTrigger as-child>
                                            <RiAlertLine class="size-3.5 text-amber-500 shrink-0" />
                                        </TooltipTrigger>
                                        <TooltipContent side="top">
                                            <p class="text-xs">No token assigned — this device is not accessible via API</p>
                                        </TooltipContent>
                                    </Tooltip>
                                </TooltipProvider>
                            </div>

                            <img v-if="viewMode === 'list' && pluginBlobIcons.get(device.plugin_id)" :src="pluginBlobIcons.get(device.plugin_id)" class="size-4 object-contain shrink-0" />
                            <component v-else-if="viewMode === 'list'" :is="getFallbackIcon(device.plugin_id)" class="size-4 text-muted-foreground shrink-0" />
                            <div v-if="viewMode === 'list'" class="flex-1 min-w-0 flex items-center gap-2">
                                <span class="text-xs font-medium text-foreground truncate">{{ device.name }}</span>
                                <span class="text-[10px] text-muted-foreground font-mono truncate hidden sm:block">{{ device.plugin_id }}</span>
                            </div>
                            <div v-if="viewMode === 'list'" class="flex items-center gap-2 shrink-0">
                                <TooltipProvider v-if="!coveredDeviceIds.has(device.id)" :delay-duration="100">
                                    <Tooltip>
                                        <TooltipTrigger as-child>
                                            <RiAlertLine class="size-3.5 text-amber-500" />
                                        </TooltipTrigger>
                                        <TooltipContent side="top">
                                            <p class="text-xs">No token assigned — this device is not accessible via API</p>
                                        </TooltipContent>
                                    </Tooltip>
                                </TooltipProvider>
                                <span class="block size-1.5 rounded-full" :class="device.online === null ? 'bg-muted-foreground/30 animate-pulse' : device.online ? 'bg-emerald-500' : 'bg-zinc-400'" />
                                <div class="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground cursor-grab">
                                    <RiDraggable class="size-3.5" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-if="sections.length === 0" class="flex flex-col items-center justify-center py-20 text-center gap-3">
                    <RiPlugLine class="size-10 text-muted-foreground/30" />
                    <div>
                        <p class="text-xs font-medium text-foreground">No devices yet</p>
                        <p class="text-xs text-muted-foreground mt-0.5">Create a group and add your first device</p>
                    </div>
                    <Button size="sm" class="gap-1.5 mt-1" @click="openNewDevice(null)">
                        <RiAddLine class="size-3.5" />
                        New device
                    </Button>
                </div>

                <div v-else-if="filteredSections.length === 0" class="flex flex-col items-center justify-center py-20 text-center gap-2">
                    <RiSearchLine class="size-8 text-muted-foreground/30" />
                    <p class="text-xs text-muted-foreground">No results for <span class="font-medium text-foreground">"{{ search }}"</span></p>
                </div>
            </template>
        </div>
    </div>

    <ContextMenu v-if="contextMenu" :x="contextMenu.x" :y="contextMenu.y" :items="contextMenu.items" @close="contextMenu = null" />

    <Teleport to="body">
        <Transition name="fade">
            <div v-if="deleteDeviceTarget" class="fixed inset-0 z-[60] flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50" @click="deleteDeviceTarget = null" />
                <div class="relative z-10 w-full max-w-xs rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4">
                    <h2 class="text-sm font-semibold">Delete device?</h2>
                    <p class="text-xs text-muted-foreground mt-1.5">
                        <span class="font-medium text-foreground">{{ deleteDeviceTarget.name }}</span>
                        will be permanently deleted and disconnected.
                    </p>
                    <div v-if="deleteDeviceError" class="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs">
                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        {{ deleteDeviceError }}
                    </div>
                    <div class="flex gap-2 justify-end mt-4">
                        <Button variant="outline" size="sm" @click="deleteDeviceTarget = null">Cancel</Button>
                        <Button variant="destructive" size="sm" class="gap-1.5" :disabled="deletingDevice" @click="confirmDeleteDevice">
                            <RiLoader4Line v-if="deletingDevice" class="size-3.5 animate-spin" />
                            <RiDeleteBinLine v-else class="size-3.5" />
                            Delete
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>

    <NewGroupDialog :show="showNewGroup" :name="newGroupName" :saving="savingGroup" :error="groupError" @update:show="showNewGroup = $event" @update:name="newGroupName = $event" @create="createGroup" />

    <NewDeviceDialog
        :show="showNewDevice"
        :target-group-id="newDeviceTargetGroup"
        :name="newDeviceName"
        :plugin="newDevicePlugin"
        :credential="newDeviceCredential"
        :saving="savingDevice"
        :error="deviceError"
        :plugins="plugins"
        :credentials="credentials"
        :groups="groups"
        :creating-group="creatingGroupInline"
        :create-group-error="createGroupInlineError"
        @update:show="showNewDevice = $event"
        @update:name="newDeviceName = $event"
        @update:plugin="newDevicePlugin = $event"
        @update:credential="newDeviceCredential = $event"
        @update:target-group-id="newDeviceTargetGroup = $event"
        @create="createDevice"
        @open-new-credential="openNewCredentialFromDevice"
        @open-new-group="openNewGroupFromDevice"
    />

    <EditDeviceDialog
        :show="showEditDevice"
        :target-group-id="newDeviceTargetGroup"
        :name="newDeviceName"
        :plugin="newDevicePlugin"
        :credential="newDeviceCredential"
        :saving="savingDevice"
        :error="deviceError"
        :plugins="plugins"
        :credentials="credentials"
        :groups="groups"
        :creating-group="creatingGroupInline"
        :create-group-error="createGroupInlineError"
        @update:show="showEditDevice = $event"
        @update:name="newDeviceName = $event"
        @update:plugin="newDevicePlugin = $event"
        @update:credential="newDeviceCredential = $event"
        @update:target-group-id="newDeviceTargetGroup = $event"
        @save="updateDevice"
        @open-new-credential="openNewCredentialFromDevice"
        @open-new-group="openNewGroupFromDevice"
    />

    <NewCredentialDialog
        :show="showNewCredential"
        :saving="creatingCredential"
        :error="credentialError"
        :templates="credentialTemplates"
        style="z-index: 60"
        @update:show="showNewCredential = $event"
        @create="createCredential"
    />

    <EditGroupDialog
        :group="editGroup"
        :name="editGroupName"
        :saving-name="savingGroupName"
        :error="editGroupError"
        @update:name="editGroupName = $event"
        @save-name="saveGroupName"
        @manage-tokens="tokenSheetGroup = editGroup; showTokenSheet = true"
        @close="closeEditGroup"
        @delete="confirmDeleteGroup = true"
    />

    <TokenSheet
        :group-id="showTokenSheet ? tokenSheetGroup?.id ?? null : null"
        :group-name="tokenSheetGroup?.name ?? ''"
        :devices="devices.filter((d) => d.group_id === tokenSheetGroup?.id)"
        @close="showTokenSheet = false; tokenSheetGroup = null; loadCoveredDevices(groups.map(g => g.id))"
    />

    <DeleteGroupDialog
        :show="confirmDeleteGroup || !!deleteGroupTarget"
        :group="deleteGroupTarget ?? editGroup"
        :deleting="deletingGroup"
        :device-count="devices.filter((d) => d.group_id === (deleteGroupTarget ?? editGroup)?.id).length"
        @cancel="deleteGroupTarget = null; confirmDeleteGroup = false"
        @confirm="deleteGroup"
    />
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>