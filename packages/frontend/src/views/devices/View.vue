<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { api, type Device, type Credential, type Group, type PluginMeta, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { RiLoader4Line, RiErrorWarningLine, RiExternalLinkLine, RiInformationLine, RiFlashlightLine } from "@remixicon/vue";
import DeviceHeader from "./DeviceHeader.vue";
import ActionSidebar from "./ActionSidebar.vue";
import ActionPlayground from "./ActionPlayground.vue";
import InfoTable from "./InfoTable.vue";


const route = useRoute();
const deviceId = route.params.id as string;

// ── State ──────────────────────────────────────────────────────────────────

const device = ref<Device | null>(null);
const credential = ref<Credential | null>(null);
const group = ref<Group | null>(null);
const pluginMeta = ref<PluginMeta | null>(null);
const pluginConfig = ref<Record<string, any> | null>(null);

const loading = ref(true);
const error = ref<string | null>(null);

const online = ref<boolean | null>(null);
const latency = ref<number | null>(null);
const pinging = ref(false);

const activeTab = ref<"actions" | "info">("actions");

// Sidebar selection
const selectedAction = ref<string | null>(null);

// Per-action state
const actionBodies = ref<Record<string, string>>({});
const actionResults = ref<Record<string, { ok: boolean; data: unknown } | null>>({});
const actionRunning = ref<Record<string, boolean>>({});

// Streams
const streamSockets = ref<Record<string, WebSocket>>({});
const streamMessages = ref<Record<string, unknown[]>>({});
const streamConnected = ref<Record<string, boolean>>({});

// ── Load ───────────────────────────────────────────────────────────────────

onMounted(async () => {
   loading.value = true;
   error.value = null;
   try {
       const [dev, pluginsList] = await Promise.all([
           api.devices.get(deviceId),
           api.plugins.devices.list(),
       ]);
       device.value = dev;
       pluginMeta.value = pluginsList.items.find((p) => p.id === dev.plugin_id) ?? null;

       const [cred, grp, pluginDetail] = await Promise.all([
           api.credentials.get(dev.credential_id),
           dev.group_id ? api.groups.get(dev.group_id) : Promise.resolve(null),
           api.plugins.devices.get(dev.plugin_id),
       ]);
       credential.value = cred;
       group.value = grp;
       pluginConfig.value = (pluginDetail as any)._config ?? null;

       // Pre-fill bodies from examples
       for (const [name, def] of Object.entries<any>(pluginConfig.value?.actions?.send ?? {})) {
           actionBodies.value[name] = JSON.stringify(def.example ?? {}, null, 2);
       }
       for (const [name, def] of Object.entries<any>(pluginConfig.value?.actions?.request ?? {})) {
           actionBodies.value[`req_${name}`] = def.input?.path?.default ?? "/";
       }

       // Auto-select first action
       const first = allActions.value[0];
       if (first) selectedAction.value = first.name;

       await ping();
   } catch (e) {
       error.value = e instanceof ApiError ? e.detail : "Failed to load device";
   } finally {
       loading.value = false;
   }
});

onUnmounted(() => {
   for (const ws of Object.values(streamSockets.value)) ws.close();
});

// ── Ping ───────────────────────────────────────────────────────────────────

async function ping() {
   pinging.value = true;
   try {
       const result = await api.devices.ping(deviceId);
       online.value = result.online;
       latency.value = Object.values(result.protocols)[0]?.latency_ms ?? null;
   } catch {
       online.value = false;
       latency.value = null;
   } finally {
       pinging.value = false;
   }
}

// ── Actions ────────────────────────────────────────────────────────────────

async function runSend(name: string) {
   actionRunning.value[name] = true;
   actionResults.value[name] = null;
   try {
       let body: Record<string, unknown> = {};
       try { body = JSON.parse(actionBodies.value[name] ?? "{}"); } catch { /* ignore */ }
       const result = await api.actions.send(deviceId, name, body);
       actionResults.value[name] = { ok: true, data: result };
   } catch (e) {
       actionResults.value[name] = { ok: false, data: e instanceof ApiError ? e.detail : String(e) };
   } finally {
       actionRunning.value[name] = false;
   }
}

async function runRequest(name: string) {
   const key = `req_${name}`;
   actionRunning.value[key] = true;
   actionResults.value[key] = null;
   try {
       const path = actionBodies.value[key] || undefined;
       const result = await api.actions.request(deviceId, name, path);
       actionResults.value[key] = { ok: true, data: result };
   } catch (e) {
       actionResults.value[key] = { ok: false, data: e instanceof ApiError ? e.detail : String(e) };
   } finally {
       actionRunning.value[key] = false;
   }
}

function toggleStream(name: string) {
   if (streamConnected.value[name]) {
       streamSockets.value[name]?.close();
       delete streamSockets.value[name];
       streamConnected.value[name] = false;
   } else {
       streamMessages.value[name] = [];
       const ws = api.ws.stream(
           deviceId,
           name,
           (data) => {
               streamMessages.value[name] = [data, ...(streamMessages.value[name] ?? [])].slice(0, 50);
           },
           () => { streamConnected.value[name] = false; },
       );
       streamSockets.value[name] = ws;
       streamConnected.value[name] = true;
   }
}

// ── Computed ───────────────────────────────────────────────────────────────

const allActions = computed(() => {
   const cfg = pluginConfig.value?.actions ?? {};
   return [
       ...Object.entries<any>(cfg.send ?? {}).map(([name, def]) => ({
           name, label: def.label ?? name, category: "send" as const,
       })),
       ...Object.entries<any>(cfg.request ?? {}).map(([name, def]) => ({
           name: `req_${name}`, label: def.label ?? name, category: "request" as const,
       })),
       ...Object.entries<any>(cfg.stream ?? {}).map(([name, def]) => ({
           name, label: def.label ?? name, category: "stream" as const,
       })),
   ];
});

const selectedEntry = computed(() =>
   allActions.value.find((a) => a.name === selectedAction.value) ?? null,
);

// Resolve the raw def + body/result keys based on category
const selectedDef = computed(() => {
   if (!selectedEntry.value) return null;
   const cfg = pluginConfig.value?.actions ?? {};
   const { name, category } = selectedEntry.value;
   if (category === "send") return cfg.send?.[name] ?? null;
   if (category === "request") return cfg.request?.[name.replace(/^req_/, "")] ?? null;
   if (category === "stream") return cfg.stream?.[name] ?? null;
   return null;
});

const playgroundBody = computed(() => actionBodies.value[selectedAction.value ?? ""] ?? "");
const playgroundRunning = computed(() => actionRunning.value[selectedAction.value ?? ""] ?? false);
const playgroundResult = computed(() => actionResults.value[selectedAction.value ?? ""] ?? null);
const playgroundStreamConnected = computed(() => streamConnected.value[selectedAction.value ?? ""] ?? false);
const playgroundStreamMessages = computed(() => streamMessages.value[selectedAction.value ?? ""] ?? []);

function handleRun() {
   if (!selectedEntry.value) return;
   if (selectedEntry.value.category === "send") runSend(selectedEntry.value.name);
   if (selectedEntry.value.category === "request") runRequest(selectedEntry.value.name.replace(/^req_/, ""));
}

function handleToggleStream() {
   if (selectedEntry.value?.category === "stream") toggleStream(selectedEntry.value.name);
}

const docsUrl = computed(() => `http://localhost:8000/devices/${deviceId}/docs`);

function openDocs() {
   window.open(docsUrl.value, "_blank");
}

// Info tab rows
const instanceRows = computed(() => device.value ? [
   { label: "Device ID", value: device.value.id, mono: true },
   { label: "Name",      value: device.value.name },
   { label: "Group",     value: group.value?.name ?? "—" },
   { label: "Credential",value: credential.value?.name ?? "—" },
] : []);

const pluginRows = computed(() => pluginMeta.value ? [
   { label: "Plugin ID",    value: pluginMeta.value.id, mono: true },
   { label: "Name",         value: pluginMeta.value.name },
   { label: "Version",      value: pluginMeta.value.version },
   { label: "Author",       value: pluginMeta.value.author?.name ?? "—" },
   { label: "Organisation", value: pluginMeta.value.author?.organisation ?? "—" },
   { label: "Description",  value: pluginMeta.value.description ?? "—" },
] : []);
</script>

<template>
   <!-- Loading -->
   <div v-if="loading" class="flex items-center justify-center h-full text-muted-foreground">
       <RiLoader4Line class="size-5 animate-spin mr-2" />
       <span class="text-xs">Loading…</span>
   </div>

   <!-- Error -->
   <div
       v-else-if="error"
       class="flex items-start gap-2 m-6 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs"
   >
       <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
       {{ error }}
   </div>

   <!-- Main -->
   <div v-else-if="device" class="flex flex-col h-full overflow-hidden">

       <!-- Header -->
       <DeviceHeader
           :device="device"
           :plugin-meta="pluginMeta"
           :online="online"
           :latency="latency"
           :pinging="pinging"
           :docs-url="docsUrl"
           @ping="ping"
       />

       <!-- Tab bar -->
       <div class="flex items-center gap-px px-6 border-b border-border shrink-0">
           <button
               v-for="tab in [
                   { id: 'actions', label: 'Actions', icon: RiFlashlightLine },
                   { id: 'info',    label: 'Info',    icon: RiInformationLine },
               ]"
               :key="tab.id"
               class="flex items-center gap-1.5 px-3 py-2.5 text-xs border-b-2 transition-colors -mb-px"
               :class="
                   activeTab === tab.id
                       ? 'border-primary text-foreground font-medium'
                       : 'border-transparent text-muted-foreground hover:text-foreground'
               "
               @click="activeTab = tab.id as any"
           >
               <component :is="tab.icon" class="size-3.5" />
               {{ tab.label }}
           </button>
       </div>

       <!-- Tab: Actions — two-column layout -->
       <div v-if="activeTab === 'actions'" class="flex flex-1 min-h-0 overflow-hidden">

           <!-- Sidebar -->
           <ActionSidebar
               :actions="allActions"
               :selected="selectedAction"
               :connected-streams="streamConnected"
               @select="selectedAction = $event"
           />

           <!-- Playground -->
           <div class="flex-1 min-w-0 overflow-hidden">
               <ActionPlayground
                   :action-name="selectedEntry?.name ?? null"
                   :action-def="selectedDef"
                   :category="selectedEntry?.category ?? null"
                   :body="playgroundBody"
                   :running="playgroundRunning"
                   :result="playgroundResult"
                   :stream-connected="playgroundStreamConnected"
                   :stream-messages="playgroundStreamMessages"
                   @update:body="actionBodies[selectedAction!] = $event"
                   @run="handleRun"
                   @toggle-stream="handleToggleStream"
               />
           </div>
       </div>

       <!-- Tab: Info -->
       <div v-if="activeTab === 'info'" class="flex-1 overflow-auto px-6 py-5">
           <div class="flex flex-col gap-5 max-w-lg">

               <InfoTable title="Instance" :rows="instanceRows" />
               <InfoTable v-if="pluginMeta" title="Plugin" :rows="pluginRows" />

               <!-- Tags -->
               <div v-if="pluginMeta?.tags?.length" class="flex flex-wrap gap-1.5">
                   <span
                       v-for="tag in pluginMeta.tags"
                       :key="tag"
                       class="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
                   >
                       {{ tag }}
                   </span>
               </div>

               <!-- API Docs -->
               <section class="flex flex-col gap-2">
                   <h2 class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">API</h2>
                   <div class="rounded-lg border border-border px-4 py-3 flex items-center justify-between gap-3">
                       <div>
                           <p class="text-xs font-medium">Swagger UI</p>
                           <p class="text-[10px] text-muted-foreground font-mono mt-0.5 break-all">{{ docsUrl }}</p>
                       </div>
                       <Button
                           variant="outline"
                           size="sm"
                           class="gap-1.5 shrink-0"
                           @click="openDocs"
                       >
                           <RiExternalLinkLine class="size-3.5" />
                           Open
                       </Button>
                   </div>
               </section>
           </div>
       </div>
   </div>
</template>