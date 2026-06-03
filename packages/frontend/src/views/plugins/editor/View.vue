<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
    RiCloseLine,
    RiLoader4Line,
    RiErrorWarningLine,
    RiCheckLine,
} from "@remixicon/vue";
import BaseInfoView from "./baseInfo/View.vue";
import CredentialsView, { type CredentialField } from "./credentials/View.vue";
import ProtocolsView, { type ProtocolConfig } from "./protocols/View.vue";
import ActionsView, { type ActionDef } from "./actions/View.vue";
import TabPlaceholder from "./TabPlaceholder.vue";
import PreviewView, { type IconAsset } from "./preview/View.vue";

// Props / Emits

const props = defineProps<{
    show: boolean;
    editPluginId?: string | null;
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
    saved: [pluginId: string];
}>();

// Tabs 

type TabId = "base" | "credentials" | "protocols" | "actions" | "status" | "preview";

const TABS: { id: TabId; label: string }[] = [
    { id: "base",        label: "Base Info" },
    { id: "credentials", label: "Credentials" },
    { id: "protocols",   label: "Protocols" },
    { id: "actions",     label: "Actions" },
    { id: "status",      label: "Status / Subscribe" },
    { id: "preview",     label: "Preview" },
];

const activeTab = ref<TabId>("base");

// State: Base Info

const name               = ref("");
const id                 = ref("");
const idManual           = ref(false);
const version            = ref("1.0.0");
const status             = ref<"alpha" | "beta" | "stable">("alpha");
const description        = ref("");
const authorName         = ref("");
const authorOrg          = ref("");
const authorUrl          = ref("");
const tagInput           = ref("");
const tags               = ref<string[]>([]);
const minIotta           = ref("0.1.0");
const availableProtocols = ref<{ id: string; name: string }[]>([]);
const selectedProtocols  = ref<string[]>([]);
const loadingProtocols   = ref(false);

// State: Credentials

const credentialFields = ref<CredentialField[]>([]);

// State: Protocols

const protocolBlocks = ref<ProtocolConfig[]>([]);

// State: Actions 

const actionDefs = ref<ActionDef[]>([]);

// State: Icon

const iconAsset = ref<IconAsset | null>(null);

// Global

const saving        = ref(false);
const saveError     = ref<string | null>(null);
const loadingPlugin = ref(false);
const yamlOpen      = ref(false);

// Helpers

let _counter = 0;
function uid() { return `a_${Date.now()}_${_counter++}`; }

// Lifecycle

watch(() => props.show, async (val) => {
    if (!val) return;
    reset();

    loadingProtocols.value = true;
    try {
        const res = await api.plugins.protocols.list();
        availableProtocols.value = res.items.map((p) => ({ id: p.id, name: p.name }));
    } catch {
        availableProtocols.value = [];
    } finally {
        loadingProtocols.value = false;
    }

    if (props.editPluginId) {
        loadingPlugin.value = true;
        try {
            const plugin = await api.plugins.devices.get(props.editPluginId) as any;
            prefill(plugin);
        } catch {
            saveError.value = "Failed to load plugin data.";
        } finally {
            loadingPlugin.value = false;
        }
    }
});

function reset() {
    activeTab.value         = "base";
    name.value              = "";
    id.value                = "";
    idManual.value          = false;
    version.value           = "1.0.0";
    status.value            = "alpha";
    description.value       = "";
    authorName.value        = "";
    authorOrg.value         = "";
    authorUrl.value         = "";
    tagInput.value          = "";
    tags.value              = [];
    minIotta.value          = "0.1.0";
    selectedProtocols.value = [];
    credentialFields.value  = [];
    protocolBlocks.value    = [];
    actionDefs.value        = [];
    iconAsset.value         = null;
    saveError.value         = null;
    yamlOpen.value          = false;
}

