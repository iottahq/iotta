<script setup lang="ts">
import { ref, computed } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import FilePreviewPanel from "@/components/ui/file-preview/FilePreviewPanel.vue";
import FilePreviewToggle from "@/components/ui/file-preview/FilePreviewToggle.vue";
import {
    RiAddLine,
    RiDeleteBinLine,
    RiDraggable,
    RiInformationLine,
    RiArrowDownSLine,
    RiArrowRightSLine,
} from "@remixicon/vue";

// Types

export interface InputField {
    key: string;
    type: string;
    required: boolean;
    default?: string;
}

export interface ActionDef {
    // internal editor id
    _id: string;
    name: string;
    label: string;
    protocol: string;
    method: string;
    topic: string;
    payloadJson: string;  // raw JSON string
    inputFields: InputField[];
    exampleJson: string;  // raw JSON string
}

// Props / Emits

const props = defineProps<{
    actions: ActionDef[];
    availableProtocols: { id: string; name: string }[];
}>();

const emit = defineEmits<{
    "update:actions": [v: ActionDef[]];
}>();

// State

const showJson   = ref(false);
const collapsed  = ref<Record<string, boolean>>({});
const dragId     = ref<string | null>(null);
const overId     = ref<string | null>(null);

// Helpers

let _counter = 0;
function uid() { return `a_${Date.now()}_${_counter++}`; }

// Default methods per protocol
const PROTOCOL_METHODS: Record<string, string[]> = {
    mqtt:      ["publish", "subscribe"],
    ftp:       ["list", "upload", "download", "delete", "mkdir"],
    http:      ["get", "post", "put", "patch", "delete", "head"],
    ws:        ["send"],
};

function methodsFor(protocolId: string): string[] {
    return PROTOCOL_METHODS[protocolId] ?? ["send"];
}

function newAction(): ActionDef {
    const proto = props.availableProtocols[0]?.id ?? "";
    const methods = methodsFor(proto);
    return {
        _id: uid(),
        name: "",
        label: "",
        protocol: proto,
        method: methods[0] ?? "",
        topic: "",
        payloadJson: "{}",
        inputFields: [],
        exampleJson: "{}",
    };
}

function add() {
    emit("update:actions", [...props.actions, newAction()]);
}

function remove(id: string) {
    emit("update:actions", props.actions.filter((a) => a._id !== id));
}

function update(id: string, patch: Partial<ActionDef>) {
    emit("update:actions", props.actions.map((a) => a._id === id ? { ...a, ...patch } : a));
}

function toggleCollapse(id: string) {
    collapsed.value[id] = !collapsed.value[id];
}

// Input field helpers

function addInputField(actionId: string) {
    const action = props.actions.find((a) => a._id === actionId);
    if (!action) return;
    update(actionId, {
        inputFields: [...action.inputFields, { key: "", type: "string", required: true }],
    });
}

function removeInputField(actionId: string, idx: number) {
    const action = props.actions.find((a) => a._id === actionId);
    if (!action) return;
    const next = [...action.inputFields];
    next.splice(idx, 1);
    update(actionId, { inputFields: next });
}

function updateInputField(actionId: string, idx: number, patch: Partial<InputField>) {
    const action = props.actions.find((a) => a._id === actionId);
    if (!action) return;
    const next = action.inputFields.map((f, i) => i === idx ? { ...f, ...patch } : f);
    update(actionId, { inputFields: next });
}

// Drag and drop within a category

function onDragStart(id: string) { dragId.value = id; }
function onDragOver(e: DragEvent, id: string) { e.preventDefault(); overId.value = id; }
function onDrop(targetId: string) {
    if (!dragId.value || dragId.value === targetId) {
        dragId.value = null; overId.value = null; return;
    }
    const next = [...props.actions];
    const from = next.findIndex((a) => a._id === dragId.value);
    const to   = next.findIndex((a) => a._id === targetId);
    if (from === -1 || to === -1) { dragId.value = null; overId.value = null; return; }
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    emit("update:actions", next);
    dragId.value = null; overId.value = null;
}
function onDragEnd() { dragId.value = null; overId.value = null; }

