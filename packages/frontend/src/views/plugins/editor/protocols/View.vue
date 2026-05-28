<script setup lang="ts">
import { ref, computed } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import FilePreviewPanel from "@/components/ui/file-preview/FilePreviewPanel.vue";
import FilePreviewToggle from "@/components/ui/file-preview/FilePreviewToggle.vue";
import {
    RiAddLine,
    RiDeleteBinLine,
    RiSignalWifiLine,
    RiInformationLine,
    RiArrowDownSLine,
    RiArrowRightSLine,
    RiCheckLine,
} from "@remixicon/vue";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ProtocolConfig {
    protocolId: string;
    config: Record<string, unknown>;
}

// A single capability from capabilities.yaml, as returned by the API:
// GET /plugins/protocols/{id} → meta.capabilities → { action_id: { input: { field: { type, required, default, description } } } }
interface CapabilityInputField {
    type?: string;
    required?: boolean;
    default?: unknown;
    description?: string;
    enum?: string[];
}

interface Capability {
    label?: string;
    description?: string;
    input?: Record<string, CapabilityInputField>;
    output?: Record<string, unknown>;
}

// ── Props / Emits ─────────────────────────────────────────────────────────────

const props = defineProps<{
    blocks: ProtocolConfig[];
    // availableProtocols already carries meta.capabilities from the loader
    availableProtocols: { id: string; name: string; capabilities?: Record<string, Capability> }[];
}>();

const emit = defineEmits<{
    "update:blocks": [v: ProtocolConfig[]];
}>();

// ── State ─────────────────────────────────────────────────────────────────────

const showJson   = ref(false);
const collapsed  = ref<Record<number, boolean>>({});
const showPicker = ref(false);

// ── Derive config fields from capabilities ────────────────────────────────────

/**
 * Collect all unique input fields across all capabilities of a protocol.
 * e.g. mqtt has publish (topic, payload, qos) and subscribe (topics) → merged set.
 *
 * For protocols like mqtt/ftp/http, the "connection config" fields (host, port, tls…)
 * are NOT part of capabilities (capabilities describe actions, not connection params).
 * So we also include a hard-coded set of connection fields per protocol_name that
 * are universally needed. These are minimal and obvious – host/port/tls/auth –
 * NOT the full action schemas which DO come from capabilities.
 */

interface ConfigFieldDef {
    key: string;
    label: string;
    valueType: "string" | "number" | "boolean" | "array" | "object";
    placeholder?: string;
    description?: string;
    defaultValue?: unknown;
    required?: boolean;
    enumValues?: string[];
    source: "connection" | "capability";
    capabilityId?: string;
}

// Minimal connection-level fields that every protocol needs to connect.
// These are NOT in capabilities.yaml (which only describes actions).
// This will change in the future 
const CONNECTION_FIELDS: Record<string, ConfigFieldDef[]> = {
    mqtt: [
        { key: "host",               label: "Host",               valueType: "string",  placeholder: "{ip}",            required: true,  source: "connection" },
        { key: "port",               label: "Port",               valueType: "number",  placeholder: "8883",            defaultValue: 8883, source: "connection" },
        { key: "tls",                label: "TLS",                valueType: "boolean", defaultValue: true,             source: "connection" },
        { key: "username",           label: "Username",           valueType: "string",  placeholder: "{username}",      source: "connection" },
        { key: "password",           label: "Password",           valueType: "string",  placeholder: "{access_code}",   source: "connection" },
        { key: "subscribe_topics",   label: "Subscribe topics",   valueType: "array",   placeholder: "device/{serial}/report", description: "One topic per line", source: "connection" },
        { key: "on_connect_publish", label: "On-connect publish", valueType: "object",  placeholder: '{"topic":"...","payload":{}}', description: "Published immediately after connecting", source: "connection" },
        { key: "methods",            label: "Allowed methods",    valueType: "array",   placeholder: "publish", description: "Leave empty for all", source: "connection" },
    ],
    ftp: [
        { key: "host",     label: "Host",       valueType: "string",  placeholder: "{ip}",          required: true, source: "connection" },
        { key: "port",     label: "Port",       valueType: "number",  placeholder: "990",            defaultValue: 990, source: "connection" },
        { key: "tls",      label: "TLS mode",   valueType: "string",  placeholder: "implicit",       description: "none | explicit | implicit", source: "connection" },
        { key: "username", label: "Username",   valueType: "string",  placeholder: "{username}",    source: "connection" },
        { key: "password", label: "Password",   valueType: "string",  placeholder: "{access_code}", source: "connection" },
        { key: "methods",  label: "Methods",    valueType: "string",  placeholder: "all",            description: 'Comma-separated capability IDs or "all"', source: "connection" },
    ],
    http: [
        { key: "base_url",   label: "Base URL",    valueType: "string",  placeholder: "http://{ip}", required: true, source: "connection" },
        { key: "timeout",    label: "Timeout (s)", valueType: "number",  placeholder: "10",           defaultValue: 10, source: "connection" },
        { key: "verify_ssl", label: "Verify SSL",  valueType: "boolean", defaultValue: false,         source: "connection" },
        { key: "auth",       label: "Auth",        valueType: "object",  placeholder: '{"type":"bearer","token":"{token}"}', description: "bearer | basic | api-key | none", source: "connection" },
    ],
    ws: [
        { key: "url",     label: "URL",     valueType: "string", placeholder: "ws://{ip}:{port}/ws", required: true, source: "connection" },
        { key: "headers", label: "Headers", valueType: "object", placeholder: '{"Authorization":"Bearer {token}"}', description: "Extra HTTP headers for the handshake", source: "connection" },
    ],
};