function prefill(plugin: any) {
    name.value        = plugin.name              ?? "";
    id.value          = plugin.id                ?? "";
    idManual.value    = true;
    version.value     = plugin.version           ?? "1.0.0";
    status.value      = plugin.status            ?? "alpha";
    description.value = plugin.description       ?? "";
    minIotta.value    = plugin.min_iotta_version ?? "0.1.0";
    authorName.value  = plugin.author?.name          ?? "";
    authorOrg.value   = plugin.author?.organisation  ?? "";
    authorUrl.value   = plugin.author?.url            ?? "";
    tags.value        = Array.isArray(plugin.tags) ? [...plugin.tags] : [];

    const deps = plugin.dependencies?.protocols ?? [];
    selectedProtocols.value = Array.isArray(deps) ? [...deps] : [];

    // credentials.json → _credentials
    if (Array.isArray(plugin._credentials)) {
        credentialFields.value = plugin._credentials.map((f: any) => ({
            field:       f.field       ?? "",
            type:        f.type        ?? "string",
            label:       f.label       ?? "",
            placeholder: f.placeholder ?? "",
            required:    f.required    ?? true,
            secret:      f.secret      ?? false,
        }));
    } else {
        credentialFields.value = [];
    }

    // protocols.json → _protocols
    if (plugin._protocols && typeof plugin._protocols === "object") {
        protocolBlocks.value = Object.entries(plugin._protocols).map(
            ([protocolId, config]) => ({ protocolId, config: config as Record<string, unknown> })
        );
    } else {
        protocolBlocks.value = [];
    }

    // actions.json → _actions
    if (plugin._actions && typeof plugin._actions === "object") {
        const loaded: ActionDef[] = [];
        for (const category of ["send", "request", "stream"] as const) {
            const section = plugin._actions[category] ?? {};
            for (const [actionName, def] of Object.entries(section as Record<string, any>)) {
                loaded.push({
                    _id: uid(),
                    name: actionName,
                    category,
                    label:    def.label   ?? "",
                    protocol: def.protocol ?? "",
                    method:   def.method   ?? "",
                    // send
                    topic:       def.topic ?? "",
                    payloadJson: def.payload ? JSON.stringify(def.payload, null, 2) : "{}",
                    inputFields: Object.entries(def.input ?? {})
                        .filter(([k]) => k !== "path" || category !== "request")
                        .map(([k, v]: any) => ({
                            key:      k,
                            type:     v.type     ?? "string",
                            required: v.required ?? true,
                            default:  v.default !== undefined ? String(v.default) : undefined,
                        })),
                    exampleJson: def.example ? JSON.stringify(def.example, null, 2) : "{}",
                    // request
                    inputPathDefault: def.input?.path?.default ?? "/",
                    // stream
                    streamTopic:  def.topic  ?? "",
                    streamFilter: def.filter ? JSON.stringify(def.filter) : "",
                    streamMerge:  def.merge  !== false,
                });
            }
        }
        actionDefs.value = loaded;
    } else {
        actionDefs.value = [];
    }
}

// Build payloads

function buildPluginYaml(): Record<string, unknown> {
    const yaml: Record<string, unknown> = {
        id:      id.value,
        name:    name.value,
        version: version.value,
        status:  status.value,
        scope:   "community",
    };
    if (description.value.trim()) yaml.description = description.value.trim();
    const author: Record<string, string> = {};
    if (authorName.value.trim()) author.name         = authorName.value.trim();
    if (authorOrg.value.trim())  author.organisation = authorOrg.value.trim();
    if (authorUrl.value.trim())  author.url          = authorUrl.value.trim();
    if (Object.keys(author).length) yaml.author = author;
    if (tags.value.length) yaml.tags = [...tags.value];
    yaml.dependencies = { protocols: [...selectedProtocols.value] };
    if (minIotta.value.trim()) yaml.min_iotta_version = minIotta.value.trim();
    return yaml;
}

function buildCredentialsJson(): any[] | null {
    if (!credentialFields.value.length) return null;
    return credentialFields.value.map(({ placeholder, ...f }) =>
        placeholder ? { ...f, placeholder } : f
    );
}

function buildProtocolsJson(): Record<string, unknown> | null {
    if (!protocolBlocks.value.length) return null;
    const obj: Record<string, unknown> = {};
    for (const b of protocolBlocks.value) obj[b.protocolId] = b.config;
    return obj;
}

function buildActionsJson(): Record<string, unknown> | null {
    if (!actionDefs.value.length) return null;

    const result: Record<string, Record<string, unknown>> = {
        send: {}, request: {}, stream: {},
    };

    for (const a of actionDefs.value) {
        if (!a.name.trim()) continue;

        const def: Record<string, unknown> = {
            protocol: a.protocol,
            label:    a.label || a.name,
        };
        if (a.method) def.method = a.method;

        if (a.category === "send") {
            if (a.topic.trim()) def.topic = a.topic.trim();
            try { def.payload = JSON.parse(a.payloadJson); } catch { def.payload = {}; }
            if (a.inputFields.length) {
                const inp: Record<string, unknown> = {};
                for (const f of a.inputFields) {
                    if (!f.key.trim()) continue;
                    const fd: Record<string, unknown> = { type: f.type, required: f.required };
                    if (f.default !== undefined && f.default !== "") fd.default = f.default;
                    inp[f.key] = fd;
                }
                if (Object.keys(inp).length) def.input = inp;
            }
            try {
                const ex = JSON.parse(a.exampleJson);
                if (Object.keys(ex).length) def.example = ex;
            } catch { /* skip */ }
        }

        if (a.category === "request") {
            def.input = { path: { type: "string", default: a.inputPathDefault || "/" } };
        }

        if (a.category === "stream") {
            if (a.streamTopic.trim()) def.topic = a.streamTopic.trim();
            if (a.streamFilter.trim()) {
                try { def.filter = JSON.parse(a.streamFilter); } catch { /* skip */ }
            }
            def.merge   = a.streamMerge;
            def.emit_as = "websocket";
        }

        result[a.category][a.name.trim()] = def;
    }

    // Drop empty sections
    for (const k of ["send", "request", "stream"] as const) {
        if (Object.keys(result[k]).length === 0) delete result[k];
    }

    return Object.keys(result).length ? result : null;
}

