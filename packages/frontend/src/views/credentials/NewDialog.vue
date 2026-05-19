<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    RiAddLine,
    RiCloseLine,
    RiDeleteBinLine,
    RiErrorWarningLine,
    RiEyeLine,
    RiEyeOffLine,
    RiLoader4Line,
} from "@remixicon/vue";

interface FieldEntry {
    key: string;
    value: string;
    secret: boolean;
}

const props = defineProps<{
    show: boolean;
    saving: boolean;
    error: string | null;
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
    create: [name: string, data: Record<string, string>];
}>();

// ── Local state ────────────────────────────────────────────────────────────

const name = ref("");
const fields = ref<FieldEntry[]>([]);
const revealed = ref<Record<number, boolean>>({});

watch(
    () => props.show,
    (v) => {
        if (v) {
            name.value = "";
            fields.value = [];
            revealed.value = {};
        }
    },
);

// ── Field management ───────────────────────────────────────────────────────

function addField() {
    fields.value.push({ key: "", value: "", secret: false });
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
    if (!name.value.trim()) return;
    const data: Record<string, string> = {};
    for (const f of fields.value) {
        if (f.key.trim()) data[f.key.trim()] = f.value;
    }
    emit("create", name.value.trim(), data);
}

function close() {
    emit("update:show", false);
}
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="close"
            >
                <div class="absolute inset-0 bg-black/50" @click="close" />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 max-h-[90vh] flex flex-col"
                >
                    <!-- Header -->
                    <div class="flex items-center justify-between mb-4 shrink-0">
                        <h2 class="text-sm font-semibold">New credential</h2>
                        <Button variant="ghost" size="icon-sm" @click="close">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>
            
                    <!-- Scrollable body -->
                    <div class="flex flex-col gap-4 overflow-y-auto min-h-0">
                        <!-- Name -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <Input
                                v-model="name"
                                placeholder="e.g. Bambu Lab A1 – Home"
                                autofocus
                                @keydown.enter="submit"
                            />
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
                                No fields yet — click "Add field" to start
                            </div>
                
                            <div
                                v-for="(field, idx) in fields"
                                :key="idx"
                                class="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/20 px-3 py-2.5"
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
                    <div class="flex gap-2 justify-end mt-4 shrink-0">
                        <Button variant="outline" size="sm" @click="close"> Cancel </Button>
                        <Button
                            size="sm"
                            class="gap-1.5"
                            :disabled="saving || !name.trim()"
                            @click="submit"
                        >
                            <RiLoader4Line v-if="saving" class="size-3.5 animate-spin" />
                            <RiAddLine v-else class="size-3.5" />
                            Create
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
