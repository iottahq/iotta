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
    RiLockLine,
} from "@remixicon/vue";

// Types

export interface CredentialField {
    field: string;
    type: "string" | "password" | "number" | "boolean";
    label: string;
    placeholder?: string;
    required: boolean;
    secret: boolean;
}

// Props / Emits

const props = defineProps<{
    fields: CredentialField[];
}>();

const emit = defineEmits<{
    "update:fields": [v: CredentialField[]];
}>();

// State

const showJson  = ref(false);
const dragIndex = ref<number | null>(null);
const overIndex = ref<number | null>(null);

// Helpers

function newField(): CredentialField {
    return { field: "", type: "string", label: "", placeholder: "", required: true, secret: false };
}

function addField() {
    emit("update:fields", [...props.fields, newField()]);
}

function removeField(i: number) {
    const next = [...props.fields];
    next.splice(i, 1);
    emit("update:fields", next);
}

function updateField(i: number, patch: Partial<CredentialField>) {
    const next = props.fields.map((f, idx) => idx === i ? { ...f, ...patch } : f);
    emit("update:fields", next);
}

function autoField(i: number, label: string) {
    const current = props.fields[i];
    if (current.field && current.field !== slugify(current.label)) return;
    updateField(i, { field: slugify(label) });
}
function slugify(s: string) {
    return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function onDragStart(i: number) { dragIndex.value = i; }
function onDragOver(e: DragEvent, i: number) { e.preventDefault(); overIndex.value = i; }
function onDrop(i: number) {
    if (dragIndex.value === null || dragIndex.value === i) {
        dragIndex.value = null; overIndex.value = null; return;
    }
    const next = [...props.fields];
    const [moved] = next.splice(dragIndex.value, 1);
    next.splice(i, 0, moved);
    emit("update:fields", next);
    dragIndex.value = null; overIndex.value = null;
}
function onDragEnd() { dragIndex.value = null; overIndex.value = null; }

const jsonPreview = computed(() =>
    JSON.stringify(
        props.fields.map(({ placeholder, ...f }) =>
            placeholder ? { ...f, placeholder } : f
        ),
        null, 4,
    )
);

const typeColor: Record<string, string> = {
    string:   "border-sky-500/30 text-sky-600 bg-sky-500/10",
    password: "border-rose-500/30 text-rose-600 bg-rose-500/10",
    number:   "border-amber-500/30 text-amber-600 bg-amber-500/10",
    boolean:  "border-violet-500/30 text-violet-600 bg-violet-500/10",
};
</script>

<template>
    <div class="flex items-stretch w-full">

        <div class="flex-1 min-w-0 flex flex-col gap-3 px-6 py-5 overflow-y-auto">

            <div class="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2.5 text-[11px] text-muted-foreground">
                <RiInformationLine class="size-3.5 shrink-0 mt-px text-muted-foreground/70" />
                <span>
                    Define the credential fields users must fill in when connecting a device with this plugin.
                    These become the <code class="font-mono bg-muted px-1 rounded text-[10px]">credentials.json</code> schema.
                </span>
            </div>

            <div v-if="fields.length" class="flex flex-col gap-2">
                <div
                    v-for="(field, i) in fields"
                    :key="i"
                    class="group relative rounded-lg border bg-card transition-colors"
                    :class="[
                        overIndex === i && dragIndex !== i
                            ? 'border-primary/50 bg-primary/5'
                            : 'border-border hover:border-border/80',
                    ]"
                    draggable="true"
                    @dragstart="onDragStart(i)"
                    @dragover="onDragOver($event, i)"
                    @drop="onDrop(i)"
                    @dragend="onDragEnd"
                >
                    <div class="absolute left-0 inset-y-0 flex items-center px-2 cursor-grab opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground/50 hover:text-muted-foreground">
                        <RiDraggable class="size-3.5" />
                    </div>

                    <div class="pl-7 pr-3 py-3 flex flex-col gap-2.5">

                        <div class="grid grid-cols-[1fr_1fr_auto_auto] gap-2 items-end">
                            <div class="flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Label</label>
                                <Input
                                    :model-value="field.label"
                                    placeholder="e.g. Host"
                                    class="h-7 text-xs"
                                    @update:model-value="
                                        autoField(i, $event as string);
                                        updateField(i, { label: $event as string });
                                    "
                                />
                            </div>

                            <div class="flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Field key</label>
                                <Input
                                    :model-value="field.field"
                                    placeholder="host"
                                    class="h-7 text-xs font-mono"
                                    @update:model-value="updateField(i, { field: $event as string })"
                                />
                            </div>

                            <div class="flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Type</label>
                                <select
                                    :value="field.type"
                                    class="h-7 rounded-md border border-input bg-input/20 dark:bg-input/30 px-2 text-xs outline-none w-28"
                                    @change="updateField(i, { type: ($event.target as HTMLSelectElement).value as CredentialField['type'] })"
                                >
                                    <option value="string">string</option>
                                    <option value="password">password</option>
                                    <option value="number">number</option>
                                    <option value="boolean">boolean</option>
                                </select>
                            </div>

                            <button
                                class="mb-px text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                                @click="removeField(i)"
                            >
                                <RiDeleteBinLine class="size-3.5" />
                            </button>
                        </div>

                        <div class="flex items-center gap-3">
                            <div class="flex-1 flex flex-col gap-1">
                                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                                    Placeholder <span class="normal-case font-normal">(optional)</span>
                                </label>
                                <Input
                                    :model-value="field.placeholder ?? ''"
                                    placeholder="e.g. 192.168.1.100"
                                    class="h-7 text-xs"
                                    @update:model-value="updateField(i, { placeholder: ($event as string) || undefined })"
                                />
                            </div>

                            <div class="flex items-center gap-3 pt-4 shrink-0">
                                <label class="flex items-center gap-1.5 cursor-pointer select-none">
                                    <button
                                        type="button"
                                        class="relative w-7 h-4 rounded-full transition-colors focus:outline-none"
                                        :class="field.required ? 'bg-primary' : 'bg-muted-foreground/30'"
                                        @click="updateField(i, { required: !field.required })"
                                    >
                                        <span
                                            class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
                                            :class="field.required ? 'translate-x-3' : 'translate-x-0'"
                                        />
                                    </button>
                                    <span class="text-[10px] text-muted-foreground">Required</span>
                                </label>

                                <label class="flex items-center gap-1.5 cursor-pointer select-none">
                                    <button
                                        type="button"
                                        class="relative w-7 h-4 rounded-full transition-colors focus:outline-none"
                                        :class="field.secret ? 'bg-primary' : 'bg-muted-foreground/30'"
                                        @click="updateField(i, { secret: !field.secret })"
                                    >
                                        <span
                                            class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform"
                                            :class="field.secret ? 'translate-x-3' : 'translate-x-0'"
                                        />
                                    </button>
                                    <span class="flex items-center gap-1 text-[10px] text-muted-foreground">
                                        <RiLockLine class="size-3" />
                                        Secret
                                    </span>
                                </label>
                            </div>
                        </div>

                        <div class="flex items-center gap-1.5">
                            <span :class="['text-[9px] font-medium px-1.5 py-px rounded-full border font-mono', typeColor[field.type]]">
                                {{ field.type }}
                            </span>
                            <span v-if="field.required" class="text-[9px] font-medium px-1.5 py-px rounded-full border border-emerald-500/30 text-emerald-600 bg-emerald-500/10">
                                required
                            </span>
                            <span v-if="field.secret" class="text-[9px] font-medium px-1.5 py-px rounded-full border border-rose-500/30 text-rose-600 bg-rose-500/10 flex items-center gap-1">
                                <RiLockLine class="size-2.5" /> secret
                            </span>
                            <span v-if="field.field" class="text-[9px] font-mono text-muted-foreground/60 ml-auto">
                                .{{ field.field }}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <div
                v-else
                class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-10 text-center"
            >
                <RiLockLine class="size-6 text-muted-foreground/30 mb-2" />
                <p class="text-xs text-muted-foreground">No credential fields defined yet.</p>
                <p class="text-[11px] text-muted-foreground/60 mt-0.5">Add fields that users must fill in to connect this device.</p>
            </div>

            <Button variant="outline" size="sm" class="gap-1.5 w-fit" @click="addField">
                <RiAddLine class="size-3.5" />
                Add field
            </Button>

            <div class="pt-1">
                <FilePreviewToggle
                    :show="showJson"
                    filename="credentials.json"
                    @update:show="showJson = $event"
                />
            </div>
        </div>

        <FilePreviewPanel
            :show="showJson"
            filename="credentials.json"
            :content="jsonPreview"
            @update:show="showJson = $event"
        />

    </div>
</template>