// Validation + Save

function validate(): string | null {
    if (!name.value.trim())    return "Name is required.";
    if (!id.value.trim())      return "Plugin ID is required.";
    if (!/^[a-z0-9][a-z0-9\-]*$/.test(id.value))
        return "Plugin ID must be lowercase alphanumeric with hyphens only.";
    if (!version.value.trim()) return "Version is required.";

    for (const [i, f] of credentialFields.value.entries()) {
        if (!f.field.trim()) return `Credential field #${i + 1}: field key is required.`;
        if (!f.label.trim()) return `Credential field #${i + 1}: label is required.`;
        if (!/^[a-z0-9_]+$/.test(f.field))
            return `Credential field #${i + 1}: key "${f.field}" must be lowercase letters, numbers and underscores only.`;
    }

    for (const [i, a] of actionDefs.value.entries()) {
        if (!a.name.trim())     return `Action #${i + 1}: name is required.`;
        if (!a.protocol.trim()) return `Action "${a.name}": protocol is required.`;
    }

    return null;
}

async function save() {
    const err = validate();
    if (err) { saveError.value = err; return; }

    saving.value    = true;
    saveError.value = null;

    try {
        const isEdit = !!props.editPluginId;
        const res = await fetch(
            isEdit
                ? `http://localhost:8000/plugins/devices/${props.editPluginId}`
                : "http://localhost:8000/plugins/devices/create",
            {
                method: isEdit ? "PUT" : "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${localStorage.getItem("iotta_token") ?? ""}`,
                },
                body: JSON.stringify({
                    plugin_yaml:      buildPluginYaml(),
                    credentials_json: buildCredentialsJson(),
                    protocols_json:   buildProtocolsJson(),
                    actions_json:     buildActionsJson(),
                    icon: iconAsset.value
                        ? {
                            filename:  iconAsset.value.filename,
                            base64:    iconAsset.value.base64,
                            mime_type: iconAsset.value.mimeType,
                        }
                        : null,
                }),
            },
        );

        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail ?? res.statusText);
        }

        const data = await res.json();
        emit("saved", data.id);
        emit("update:show", false);
    } catch (e: unknown) {
        saveError.value = e instanceof Error ? e.message : "Failed to save plugin.";
    } finally {
        saving.value = false;
    }
}

