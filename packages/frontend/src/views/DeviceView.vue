<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import {
  api,
  type Device,
  type Credential,
  type Group,
  type PluginMeta,
  ApiError,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  RiArrowLeftLine,
  RiExternalLinkLine,
  RiLoader4Line,
  RiErrorWarningLine,
  RiRefreshLine,
  RiPlayLine,
  RiRadioLine,
  RiStopLine,
  RiInformationLine,
  RiCodeLine,
  RiFlashlightLine,
} from "@remixicon/vue";

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

const activeTab = ref<"actions" | "info" | "docs">("actions");

// Action runner state — keyed by action name
const actionBodies = ref<Record<string, string>>({});
const actionResults = ref<
  Record<string, { ok: boolean; data: unknown } | null>
>({});
const actionRunning = ref<Record<string, boolean>>({});

// Stream state — keyed by action name
const streamSockets = ref<Record<string, WebSocket>>({});
const streamMessages = ref<Record<string, unknown[]>>({});
const streamConnected = ref<Record<string, boolean>>({});

// ── Load ───────────────────────────────────────────────────────────────────

onMounted(async () => {
  loading.value = true;
  error.value = null;
  try {
    const [dev, plugins] = await Promise.all([
      api.devices.get(deviceId),
      api.plugins.devices.list(),
    ]);
    device.value = dev;
    pluginMeta.value =
      plugins.items.find((p) => p.id === dev.plugin_id) ?? null;

    // Load credential + group in parallel
    const extras = await Promise.all([
      api.credentials.get(dev.credential_id),
      dev.group_id ? api.groups.get(dev.group_id) : Promise.resolve(null),
      api.plugins.devices.get(dev.plugin_id),
    ]);
    credential.value = extras[0];
    group.value = extras[1];
    // The raw plugin detail contains _config with actions
    pluginConfig.value = (extras[2] as any)._config ?? null;

    // Pre-fill action bodies with examples
    const actions = pluginConfig.value?.actions ?? {};
    for (const [name, def] of Object.entries<any>(actions.send ?? {})) {
      actionBodies.value[name] = JSON.stringify(def.example ?? {}, null, 2);
    }
    for (const [name, def] of Object.entries<any>(actions.request ?? {})) {
      actionBodies.value[`req_${name}`] = def.input?.path?.default ?? "/";
    }

    await ping();
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : "Failed to load device";
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  // Close all open streams
  for (const ws of Object.values(streamSockets.value)) {
    ws.close();
  }
});

// ── Ping ───────────────────────────────────────────────────────────────────

async function ping() {
  pinging.value = true;
  try {
    const result = await api.devices.ping(deviceId);
    online.value = result.online;
    // Pick first latency available
    const first = Object.values(result.protocols)[0];
    latency.value = first?.latency_ms ?? null;
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
    try {
      body = JSON.parse(actionBodies.value[name] ?? "{}");
    } catch {
      /* invalid json, send empty */
    }
    const result = await api.actions.send(deviceId, name, body);
    actionResults.value[name] = { ok: true, data: result };
  } catch (e) {
    actionResults.value[name] = {
      ok: false,
      data: e instanceof ApiError ? e.detail : String(e),
    };
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
    actionResults.value[key] = {
      ok: false,
      data: e instanceof ApiError ? e.detail : String(e),
    };
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
        streamMessages.value[name] = [
          data,
          ...(streamMessages.value[name] ?? []),
        ].slice(0, 50);
      },
      () => {
        streamConnected.value[name] = false;
      },
    );
    streamSockets.value[name] = ws;
    streamConnected.value[name] = true;
  }
}

// ── Computed helpers ───────────────────────────────────────────────────────

const sendActions = computed(() =>
  Object.entries<any>(pluginConfig.value?.actions?.send ?? {}),
);
const requestActions = computed(() =>
  Object.entries<any>(pluginConfig.value?.actions?.request ?? {}),
);
const streamActions = computed(() =>
  Object.entries<any>(pluginConfig.value?.actions?.stream ?? {}),
);

