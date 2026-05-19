<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Credential } from "@/lib/api";
import {
    RiAddLine,
    RiDeleteBinLine,
    RiCloseLine,
    RiErrorWarningLine,
    RiEyeLine,
    RiEyeOffLine,
    RiLoader4Line,
    RiSave3Line,
} from "@remixicon/vue";

interface FieldEntry {
    originalKey: string | null; // null = newly added, not yet saved
    key: string;
    value: string;
    secret: boolean;
}

const props = defineProps<{
    credential: Credential | null;
    saving: boolean;
    error: string | null;
    usedByDevices: { id: string; name: string; plugin_id: string }[];
    pluginName: (pluginId: string) => string;
}>();

const emit = defineEmits<{
    save: [name: string, data: Record<string, string>];
    close: [];
    delete: [];
}>();

// ── Local state ────────────────────────────────────────────────────────────

const name = ref("");
const fields = ref<FieldEntry[]>([]);
const revealed = ref<Record<number, boolean>>({});

function isSecret(key: string): boolean {
    return /password|secret|access_code|token|key/i.test(key);
}

// Sync local state whenever the dialog opens with a new credential
watch(
    () => props.credential,
    (cred) => {
        if (!cred) return;
        name.value = cred.name;
        fields.value = Object.entries(cred.data).map(([k, v]) => ({
            originalKey: k,
            key: k,
            value: String(v),
            secret: isSecret(k),
        }));
        revealed.value = {};
    },
    { immediate: true },
);

// ── Field management ───────────────────────────────────────────────────────

function addField() {
    fields.value.push({ originalKey: null, key: "", value: "", secret: false });
}

function removeField(idx: number) {
    fields.value.splice(idx, 1);
    delete revealed.value[idx];
}

function toggleSecret(idx: number) {
    fields.value[idx].secret = !fields.value[idx].secret;
}

function toggleReveal(idx: number) {
    revealed.value[idx] = !revealed.value[idx];
}

// ── Submit ─────────────────────────────────────────────────────────────────

function submit() {
    const data: Record<string, string> = {};
    for (const f of fields.value) {
        const k = f.key.trim();
        if (k) data[k] = f.value;
    }
    emit("save", name.value.trim(), data);
}
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="credential"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="emit('close')"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 max-h-[90vh] flex flex-col"
                >
                    
                <!-- Header -->
                <div class="flex items-center justify-between mb-4 shrink-0">
                    <h2 class="text-sm font-semibold">Edit credential</h2>
                    <Button variant="ghost" size="icon-sm" @click="emit('close')">
                        <RiCloseLine class="size-3.5" />
                    </Button>
                </div>
        
                <!-- Scrollable body -->
                <div class="flex flex-col gap-4 overflow-y-auto min-h-0">
                    <!-- Name -->
                    <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium">Name</label>
                        <Input v-model="name" placeholder="Credential name" />
                    </div>
        
                    <!-- Fields -->
                    <div class="flex flex-col gap-2">
                        <div class="flex items-center justify-between">
                            <label class="text-xs font-medium">Fields</label>
                            <Button
                                variant="ghost"
                                size="sm"
                                class="gap-1 h-6 px-1.5 text-muted-foreground"
                                @click="addField"
                            >
                            <RiAddLine class="size-3" />
                                Add field
                            </Button>
                        </div>
            
                        <div
                            v-if="fields.length === 0"
                            class="flex items-center justify-center rounded-md border border-dashed border-border py-5 text-[11px] text-muted-foreground"
                        >
                            No fields — click "Add field" to add one
                        </div>
            
                        <div
                            v-for="(field, idx) in fields"
                            :key="idx"
                            class="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/20 px-3 py-2.5"
                            :class="field.originalKey === null ? 'border-primary/30' : ''"
                        >
                            <!-- Key + controls -->
                            <div class="flex items-center gap-1.5">
                                <Input
                                    v-model="field.key"
                                    placeholder="key"
                                    class="font-mono text-[11px] h-6 flex-1"
                                />
                                <button
                                    type="button"
                                    class="shrink-0 flex items-center gap-1 text-[10px] px-1.5 py-1 rounded border transition-colors"
                                    :class="
                                    field.secret
                                        ? 'border-primary/40 bg-primary/10 text-primary'
                                        : 'border-border text-muted-foreground hover:text-foreground'
                                    "
                                    @click="toggleSecret(idx)"
                                >
                                    <RiEyeOffLine class="size-3" />
                                    secret
                                </button>
                                <button
                                    type="button"
                                    class="shrink-0 text-muted-foreground hover:text-destructive transition-colors"
                                    @click="removeField(idx)"
                                >
                                    <RiDeleteBinLine class="size-3.5" />
                                </button>
                            </div>
            
                            <!-- Value -->
                            <div class="relative">
                                <Input
                                    v-model="field.value"
                                    :type="field.secret && !revealed[idx] ? 'password' : 'text'"
                                    placeholder="value"
                                    class="font-mono text-[11px] h-6"
                                    :class="field.secret ? 'pr-7' : ''"
                                />
                                <button
                                    v-if="field.secret"
                                    type="button"
                                    class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                    @click="toggleReveal(idx)"
                                >
                                    <RiEyeLine v-if="!revealed[idx]" class="size-3" />
                                    <RiEyeOffLine v-else class="size-3" />
                                </button>
                            </div>
                        </div>
                    </div>
        
                    <!-- Used by -->
                    <div v-if="usedByDevices.length > 0" class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium text-muted-foreground"
                            >Used by</label
                        >
                        <div class="flex flex-wrap gap-1.5">
                            <span
                                v-for="dev in usedByDevices"
                                :key="dev.id"
                                class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
                            >
                                {{ dev.name }}
                                <span class="opacity-60">· {{ pluginName(dev.plugin_id) }}</span
                            >
                            </span>
                        </div>
                    </div>
        
                    <!-- Error -->
                    <div
                        v-if="error"
                        class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                    >
                    <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        {{ error }}
                    </div>
                </div>
        
                <!-- Footer -->
                <div class="flex gap-2 justify-between mt-4 shrink-0">
                    <Button
                        variant="destructive"
                        size="sm"
                        class="gap-1.5"
                        @click="emit('delete')"
                    >
                        <RiDeleteBinLine class="size-3.5" />
                        Delete
                    </Button>
                    <Button
                        size="sm"
                        class="gap-1.5"
                        :disabled="saving || !name.trim()"
                        @click="submit"
                    >
                        <RiLoader4Line v-if="saving" class="size-3.5 animate-spin" />
                        <RiSave3Line v-else class="size-3.5" />
                        Save
                    </Button>
                </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