// JSON preview

function buildActionsJson(): Record<string, unknown> {
    const actions: Record<string, unknown> = {};

    for (const a of props.actions) {
        if (!a.name.trim()) continue;

        const def: Record<string, unknown> = {
            protocol: a.protocol,
            label: a.label || a.name,
        };

        if (a.method) def.method = a.method;
        if (a.topic.trim()) def.topic = a.topic.trim();

        try { def.payload = JSON.parse(a.payloadJson); } catch { def.payload = {}; }

        if (a.inputFields.length) {
            const inp: Record<string, unknown> = {};
            for (const f of a.inputFields) {
                if (f.key.trim()) {
                    const fd: Record<string, unknown> = { type: f.type, required: f.required };
                    if (f.default !== undefined && f.default !== "") fd.default = f.default;
                    inp[f.key] = fd;
                }
            }
            if (Object.keys(inp).length) def.input = inp;
        }

        try {
            const ex = JSON.parse(a.exampleJson);
            if (Object.keys(ex).length) def.example = ex;
        } catch { /* skip */ }

        actions[a.name.trim()] = def;
    }

    return { actions };
}

const jsonPreview = computed(() =>
    JSON.stringify(buildActionsJson(), null, 4)
);
</script>

<template>
    <div class="flex items-stretch w-full">

        <!-- Main editor area -->
        <div class="flex-1 min-w-0 flex flex-col gap-4 px-6 py-5 overflow-y-auto">

            <!-- Info banner -->
            <div class="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2.5 text-[11px] text-muted-foreground">
                <RiInformationLine class="size-3.5 shrink-0 mt-px text-muted-foreground/70" />
                <span>
                    Define actions this plugin exposes. Each action is called via
                    <code class="font-mono bg-muted px-1 rounded text-[10px]">POST /action/{name}</code> and returns a response from the device.
                    Use <code class="font-mono bg-muted px-1 rounded text-[10px]">{credential_field}</code> in topics and payloads (e.g. <code class="font-mono bg-muted px-1 rounded text-[10px]">{serial}</code>).
                </span>
            </div>

            <!-- Actions list -->
            <div class="flex flex-col gap-2">

                <!-- Header -->
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Actions
                        <span class="font-normal text-muted-foreground/50 tabular-nums ml-1">{{ actions.length }}</span>
                    </span>
                    <Button variant="ghost" size="sm" class="gap-1 h-6 px-1.5 text-muted-foreground" @click="add()">
                        <RiAddLine class="size-3" />
                        Add
                    </Button>
                </div>

                <!-- Empty state -->
                <div
                    v-if="actions.length === 0"
                    class="flex items-center justify-center rounded-lg border border-dashed border-border py-5 text-[11px] text-muted-foreground"
                >
                    No actions defined — click Add
                </div>

                <!-- Action cards -->
                <div
                    v-for="action in actions"
                    :key="action._id"
                        class="group rounded-lg border bg-card transition-colors"
                        :class="[
                            overId === action._id && dragId !== action._id
                                ? 'border-primary/50 bg-primary/5'
                                : 'border-border',
                            dragId === action._id ? 'opacity-40 scale-[0.99]' : '',
                        ]"
                        draggable="true"
                        @dragstart="onDragStart(action._id)"
                        @dragover="onDragOver($event, action._id)"
                        @drop="onDrop(action._id)"
                        @dragend="onDragEnd"
                    >
                        <!-- Card header -->
                        <div
                            class="flex items-center gap-2 px-3 py-2.5 cursor-pointer select-none hover:bg-muted/30 transition-colors rounded-t-lg"
                            @click="toggleCollapse(action._id)"
                        >
                            <!-- Drag handle -->
                            <div class="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground/40 hover:text-muted-foreground cursor-grab shrink-0">
                                <RiDraggable class="size-3.5" />
                            </div>

                            <component
                                :is="collapsed[action._id] ? RiArrowRightSLine : RiArrowDownSLine"
                                class="size-3.5 text-muted-foreground shrink-0"
                            />

                            <!-- Name badge -->
                            <code
                                class="text-[11px] font-mono px-1.5 py-px rounded bg-muted text-foreground/80 truncate"
                                :class="!action.name ? 'text-muted-foreground italic' : ''"
                            >
                                {{ action.name || "unnamed" }}
                            </code>

                            <span v-if="action.label" class="text-[11px] text-muted-foreground truncate flex-1">
                                {{ action.label }}
                            </span>
                            <div v-else class="flex-1" />

                            <!-- Protocol badge -->
                            <span
                                v-if="action.protocol"
                                class="shrink-0 text-[9px] font-mono px-1.5 py-px rounded-full border border-border text-muted-foreground/60"
                            >
                                {{ action.protocol }}
                            </span>

                            <span
                                v-if="action.method"
                                class="shrink-0 text-[9px] font-mono px-1.5 py-px rounded-full border border-border text-muted-foreground/60"
                            >
                                {{ action.method }}
                            </span>

                            <!-- Delete -->
                            <button
                                class="shrink-0 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100 ml-1"
                                @click.stop="remove(action._id)"
                            >
                                <RiDeleteBinLine class="size-3.5" />
                            </button>
                        </div>

                        <!-- Card body -->
                        <div v-if="!collapsed[action._id]" class="border-t border-border px-3 py-3 flex flex-col gap-3">

                            <!-- Row 1: name + label -->
                            <div class="grid grid-cols-2 gap-2">
                                <div class="flex flex-col gap-1">
                                    <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                                        Action name <span class="text-destructive">*</span>
                                    </label>
                                    <Input
                                        :model-value="action.name"
                                        placeholder="e.g. print"
                                        class="h-7 text-xs font-mono"
                                        @update:model-value="update(action._id, { name: $event as string })"
                                    />
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Label</label>
                                    <Input
                                        :model-value="action.label"
                                        placeholder="e.g. Start Print"
                                        class="h-7 text-xs"
                                        @update:model-value="update(action._id, { label: $event as string })"
                                    />
                                </div>
                            </div>

                            <!-- Row 2: protocol + method -->
                            <div class="grid grid-cols-2 gap-2">
                                <div class="flex flex-col gap-1">
                                    <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Protocol</label>
                                    <select
                                        :value="action.protocol"
                                        class="h-7 rounded-md border border-input bg-input/20 dark:bg-input/30 px-2 text-xs outline-none"
                                        @change="update(action._id, {
                                            protocol: ($event.target as HTMLSelectElement).value,
                                            method: methodsFor(($event.target as HTMLSelectElement).value)[0] ?? '',
                                        })"
                                    >
                                        <option value="" disabled>Select protocol…</option>
                                        <option v-for="p in availableProtocols" :key="p.id" :value="p.id">
                                            {{ p.name }}
                                        </option>
                                    </select>
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Method</label>
                                    <select
                                        v-if="methodsFor(action.protocol).length > 0"
                                        :value="action.method"
                                        class="h-7 rounded-md border border-input bg-input/20 dark:bg-input/30 px-2 text-xs font-mono outline-none"
                                        @change="update(action._id, { method: ($event.target as HTMLSelectElement).value })"
                                    >
                                        <option v-for="m in methodsFor(action.protocol)" :key="m" :value="m">{{ m }}</option>
                                    </select>
                                    <Input
                                        v-else
                                        :model-value="action.method"
                                        placeholder="method"
                                        class="h-7 text-xs font-mono"
                                        @update:model-value="update(action._id, { method: $event as string })"
                                    />
                                </div>
                            </div>

                            <!-- Topic -->
                            <div class="flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                                    Topic
                                    <span class="normal-case font-normal text-muted-foreground/50">(optional for non-MQTT)</span>
                                </label>
                                <Input
                                    :model-value="action.topic"
                                    placeholder="device/{serial}/request"
                                    class="h-7 text-xs font-mono"
                                    @update:model-value="update(action._id, { topic: $event as string })"
                                />
                            </div>

                            <!-- Payload JSON -->
                            <div class="flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Payload</label>
                                <textarea
                                    :value="action.payloadJson"
                                    rows="5"
                                    spellcheck="false"
                                    placeholder='{"command": "pause"}'
                                    class="w-full rounded-md border border-border bg-input/20 dark:bg-input/30 px-2.5 py-2 font-mono text-[11px] text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors placeholder:text-muted-foreground"
                                    @input="update(action._id, { payloadJson: ($event.target as HTMLTextAreaElement).value })"
                                />
                            </div>

                            <!-- Input fields -->
                            <div class="flex flex-col gap-2">
                                <div class="flex items-center justify-between">
                                    <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Input fields</label>
                                    <Button
                                        variant="ghost" size="sm"
                                        class="gap-1 h-6 px-1.5 text-muted-foreground"
                                        @click="addInputField(action._id)"
                                    >
                                        <RiAddLine class="size-3" /> Add field
                                    </Button>
                                </div>

                                <div
                                    v-if="action.inputFields.length === 0"
                                    class="flex items-center justify-center rounded-md border border-dashed border-border/60 py-3 text-[10px] text-muted-foreground/60"
                                >
                                    No input fields — body will be passed as-is
                                </div>

                                <div
                                    v-for="(field, fi) in action.inputFields"
                                    :key="fi"
                                    class="grid grid-cols-[1fr_auto_auto_auto_auto] gap-1.5 items-center"
                                >
                                    <Input
                                        :model-value="field.key"
                                        placeholder="field_name"
                                        class="h-6 text-[11px] font-mono"
                                        @update:model-value="updateInputField(action._id, fi, { key: $event as string })"
                                    />
                                    <select
                                        :value="field.type"
                                        class="h-6 rounded-md border border-input bg-input/20 dark:bg-input/30 px-1.5 text-[11px] font-mono outline-none"
                                        @change="updateInputField(action._id, fi, { type: ($event.target as HTMLSelectElement).value })"
                                    >
                                        <option value="string">string</option>
                                        <option value="integer">integer</option>
                                        <option value="number">number</option>
                                        <option value="boolean">boolean</option>
                                        <option value="bytes">bytes</option>
                                    </select>
                                    <Input
                                        :model-value="field.default ?? ''"
                                        placeholder="default"
                                        class="h-6 text-[11px] font-mono w-20"
                                        @update:model-value="updateInputField(action._id, fi, { default: $event as string || undefined })"
                                    />
                                    <button
                                        type="button"
                                        class="h-6 px-1.5 rounded border text-[9px] font-medium transition-colors"
                                        :class="field.required
                                            ? 'border-primary/40 bg-primary/10 text-primary'
                                            : 'border-border text-muted-foreground hover:text-foreground'"
                                        @click="updateInputField(action._id, fi, { required: !field.required })"
                                    >
                                        req
                                    </button>
                                    <button
                                        class="text-muted-foreground hover:text-destructive transition-colors"
                                        @click="removeInputField(action._id, fi)"
                                    >
                                        <RiDeleteBinLine class="size-3.5" />
                                    </button>
                                </div>
                            </div>

                            <!-- Example JSON -->
                            <div class="flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                                    Example
                                    <span class="normal-case font-normal text-muted-foreground/50">(shown in Swagger UI)</span>
                                </label>
                                <textarea
                                    :value="action.exampleJson"
                                    rows="3"
                                    spellcheck="false"
                                    placeholder='{}'
                                    class="w-full rounded-md border border-border bg-input/20 dark:bg-input/30 px-2.5 py-2 font-mono text-[11px] text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors placeholder:text-muted-foreground"
                                    @input="update(action._id, { exampleJson: ($event.target as HTMLTextAreaElement).value })"
                                />
                            </div>

                        </div>
                    </div>
                </div>

            <!-- JSON preview toggle -->
            <div class="pt-1">
                <FilePreviewToggle
                    :show="showJson"
                    filename="actions.json"
                    @update:show="showJson = $event"
                />
            </div>
        </div>

        <!-- JSON preview panel -->
        <FilePreviewPanel
            :show="showJson"
            filename="actions.json"
            :content="jsonPreview"
            @update:show="showJson = $event"
        />
    </div>
</template>