const canSave = computed(() =>
    !!name.value.trim() && !!id.value.trim() && !!version.value.trim()
);
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="emit('update:show', false)"
            >
                <div class="absolute inset-0 bg-black/60" @click="emit('update:show', false)" />

                <div
                    class="relative z-10 flex flex-col w-full mx-4 rounded-xl border border-border bg-card shadow-2xl overflow-hidden transition-[max-width] duration-200"
                    :class="yamlOpen ? 'max-w-4xl' : 'max-w-2xl'"
                >
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
                        <div>
                            <h2 class="text-sm font-semibold">
                                {{ editPluginId ? `Edit plugin · ${editPluginId}` : "New device plugin" }}
                            </h2>
                            <p class="text-[11px] text-muted-foreground mt-0.5">
                                Define the plugin metadata, credentials, protocols and actions.
                            </p>
                        </div>
                        <Button variant="ghost" size="icon-sm" @click="emit('update:show', false)">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>

                    <!-- Tabs bar -->
                    <div class="flex items-center gap-px px-6 border-b border-border shrink-0 overflow-x-auto no-scrollbar">
                        <button
                            v-for="tab in TABS"
                            :key="tab.id"
                            class="flex items-center px-3 py-2.5 text-xs border-b-2 transition-colors whitespace-nowrap shrink-0 -mb-px"
                            :class="
                                activeTab === tab.id
                                    ? 'border-primary text-foreground font-medium'
                                    : 'border-transparent text-muted-foreground hover:text-foreground'
                            "
                            @click="activeTab = tab.id"
                        >
                            {{ tab.label }}
                            <span
                                v-if="tab.id === 'credentials' && credentialFields.length"
                                class="ml-1.5 inline-flex size-1.5 rounded-full bg-primary"
                            />
                            <span
                                v-if="tab.id === 'protocols' && protocolBlocks.length"
                                class="ml-1.5 inline-flex size-1.5 rounded-full bg-primary"
                            />
                            <span
                                v-if="tab.id === 'actions' && actionDefs.length"
                                class="ml-1.5 inline-flex size-1.5 rounded-full bg-primary"
                            />
                            <span
                                v-if="tab.id === 'preview' && iconAsset"
                                class="ml-1.5 inline-flex size-1.5 rounded-full bg-primary"
                            />
                        </button>
                    </div>

                    <!-- Body -->
                    <div class="flex relative" style="max-height: 60vh; overflow-y: auto;">

                        <!-- Loading overlay -->
                        <div
                            v-if="loadingPlugin"
                            class="absolute inset-0 z-10 flex items-center justify-center bg-card/80 backdrop-blur-[2px]"
                        >
                            <div class="flex items-center gap-2 text-xs text-muted-foreground">
                                <RiLoader4Line class="size-4 animate-spin" />
                                Loading plugin data…
                            </div>
                        </div>

                        <!-- Tab: Base Info -->
                        <BaseInfoView
                            v-if="activeTab === 'base'"
                            :name="name"
                            :id="id"
                            :id-manual="idManual"
                            :version="version"
                            :status="status"
                            :description="description"
                            :author-name="authorName"
                            :author-org="authorOrg"
                            :author-url="authorUrl"
                            :tag-input="tagInput"
                            :tags="tags"
                            :min-iotta="minIotta"
                            :available-protocols="availableProtocols"
                            :selected-protocols="selectedProtocols"
                            :loading-protocols="loadingProtocols"
                            @update:name="name = $event"
                            @update:id="id = $event"
                            @update:id-manual="idManual = $event"
                            @update:version="version = $event"
                            @update:status="status = $event"
                            @update:description="description = $event"
                            @update:author-name="authorName = $event"
                            @update:author-org="authorOrg = $event"
                            @update:author-url="authorUrl = $event"
                            @update:tag-input="tagInput = $event"
                            @update:tags="tags = $event"
                            @update:min-iotta="minIotta = $event"
                            @update:selected-protocols="selectedProtocols = $event"
                            @update:yaml-open="yamlOpen = $event"
                        />

                        <!-- Tab: Credentials -->
                        <CredentialsView
                            v-else-if="activeTab === 'credentials'"
                            :fields="credentialFields"
                            @update:fields="credentialFields = $event"
                        />

                        <!-- Tab: Protocols -->
                        <ProtocolsView
                            v-else-if="activeTab === 'protocols'"
                            :blocks="protocolBlocks"
                            :available-protocols="availableProtocols"
                            @update:blocks="protocolBlocks = $event"
                        />

                        <!-- Tab: Actions -->
                        <ActionsView
                            v-else-if="activeTab === 'actions'"
                            :actions="actionDefs"
                            :available-protocols="availableProtocols"
                            @update:actions="actionDefs = $event"
                        />

                        <!-- Tab: Status / Subscribe (coming soon) -->
                        <TabPlaceholder v-else-if="activeTab === 'status'"  label="Status / Subscribe" :issue="30" />

                        <!-- Tab: Preview / Icon -->
                        <PreviewView
                            v-else-if="activeTab === 'preview'"
                            :icon="iconAsset"
                            :plugin-id="editPluginId"
                            @update:icon="iconAsset = $event"
                        />

                    </div>

                    <!-- Footer -->
                    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border shrink-0">
                        <div v-if="saveError" class="flex items-center gap-1.5 text-xs text-destructive mr-auto">
                            <RiErrorWarningLine class="size-3.5 shrink-0" />
                            {{ saveError }}
                        </div>
                        <Button variant="outline" size="sm" @click="emit('update:show', false)">
                            Cancel
                        </Button>
                        <Button size="sm" class="gap-1.5" :disabled="saving || !canSave" @click="save">
                            <RiLoader4Line v-if="saving" class="size-3.5 animate-spin" />
                            <RiCheckLine v-else class="size-3.5" />
                            {{ editPluginId ? "Save changes" : "Create plugin" }}
                        </Button>
                    </div>

                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>