<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { api, type Device, type Group, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import NewGroupDialog from "./group/NewDialog.vue";
import EditGroupDialog from "./group/EditDialog.vue";
import DeleteGroupDialog from "./group/DeleteDialog.vue";
import NewDeviceDialog from "./device/NewDialog.vue";
import {
    RiAddLine,
    RiArrowDownSLine,
    RiArrowRightSLine,
    RiDraggable,
    RiGroupLine,
    RiLayoutGridLine,
    RiListCheck2,
    RiLoader4Line,
    RiErrorWarningLine,
    RiPencilLine,
    RiPlugLine,
    RiPrinterLine,
    RiSearchLine,
    RiServerLine,
} from "@remixicon/vue";
import type { Component } from "vue";

const router = useRouter();

// ── Types ──────────────────────────────────────────────────────────────────────

interface DeviceWithStatus extends Device {
    online?: boolean | null;
}

interface GroupSection {
    group: Group | null;
    devices: DeviceWithStatus[];
    collapsed: boolean;
}

// ── State ──────────────────────────────────────────────────────────────────────

const viewMode = ref<"grid" | "list">("grid");
const search = ref("");
const loading = ref(true);
const error = ref<string | null>(null);

const devices = ref<DeviceWithStatus[]>([]);
const groups = ref<Group[]>([]);
const sections = ref<GroupSection[]>([]);

// Drag & drop
const dragging = ref<string | null>(null);
const dragOverGroup = ref<string | null>(null);

// New group dialog
const showNewGroup = ref(false);
const newGroupName = ref("");
const savingGroup = ref(false);
const groupError = ref<string | null>(null);

// New device dialog
const showNewDevice = ref(false);
const newDeviceTargetGroup = ref<string | null>(null);
const newDeviceName = ref("");
const newDevicePlugin = ref("");
const newDeviceCredential = ref("");
const savingDevice = ref(false);
const deviceError = ref<string | null>(null);

const plugins = ref<{ id: string; name: string }[]>([]);
const credentials = ref<{ id: string; name: string }[]>([]);

// Edit group dialog
const editGroup = ref<Group | null>(null);
const editGroupName = ref("");
const savingGroupName = ref(false);
const groupToken = ref<string | null>(null);
const loadingToken = ref(false);
const rotatingToken = ref(false);
const tokenCopied = ref(false);
const deletingGroup = ref(false);
const editGroupError = ref<string | null>(null);
const confirmDeleteGroup = ref(false);

// ── Plugin icon map ────────────────────────────────────────────────────────────

const pluginIconMap: Record<string, Component> = {
    "bambu-lab-a1": RiPrinterLine,
};

function getPluginIcon(pluginId: string): Component {
    return pluginIconMap[pluginId] ?? RiServerLine;
}

// ── Data fetching ──────────────────────────────────────────────────────────────

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
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to load";
    } finally {
        loading.value = false;
    }
}

function buildSections() {
    const grouped: Record<string, DeviceWithStatus[]> = {};
    const ungrouped: DeviceWithStatus[] = [];

    for (const d of devices.value) {
        if (d.group_id) {
            if (!grouped[d.group_id]) grouped[d.group_id] = [];
            grouped[d.group_id].push(d);
        } else {
            ungrouped.push(d);
        }
    }

    const result: GroupSection[] = [];
    for (const g of groups.value) {
        const existing = sections.value.find((s) => s.group?.id === g.id);
        result.push({
            group: g,
            devices: grouped[g.id] ?? [],
            collapsed: existing?.collapsed ?? false,
        });
    }
    if (ungrouped.length > 0 || groups.value.length === 0) {
        const existing = sections.value.find((s) => s.group === null);
        result.push({
            group: null,
            devices: ungrouped,
            collapsed: existing?.collapsed ?? false,
        });
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
    } catch {}
});

// ── Search ─────────────────────────────────────────────────────────────────────