function capabilityInputToFieldDef(
    capId: string,
    fieldKey: string,
    fieldDef: CapabilityInputField,
): ConfigFieldDef {
    let valueType: ConfigFieldDef["valueType"] = "string";
    const t = (fieldDef.type ?? "string").toLowerCase();
    if (t === "integer" || t === "number") valueType = "number";
    else if (t === "boolean") valueType = "boolean";
    else if (t === "array") valueType = "array";
    else if (t === "object") valueType = "object";

    return {
        key: fieldKey,
        label: fieldKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        valueType,
        description: fieldDef.description,
        defaultValue: fieldDef.default,
        required: fieldDef.required,
        enumValues: fieldDef.enum,
        source: "capability",
        capabilityId: capId,
    };
}

function getConfigFields(protocolId: string): ConfigFieldDef[] {
    const proto = props.availableProtocols.find((p) => p.id === protocolId);
    const capabilities = proto?.capabilities ?? {};
    const connectionFields = CONNECTION_FIELDS[protocolId] ?? [
        { key: "host", label: "Host", valueType: "string" as const, placeholder: "hostname or IP", required: true, source: "connection" as const },
        { key: "port", label: "Port", valueType: "number" as const, placeholder: "port number", source: "connection" as const },
    ];

    // Collect capability-derived fields (deduplicated by key, skipping keys already in connectionFields)
    const connectionKeys = new Set(connectionFields.map((f) => f.key));
    const capabilityFieldMap = new Map<string, ConfigFieldDef>();

    for (const [capId, cap] of Object.entries(capabilities)) {
        for (const [fieldKey, fieldDef] of Object.entries(cap.input ?? {})) {
            if (connectionKeys.has(fieldKey)) continue;
            if (!capabilityFieldMap.has(fieldKey)) {
                capabilityFieldMap.set(fieldKey, capabilityInputToFieldDef(capId, fieldKey, fieldDef));
            }
        }
    }

    return [...connectionFields, ...capabilityFieldMap.values()];
}

// ── Block management ──────────────────────────────────────────────────────────

function isAdded(protocolId: string) {
    return props.blocks.some((b) => b.protocolId === protocolId);
}

function addProtocol(protocolId: string) {
    showPicker.value = false;
    if (isAdded(protocolId)) return;

    const fields = getConfigFields(protocolId);
    const config: Record<string, unknown> = {};
    for (const f of fields) {
        if (f.defaultValue !== undefined) config[f.key] = f.defaultValue;
    }
    emit("update:blocks", [...props.blocks, { protocolId, config }]);
}

function removeProtocol(i: number) {
    const next = [...props.blocks];
    next.splice(i, 1);
    const newCollapsed: Record<number, boolean> = {};
    for (const [k, v] of Object.entries(collapsed.value)) {
        const ki = Number(k);
        if (ki < i) newCollapsed[ki] = v;
        else if (ki > i) newCollapsed[ki - 1] = v;
    }
    collapsed.value = newCollapsed;
    emit("update:blocks", next);
}

function toggleCollapse(i: number) {
    collapsed.value[i] = !collapsed.value[i];
}