const docsUrl = computed(
  () => `http://localhost:8000/devices/${deviceId}/docs`,
);
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center h-full text-muted-foreground"
    >
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

    <template v-else-if="device">
      <!-- Header -->
      <div class="flex items-center gap-4 px-6 py-4 border-b border-border">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <h1 class="text-sm font-semibold truncate">{{ device.name }}</h1>
            <!-- Online badge -->
            <span
              class="shrink-0 inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full border"
              :class="
                online === null
                  ? 'border-border text-muted-foreground'
                  : online
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600'
                    : 'border-zinc-400/30 bg-zinc-400/10 text-zinc-500'
              "
            >
              <span
                class="block size-1.5 rounded-full"
                :class="
                  online === null
                    ? 'bg-muted-foreground/40 animate-pulse'
                    : online
                      ? 'bg-emerald-500'
                      : 'bg-zinc-400'
                "
              />
              {{
                online === null
                  ? "checking…"
                  : online
                    ? `online${latency !== null ? ` · ${latency}ms` : ""}`
                    : "offline"
              }}
            </span>
          </div>
          <p class="text-[10px] text-muted-foreground font-mono mt-0.5">
            {{ device.plugin_id }}
            <span v-if="pluginMeta?.version" class="opacity-60"
              >v{{ pluginMeta.version }}</span
            >
          </p>
        </div>

        <div class="flex items-center gap-1.5 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            :disabled="pinging"
            @click="ping"
            aria-label="Refresh ping"
          >
            <RiRefreshLine
              class="size-3.5"
              :class="pinging ? 'animate-spin' : ''"
            />
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="gap-1.5"
            @click="() => window.open(docsUrl, '_blank')"
          >
            <RiExternalLinkLine class="size-3.5" />
            API Docs
          </Button>
        </div>
      </div>

      <!-- Tabs -->
      <div
        class="flex items-center gap-px px-6 border-b border-border bg-background"
      >
        <button
          v-for="tab in [
            { id: 'actions', label: 'Actions', icon: RiFlashlightLine },
            { id: 'info', label: 'Info', icon: RiInformationLine },
          ]"
          :key="tab.id"
          @click="activeTab = tab.id as any"
          class="flex items-center gap-1.5 px-3 py-2.5 text-xs border-b-2 transition-colors"
          :class="
            activeTab === tab.id
              ? 'border-primary text-foreground font-medium'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          "
        >
          <component :is="tab.icon" class="size-3.5" />
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab: Actions -->
      <div
        v-if="activeTab === 'actions'"
        class="flex-1 overflow-auto px-6 py-4 flex flex-col gap-6"
      >
        <!-- No actions -->
        <div
          v-if="
            !sendActions.length &&
            !requestActions.length &&
            !streamActions.length
          "
          class="flex items-center justify-center py-16 text-xs text-muted-foreground"
        >
          No actions defined for this plugin.
        </div>

        <!-- Send actions -->
        <div v-if="sendActions.length" class="flex flex-col gap-2">
          <h2
            class="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
          >
            Send
          </h2>
          <div
            v-for="[name, def] in sendActions"
            :key="name"
            class="rounded-lg border border-border bg-card p-4 flex flex-col gap-3"
          >
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-xs font-medium">{{ def.label ?? name }}</p>
                <p class="text-[10px] font-mono text-muted-foreground mt-0.5">
                  POST /send/{{ name }}
                </p>
              </div>
              <Button
                size="sm"
                class="gap-1.5 shrink-0"
                :disabled="actionRunning[name]"
                @click="runSend(name)"
              >
                <RiLoader4Line
                  v-if="actionRunning[name]"
                  class="size-3.5 animate-spin"
                />
                <RiPlayLine v-else class="size-3.5" />
                Run
              </Button>
            </div>

            <!-- Body editor (skip for file uploads) -->
            <textarea
              v-if="
                !Object.values<any>(def.input ?? {}).some(
                  (v) => v.type === 'bytes',
                )
              "
              v-model="actionBodies[name]"
              rows="4"
              spellcheck="false"
              class="w-full rounded-md border border-border bg-muted/20 px-2.5 py-2 font-mono text-[11px] text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors"
            />
            <p v-else class="text-[11px] text-muted-foreground italic">
              File upload — use the API docs to upload via multipart/form-data.
            </p>

            <!-- Result -->
            <div
              v-if="actionResults[name]"
              class="rounded-md border px-2.5 py-2 font-mono text-[11px] whitespace-pre-wrap break-all"
              :class="
                actionResults[name]?.ok
                  ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400'
                  : 'border-destructive/20 bg-destructive/5 text-destructive'
              "
            >
              {{ JSON.stringify(actionResults[name]?.data, null, 2) }}
            </div>
          </div>
        </div>

        <!-- Request actions -->
        <div v-if="requestActions.length" class="flex flex-col gap-2">
          <h2
            class="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
          >
            Request
          </h2>
          <div
            v-for="[name, def] in requestActions"
            :key="name"
            class="rounded-lg border border-border bg-card p-4 flex flex-col gap-3"
          >
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-xs font-medium">{{ def.label ?? name }}</p>
                <p class="text-[10px] font-mono text-muted-foreground mt-0.5">
                  GET /request/{{ name }}
                </p>
              </div>
              <Button
                size="sm"
                class="gap-1.5 shrink-0"
                :disabled="actionRunning[`req_${name}`]"
                @click="runRequest(name)"
              >
                <RiLoader4Line
                  v-if="actionRunning[`req_${name}`]"
                  class="size-3.5 animate-spin"
                />
                <RiPlayLine v-else class="size-3.5" />
                Run
              </Button>
            </div>

            <!-- Path input if applicable -->
            <div
              v-if="def.input?.path !== undefined"
              class="flex flex-col gap-1"
            >
              <label class="text-[10px] text-muted-foreground">path</label>
              <input
                v-model="actionBodies[`req_${name}`]"
                type="text"
                placeholder="/"
                class="w-full rounded-md border border-border bg-muted/20 px-2.5 py-1.5 font-mono text-[11px] outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors"
              />
            </div>

            <!-- Result -->
            <div
              v-if="actionResults[`req_${name}`]"
              class="rounded-md border px-2.5 py-2 font-mono text-[11px] whitespace-pre-wrap break-all max-h-48 overflow-auto"
              :class="
                actionResults[`req_${name}`]?.ok
                  ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400'
                  : 'border-destructive/20 bg-destructive/5 text-destructive'
              "
            >
              {{ JSON.stringify(actionResults[`req_${name}`]?.data, null, 2) }}
            </div>
          </div>
        </div>

        <!-- Stream actions -->
        <div v-if="streamActions.length" class="flex flex-col gap-2">
          <h2
            class="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
          >
            Stream
          </h2>
          <div
            v-for="[name, def] in streamActions"
            :key="name"
            class="rounded-lg border border-border bg-card p-4 flex flex-col gap-3"
          >
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-xs font-medium">{{ def.label ?? name }}</p>
                <p class="text-[10px] font-mono text-muted-foreground mt-0.5">
                  WS /stream/{{ name }}
                </p>
              </div>
              <Button
                size="sm"
                class="gap-1.5 shrink-0"
                :variant="streamConnected[name] ? 'destructive' : 'default'"
                @click="toggleStream(name)"
              >
                <RiStopLine v-if="streamConnected[name]" class="size-3.5" />
                <RiRadioLine v-else class="size-3.5" />
                {{ streamConnected[name] ? "Disconnect" : "Connect" }}
              </Button>
            </div>

            <!-- Live messages -->
            <div
              v-if="streamConnected[name] || streamMessages[name]?.length"
              class="flex flex-col gap-1 max-h-60 overflow-auto rounded-md border border-border bg-muted/20 px-2.5 py-2"
            >
              <div
                v-if="!streamMessages[name]?.length"
                class="text-[11px] text-muted-foreground italic"
              >
                Waiting for messages…
              </div>
              <div
                v-for="(msg, i) in streamMessages[name]"
                :key="i"
                class="font-mono text-[10px] text-foreground border-b border-border/50 pb-1 last:border-0 last:pb-0 whitespace-pre-wrap break-all"
              >
                {{ JSON.stringify(msg, null, 2) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Info -->
      <div v-if="activeTab === 'info'" class="flex-1 overflow-auto px-6 py-4">
        <div class="flex flex-col gap-4 max-w-lg">
          <!-- Device instance -->
          <section class="flex flex-col gap-2">
            <h2
              class="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
            >
              Instance
            </h2>
            <div class="rounded-lg border border-border overflow-hidden">
              <div
                v-for="(val, label) in {
                  'Device ID': device.id,
                  Name: device.name,
                  Group: group?.name ?? '—',
                  Credential: credential?.name ?? '—',
                }"
                :key="label"
                class="flex items-start gap-3 px-4 py-2.5 border-b border-border/60 last:border-0"
              >
                <span
                  class="text-[11px] text-muted-foreground w-24 shrink-0 pt-px"
                  >{{ label }}</span
                >
                <span class="text-[11px] font-mono text-foreground break-all">{{
                  val
                }}</span>
              </div>
            </div>
          </section>

          <!-- Plugin -->
          <section v-if="pluginMeta" class="flex flex-col gap-2">
            <h2
              class="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
            >
              Plugin
            </h2>
            <div class="rounded-lg border border-border overflow-hidden">
              <div
                v-for="(val, label) in {
                  ID: pluginMeta.id,
                  Name: pluginMeta.name,
                  Version: pluginMeta.version,
                  Author: pluginMeta.author?.name ?? '—',
                  Organisation: pluginMeta.author?.organisation ?? '—',
                  Description: pluginMeta.description ?? '—',
                }"
                :key="label"
                class="flex items-start gap-3 px-4 py-2.5 border-b border-border/60 last:border-0"
              >
                <span
                  class="text-[11px] text-muted-foreground w-24 shrink-0 pt-px"
                  >{{ label }}</span
                >
                <span class="text-[11px] text-foreground break-all">{{
                  val
                }}</span>
              </div>
            </div>

            <!-- Tags -->
            <div v-if="pluginMeta.tags?.length" class="flex flex-wrap gap-1.5">
              <span
                v-for="tag in pluginMeta.tags"
                :key="tag"
                class="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
              >
                {{ tag }}
              </span>
            </div>
          </section>

          <!-- API Docs link -->
          <section class="flex flex-col gap-2">
            <h2
              class="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
            >
              API
            </h2>
            <div
              class="rounded-lg border border-border px-4 py-3 flex items-center justify-between gap-3"
            >
              <div>
                <p class="text-xs font-medium">Swagger UI</p>
                <p class="text-[10px] text-muted-foreground font-mono mt-0.5">
                  {{ docsUrl }}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                class="gap-1.5 shrink-0"
                @click="() => window.open(docsUrl, '_blank')"
              >
                <RiExternalLinkLine class="size-3.5" />
                Open
              </Button>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>