const filteredSections = computed(() => {
    const q = search.value.toLowerCase().trim();
    if (!q) return sections.value;
    return sections.value
        .map((s) => {
            const groupMatches = (s.group?.name ?? "Ungrouped").toLowerCase().includes(q);
            const matchedDevices = groupMatches
                ? s.devices
                : s.devices.filter((d) => d.name.toLowerCase().includes(q));
            if (!groupMatches && matchedDevices.length === 0) return null;
            return { ...s, devices: matchedDevices, collapsed: false };
        })
        .filter((s): s is GroupSection => s !== null);
});

// ── Group actions ──────────────────────────────────────────────────────────────

function toggleSection(idx: number) {
    sections.value[idx].collapsed = !sections.value[idx].collapsed;
}

async function createGroup() {
    if (!newGroupName.value.trim()) return;
    savingGroup.value = true;
    groupError.value = null;
    try {
        const g = await api.groups.create({ name: newGroupName.value.trim() });
        groups.value.push(g);
        buildSections();
        showNewGroup.value = false;
        newGroupName.value = "";
    } catch (e) {
        groupError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        savingGroup.value = false;
    }
}

async function openEditGroup(group: Group) {
    editGroup.value = group;
    editGroupName.value = group.name;
    groupToken.value = null;
    editGroupError.value = null;
    loadingToken.value = true;
    try {
        const res = await api.groups.getToken(group.id);
        groupToken.value = res.token;
    } catch {
        groupToken.value = null;
    } finally {
        loadingToken.value = false;
    }
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
        const updated = await api.groups.update(editGroup.value.id, {
            name: editGroupName.value.trim(),
        });
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

async function rotateToken() {
    if (!editGroup.value) return;
    rotatingToken.value = true;
    try {
        const res = await api.groups.rotateToken(editGroup.value.id);
        groupToken.value = res.token;
    } catch (e) {
        editGroupError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        rotatingToken.value = false;
    }
}

async function copyToken() {
    if (!groupToken.value) return;
    await navigator.clipboard.writeText(groupToken.value);
    tokenCopied.value = true;
    setTimeout(() => (tokenCopied.value = false), 2000);
}

async function deleteGroup() {
    if (!editGroup.value) return;
    deletingGroup.value = true;
    try {
        await api.groups.delete(editGroup.value.id);
        groups.value = groups.value.filter((g) => g.id !== editGroup.value!.id);
        for (const d of devices.value) {
            if (d.group_id === editGroup.value.id) d.group_id = null;
        }
        buildSections();
        closeEditGroup();
    } catch (e) {
        editGroupError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        deletingGroup.value = false;
    }
}

// ── Device actions ─────────────────────────────────────────────────────────────

function openNewDevice(groupId: string | null) {
    newDeviceTargetGroup.value = groupId;
    newDeviceName.value = "";
    newDevicePlugin.value = plugins.value[0]?.id ?? "";
    newDeviceCredential.value = credentials.value[0]?.id ?? "";
    deviceError.value = null;
    showNewDevice.value = true;
}

async function createDevice() {
    if (!newDeviceName.value.trim() || !newDevicePlugin.value || !newDeviceCredential.value) return;
    savingDevice.value = true;
    deviceError.value = null;
    try {
        const d = await api.devices.create({
            name: newDeviceName.value.trim(),
            plugin_id: newDevicePlugin.value,
            credential_id: newDeviceCredential.value,
            group_id: newDeviceTargetGroup.value ?? null,
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

// ── Drag & drop ────────────────────────────────────────────────────────────────

function onDragStart(deviceId: string) { dragging.value = deviceId; }

function onDragOver(e: DragEvent, groupId: string | null) {
    e.preventDefault();
    dragOverGroup.value = groupId ?? "ungrouped";
}

function onDragLeave() { dragOverGroup.value = null; }

async function onDrop(e: DragEvent, groupId: string | null) {
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
    try {
        await api.devices.update(deviceId, { group_id: groupId });
    } catch {
        dev.group_id = old;
        buildSections();
    }
}

function onDragEnd() { dragging.value = null; dragOverGroup.value = null; }

// ── Helpers ────────────────────────────────────────────────────────────────────

function sectionKey(s: GroupSection) { return s.group?.id ?? "ungrouped"; }

function isDragTarget(s: GroupSection) {
    return dragOverGroup.value === (s.group?.id ?? "ungrouped") && dragging.value !== null;
}
</script>

<template>
    <div class="flex flex-col h-full">
        <!-- Header -->
        <div class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border">
            <div>
                <h1 class="text-sm font-semibold">Devices</h1>
                <p class="text-xs text-muted-foreground mt-0.5">Manage your connected devices</p>
            </div>
            <div class="flex items-center gap-px bg-muted rounded-md p-0.5">
                <button
                    @click="viewMode = 'grid'"
                    :class="['flex items-center justify-center w-7 h-7 rounded text-xs transition-colors', viewMode === 'grid' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground']"
                    aria-label="Grid view"
                >
                    <RiLayoutGridLine class="size-3.5" />
                </button>
                <button
                    @click="viewMode = 'list'"
                    :class="['flex items-center justify-center w-7 h-7 rounded text-xs transition-colors', viewMode === 'list' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground']"
                    aria-label="List view"
                >
                    <RiListCheck2 class="size-3.5" />
                </button>
            </div>
        </div>

        <!-- Toolbar -->
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
                <Button size="sm" class="gap-1.5" @click="openNewDevice(null)">
                    <RiAddLine class="size-3.5" />
                    New device
                </Button>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto px-6 py-4 flex flex-col gap-4">
            <div v-if="loading" class="flex items-center justify-center py-16 text-muted-foreground">
                <RiLoader4Line class="size-5 animate-spin mr-2" />
                <span class="text-xs">Loading devices…</span>
            </div>

            <div
                v-else-if="error"
                class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs"
            >
                <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
                {{ error }}
            </div>

            <template v-else>
                <div
                    v-for="(section, idx) in filteredSections"
                    :key="sectionKey(section)"
                    class="flex flex-col gap-2"
                    @dragover="onDragOver($event, section.group?.id ?? null)"
                    @dragleave="onDragLeave"
                    @drop="onDrop($event, section.group?.id ?? null)"
                >
                    <!-- Group header -->
                    <div
                        :class="['flex items-center justify-between gap-2 rounded-md px-2 py-1.5 transition-colors', isDragTarget(section) ? 'bg-primary/10 ring-1 ring-primary/30' : 'hover:bg-muted/50']"
                    >
                        <button
                            class="flex items-center gap-1.5 text-xs font-medium text-foreground min-w-0 flex-1"
                            @click="toggleSection(idx)"
                        >
                            <component
                                :is="section.collapsed ? RiArrowRightSLine : RiArrowDownSLine"
                                class="size-3.5 text-muted-foreground shrink-0"
                            />
                            <span class="truncate">{{ section.group?.name ?? "Ungrouped" }}</span>
                            <span class="text-muted-foreground font-normal tabular-nums">{{ section.devices.length }}</span>
                        </button>
                        <div class="flex items-center gap-0.5 shrink-0">
                            <Button
                                v-if="section.group"
                                variant="ghost"
                                size="icon"
                                class="size-6"
                                @click.stop="openEditGroup(section.group)"
                            >
                                <RiPencilLine class="size-3.5" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                class="size-6"
                                @click="openNewDevice(section.group?.id ?? null)"
                            >
                                <RiAddLine class="size-3.5" />
                            </Button>
                        </div>
                    </div>

                    <!-- Devices -->
                    <div
                        v-if="!section.collapsed"
                        :class="[viewMode === 'grid' ? 'grid gap-2' : 'flex flex-col gap-1.5']"
                        :style="viewMode === 'grid' ? 'grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))' : ''"
                    >
                        <div
                            v-if="section.devices.length === 0"
                            :class="['flex items-center justify-center rounded-lg border border-dashed border-border text-xs text-muted-foreground transition-colors', viewMode === 'grid' ? 'h-24 col-span-full' : 'h-12', isDragTarget(section) ? 'border-primary/50 bg-primary/5 text-primary' : '']"
                        >
                            {{ isDragTarget(section) ? 'Drop here' : 'No devices' }}
                        </div>

                        <div
                            v-for="device in section.devices"
                            :key="device.id"
                            :draggable="true"
                            @dragstart="onDragStart(device.id)"
                            @dragend="onDragEnd"
                            @click="router.push(`/devices/${device.id}`)"
                            :class="['group flex cursor-pointer rounded-lg border border-border bg-card transition-all hover:border-primary/40 hover:shadow-sm', dragging === device.id ? 'opacity-40 scale-95' : '', viewMode === 'grid' ? 'flex-col overflow-hidden' : 'flex-row items-center gap-3 px-3 py-2']"
                        >
                            <!-- Grid preview -->
                            <div v-if="viewMode === 'grid'" class="flex items-center justify-center h-28 bg-muted/30 border-b border-border relative">
                                <component :is="getPluginIcon(device.plugin_id)" class="size-10 text-muted-foreground/40" />
                                <div class="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground cursor-grab">
                                    <RiDraggable class="size-3.5" />
                                </div>
                                <span
                                    class="absolute top-2 right-2 block size-2 rounded-full"
                                    :class="device.online === null ? 'bg-muted-foreground/30 animate-pulse' : device.online ? 'bg-emerald-500' : 'bg-zinc-400'"
                                />
                            </div>
                            <div v-if="viewMode === 'grid'" class="flex flex-col gap-0.5 px-3 py-2.5">
                                <span class="text-xs font-semibold text-foreground truncate">{{ device.name }}</span>
                                <span class="text-[10px] text-muted-foreground font-mono truncate">{{ device.plugin_id }}</span>
                            </div>

                            <!-- List -->
                            <component v-if="viewMode === 'list'" :is="getPluginIcon(device.plugin_id)" class="size-4 text-muted-foreground shrink-0" />
                            <div v-if="viewMode === 'list'" class="flex-1 min-w-0 flex items-center gap-2">
                                <span class="text-xs font-medium text-foreground truncate">{{ device.name }}</span>
                                <span class="text-[10px] text-muted-foreground font-mono truncate hidden sm:block">{{ device.plugin_id }}</span>
                            </div>
                            <div v-if="viewMode === 'list'" class="flex items-center gap-2 shrink-0">
                                <span
                                    class="block size-1.5 rounded-full"
                                    :class="device.online === null ? 'bg-muted-foreground/30 animate-pulse' : device.online ? 'bg-emerald-500' : 'bg-zinc-400'"
                                />
                                <div class="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground cursor-grab">
                                    <RiDraggable class="size-3.5" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Empty -->
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

                <!-- No search results -->
                <div v-else-if="filteredSections.length === 0" class="flex flex-col items-center justify-center py-20 text-center gap-2">
                    <RiSearchLine class="size-8 text-muted-foreground/30" />
                    <p class="text-xs text-muted-foreground">
                        No results for <span class="font-medium text-foreground">"{{ search }}"</span>
                    </p>
                </div>
            </template>
        </div>
    </div>

    <NewGroupDialog
        :show="showNewGroup"
        :name="newGroupName"
        :saving="savingGroup"
        :error="groupError"
        @update:show="showNewGroup = $event"
        @update:name="newGroupName = $event"
        @create="createGroup"
    />

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
        @update:show="showNewDevice = $event"
        @update:name="newDeviceName = $event"
        @update:plugin="newDevicePlugin = $event"
        @update:credential="newDeviceCredential = $event"
        @create="createDevice"
    />

    <EditGroupDialog
        :group="editGroup"
        :name="editGroupName"
        :saving-name="savingGroupName"
        :token="groupToken"
        :loading-token="loadingToken"
        :rotating-token="rotatingToken"
        :token-copied="tokenCopied"
        :error="editGroupError"
        @update:name="editGroupName = $event"
        @save-name="saveGroupName"
        @rotate-token="rotateToken"
        @copy-token="copyToken"
        @close="closeEditGroup"
        @delete="confirmDeleteGroup = true"
    />

    <DeleteGroupDialog
        :show="confirmDeleteGroup"
        :group="editGroup"
        :deleting="deletingGroup"
        @cancel="confirmDeleteGroup = false"
        @confirm="deleteGroup"
    />
</template>