function updateField(blockIdx: number, key: string, raw: string, valueType: ConfigFieldDef["valueType"]) {
    let value: unknown = raw;

    if (valueType === "number") {
        value = raw === "" ? undefined : Number(raw);
    } else if (valueType === "boolean") {
        value = raw === "true";
    } else if (valueType === "array") {
        const arr = raw.split("\n").map((s) => s.trim()).filter(Boolean);
        value = arr.length === 0 ? undefined : arr;
    } else if (valueType === "object") {
        try { value = JSON.parse(raw); } catch { value = raw || undefined; }
    } else {
        value = raw || undefined;
    }

    const newConfig = { ...props.blocks[blockIdx].config };
    if (value === undefined) delete newConfig[key];
    else newConfig[key] = value;

    emit("update:blocks", props.blocks.map((b, idx) =>
        idx === blockIdx ? { ...b, config: newConfig } : b
    ));
}

function getFieldValue(blockIdx: number, key: string, valueType: ConfigFieldDef["valueType"]): string {
    const val = props.blocks[blockIdx]?.config[key];
    if (val === undefined || val === null) return "";
    if (Array.isArray(val)) return val.join("\n");
    if (typeof val === "object") return JSON.stringify(val, null, 2);
    return String(val);
}

function protocolName(id: string) {
    return props.availableProtocols.find((p) => p.id === id)?.name ?? id;
}

const unusedProtocols = computed(() =>
    props.availableProtocols.filter((p) => !isAdded(p.id))
);

const jsonPreview = computed(() => {
    const obj: Record<string, unknown> = {};
    for (const b of props.blocks) obj[b.protocolId] = b.config;
    return JSON.stringify(obj, null, 4);
});
</script>

<template>
    <div class="flex items-stretch w-full">

        <div class="flex-1 min-w-0 flex flex-col gap-3 px-6 py-5 overflow-y-auto">

            <!-- Info banner -->
            <div class="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2.5 text-[11px] text-muted-foreground">
                <RiInformationLine class="size-3.5 shrink-0 mt-px text-muted-foreground/70" />
                <span>
                    Add the protocols this plugin uses and configure their connection parameters.
                    Fields are derived from each protocol's <code class="font-mono bg-muted px-1 rounded text-[10px]">capabilities.yaml</code>.
                    Use <code class="font-mono bg-muted px-1 rounded text-[10px]">{credential_field}</code> to reference credential values
                    (e.g. <code class="font-mono bg-muted px-1 rounded text-[10px]">{ip}</code>, <code class="font-mono bg-muted px-1 rounded text-[10px]">{access_code}</code>).
                </span>
            </div>

            <!-- Protocol blocks -->
            <div v-if="blocks.length" class="flex flex-col gap-2">
                <div
                    v-for="(block, i) in blocks"
                    :key="block.protocolId"
                    class="rounded-lg border border-border bg-card overflow-hidden"
                >
                    <!-- Block header -->
                    <div
                        class="flex items-center gap-2 px-3 py-2.5 cursor-pointer select-none hover:bg-muted/30 transition-colors"
                        @click="toggleCollapse(i)"
                    >
                        <component
                            :is="collapsed[i] ? RiArrowRightSLine : RiArrowDownSLine"
                            class="size-3.5 text-muted-foreground shrink-0"
                        />
                        <RiSignalWifiLine class="size-3.5 text-muted-foreground shrink-0" />
                        <span class="text-xs font-medium font-mono flex-1">{{ block.protocolId }}</span>
                        <span class="text-[10px] text-muted-foreground">{{ protocolName(block.protocolId) }}</span>
                        <button
                            class="text-muted-foreground hover:text-destructive transition-colors ml-2"
                            @click.stop="removeProtocol(i)"
                        >
                            <RiDeleteBinLine class="size-3.5" />
                        </button>
                    </div>

                    <!-- Block fields -->
                    <div v-if="!collapsed[i]" class="border-t border-border px-3 py-3 flex flex-col gap-3">

                        <!-- Section: Connection -->
                        <div class="flex flex-col gap-2.5">
                            <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/60">Connection</p>

                            <div
                                v-for="field in getConfigFields(block.protocolId).filter(f => f.source === 'connection')"
                                :key="field.key"
                                class="flex flex-col gap-1"
                            >
                                <div class="flex items-center gap-1.5">
                                    <label class="text-[10px] font-medium text-muted-foreground">
                                        {{ field.label }}
                                        <span v-if="field.required" class="text-destructive">*</span>
                                    </label>
                                    <span class="text-[9px] font-mono text-muted-foreground/40">{{ field.key }}</span>
                                </div>

                                <!-- Boolean toggle -->
                                <div v-if="field.valueType === 'boolean'" class="flex items-center gap-2">
                                    <button
                                        type="button"
                                        class="relative w-7 h-4 rounded-full transition-colors focus:outline-none"
                                        :class="getFieldValue(i, field.key, field.valueType) === 'true' ? 'bg-primary' : 'bg-muted-foreground/30'"
                                        @click="updateField(i, field.key, getFieldValue(i, field.key, field.valueType) === 'true' ? 'false' : 'true', field.valueType)"
                                    >
                                        <span
                                            class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
                                            :class="getFieldValue(i, field.key, field.valueType) === 'true' ? 'translate-x-3' : 'translate-x-0'"
                                        />
                                    </button>
                                    <span class="text-[11px] text-muted-foreground">
                                        {{ getFieldValue(i, field.key, field.valueType) === 'true' ? 'Enabled' : 'Disabled' }}
                                    </span>
                                </div>

                                <!-- Textarea for array/object -->
                                <textarea
                                    v-else-if="field.valueType === 'array' || field.valueType === 'object'"
                                    :value="getFieldValue(i, field.key, field.valueType)"
                                    :placeholder="field.placeholder"
                                    :rows="field.valueType === 'array' ? 3 : 4"
                                    spellcheck="false"
                                    class="w-full rounded-md border border-border bg-input/20 dark:bg-input/30 px-2.5 py-2 font-mono text-[11px] text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors placeholder:text-muted-foreground"
                                    @input="updateField(i, field.key, ($event.target as HTMLTextAreaElement).value, field.valueType)"
                                />

                                <!-- Number -->
                                <Input
                                    v-else-if="field.valueType === 'number'"
                                    type="number"
                                    :model-value="getFieldValue(i, field.key, field.valueType)"
                                    :placeholder="field.placeholder"
                                    class="font-mono text-xs h-7"
                                    @update:model-value="updateField(i, field.key, String($event), field.valueType)"
                                />

                                <!-- Enum select -->
                                <select
                                    v-else-if="field.enumValues?.length"
                                    :value="getFieldValue(i, field.key, field.valueType)"
                                    class="bg-input/20 dark:bg-input/30 border-input h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none font-mono"
                                    @change="updateField(i, field.key, ($event.target as HTMLSelectElement).value, field.valueType)"
                                >
                                    <option value="">–</option>
                                    <option v-for="v in field.enumValues" :key="v" :value="v">{{ v }}</option>
                                </select>

                                <!-- String -->
                                <Input
                                    v-else
                                    :model-value="getFieldValue(i, field.key, field.valueType)"
                                    :placeholder="field.placeholder"
                                    class="font-mono text-xs h-7"
                                    @update:model-value="updateField(i, field.key, String($event), field.valueType)"
                                />

                                <p v-if="field.description" class="text-[10px] text-muted-foreground/70">
                                    {{ field.description }}
                                </p>
                            </div>
                        </div>

                        <!-- Section: Capability fields (from capabilities.yaml) -->
                        <template v-if="getConfigFields(block.protocolId).some(f => f.source === 'capability')">
                            <div class="h-px bg-border/60" />
                            <div class="flex flex-col gap-2.5">
                                <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                                    Capability defaults
                                    <span class="normal-case font-normal text-muted-foreground/40">(from capabilities.yaml)</span>
                                </p>

                                <div
                                    v-for="field in getConfigFields(block.protocolId).filter(f => f.source === 'capability')"
                                    :key="field.key"
                                    class="flex flex-col gap-1"
                                >
                                    <div class="flex items-center gap-1.5">
                                        <label class="text-[10px] font-medium text-muted-foreground">
                                            {{ field.label }}
                                        </label>
                                        <span class="text-[9px] font-mono text-muted-foreground/40">{{ field.key }}</span>
                                        <span v-if="field.capabilityId" class="text-[9px] px-1 rounded bg-muted text-muted-foreground/50 font-mono">
                                            {{ field.capabilityId }}
                                        </span>
                                    </div>

                                    <div v-if="field.valueType === 'boolean'" class="flex items-center gap-2">
                                        <button
                                            type="button"
                                            class="relative w-7 h-4 rounded-full transition-colors focus:outline-none"
                                            :class="getFieldValue(i, field.key, field.valueType) === 'true' ? 'bg-primary' : 'bg-muted-foreground/30'"
                                            @click="updateField(i, field.key, getFieldValue(i, field.key, field.valueType) === 'true' ? 'false' : 'true', field.valueType)"
                                        >
                                            <span
                                                class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
                                                :class="getFieldValue(i, field.key, field.valueType) === 'true' ? 'translate-x-3' : 'translate-x-0'"
                                            />
                                        </button>
                                        <span class="text-[11px] text-muted-foreground">
                                            {{ getFieldValue(i, field.key, field.valueType) === 'true' ? 'Enabled' : 'Disabled' }}
                                        </span>
                                    </div>
                                    <textarea
                                        v-else-if="field.valueType === 'array' || field.valueType === 'object'"
                                        :value="getFieldValue(i, field.key, field.valueType)"
                                        :placeholder="field.placeholder"
                                        :rows="3"
                                        spellcheck="false"
                                        class="w-full rounded-md border border-border bg-input/20 dark:bg-input/30 px-2.5 py-2 font-mono text-[11px] text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors placeholder:text-muted-foreground"
                                        @input="updateField(i, field.key, ($event.target as HTMLTextAreaElement).value, field.valueType)"
                                    />
                                    <select
                                        v-else-if="field.enumValues?.length"
                                        :value="getFieldValue(i, field.key, field.valueType)"
                                        class="bg-input/20 dark:bg-input/30 border-input h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none font-mono"
                                        @change="updateField(i, field.key, ($event.target as HTMLSelectElement).value, field.valueType)"
                                    >
                                        <option value="">–</option>
                                        <option v-for="v in field.enumValues" :key="v" :value="v">{{ v }}</option>
                                    </select>
                                    <Input
                                        v-else-if="field.valueType === 'number'"
                                        type="number"
                                        :model-value="getFieldValue(i, field.key, field.valueType)"
                                        class="font-mono text-xs h-7"
                                        @update:model-value="updateField(i, field.key, String($event), field.valueType)"
                                    />
                                    <Input
                                        v-else
                                        :model-value="getFieldValue(i, field.key, field.valueType)"
                                        :placeholder="field.placeholder"
                                        class="font-mono text-xs h-7"
                                        @update:model-value="updateField(i, field.key, String($event), field.valueType)"
                                    />

                                    <p v-if="field.description" class="text-[10px] text-muted-foreground/70">
                                        {{ field.description }}
                                    </p>
                                </div>
                            </div>
                        </template>

                    </div>
                </div>
            </div>

            <!-- Empty state -->
            <div
                v-else
                class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-10 text-center"
            >
                <RiSignalWifiLine class="size-6 text-muted-foreground/30 mb-2" />
                <p class="text-xs text-muted-foreground">No protocols added yet.</p>
                <p class="text-[11px] text-muted-foreground/60 mt-0.5">Add the protocols this plugin depends on.</p>
            </div>

            <!-- Add protocol + picker -->
            <div class="relative w-fit">
                <Button variant="outline" size="sm" class="gap-1.5" @click="showPicker = !showPicker">
                    <RiAddLine class="size-3.5" />
                    Add protocol
                </Button>

                <div
                    v-if="showPicker"
                    class="absolute top-full left-0 mt-1 z-50 min-w-[200px] rounded-lg border border-border bg-popover shadow-lg py-1 overflow-hidden"
                >
                    <div
                        v-if="availableProtocols.length === 0"
                        class="px-3 py-2 text-[11px] text-muted-foreground"
                    >
                        No protocol plugins loaded
                    </div>
                    <button
                        v-for="proto in availableProtocols"
                        :key="proto.id"
                        class="flex items-center gap-2.5 w-full px-3 py-1.5 text-xs text-left transition-colors"
                        :class="isAdded(proto.id)
                            ? 'text-muted-foreground/50 cursor-default'
                            : 'text-foreground hover:bg-muted/70 cursor-pointer'"
                        @click="!isAdded(proto.id) && addProtocol(proto.id)"
                    >
                        <RiCheckLine v-if="isAdded(proto.id)" class="size-3.5 text-primary shrink-0" />
                        <RiSignalWifiLine v-else class="size-3.5 text-muted-foreground shrink-0" />
                        <span class="font-medium">{{ proto.name }}</span>
                        <span class="font-mono text-[10px] text-muted-foreground ml-auto">{{ proto.id }}</span>
                    </button>
                </div>

                <div v-if="showPicker" class="fixed inset-0 z-40" @click="showPicker = false" />
            </div>

            <!-- JSON preview toggle -->
            <div class="pt-1">
                <FilePreviewToggle
                    :show="showJson"
                    filename="protocols.json"
                    @update:show="showJson = $event"
                />
            </div>
        </div>

        <!-- JSON preview panel -->
        <FilePreviewPanel
            :show="showJson"
            filename="protocols.json"
            :content="jsonPreview"
            @update:show="showJson = $event"
        />
    </div>
</template>