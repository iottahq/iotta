<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    RiAddLine,
    RiArrowLeftLine,
    RiCloseLine,
    RiDeleteBinLine,
    RiErrorWarningLine,
    RiEyeLine,
    RiEyeOffLine,
    RiLayoutGridLine,
    RiLoader4Line,
} from "@remixicon/vue";

interface FieldEntry {
    key: string;
    value: string;
    secret: boolean;
}

interface PluginTemplate {
    id: string;
    name: string;
    fields: { field: string; type: string; label: string; required?: boolean }[];
}

const props = defineProps<{
    show: boolean;
    saving: boolean;
    error: string | null;
    templates: PluginTemplate[];
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
    create: [name: string, data: Record<string, string>];
}>();

type Step = "form" | "templates";

const step = ref<Step>("form");
const name = ref("");
const fields = ref<FieldEntry[]>([]);
const revealed = ref<Record<number, boolean>>({});

watch(() => props.show, (v) => {
    if (v) {
        step.value = "form";
        name.value = "";
        fields.value = [];
        revealed.value = {};
    }
});

function applyTemplate(template: PluginTemplate) {
    fields.value = template.fields.map((f) => ({
        key: f.field,
        value: "",
        secret: f.type === "secret",
    }));
    step.value = "form";
}

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
            <div v-if="show" class="fixed inset-0 z-[60] flex items-center justify-center" @click.self="close">
                <div class="absolute inset-0 bg-black/50" @click="close" />
                <div class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 max-h-[90vh] flex flex-col">

                    <!-- Header -->
                    <div class="flex items-center justify-between mb-4 shrink-0">
                        <div class="flex items-center gap-2">
                            <button v-if="step === 'templates'" class="text-muted-foreground hover:text-foreground transition-colors" @click="step = 'form'">
                                <RiArrowLeftLine class="size-3.5" />
                            </button>
                            <h2 class="text-sm font-semibold">
                                {{ step === 'templates' ? 'Choose a template' : 'New credential' }}
                            </h2>
                        </div>
                        <Button variant="ghost" size="icon-sm" @click="close">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>

                    <!-- Template picker -->
                    <template v-if="step === 'templates'">
                        <div class="flex flex-col gap-2 overflow-y-auto min-h-0">
                            <p class="text-xs text-muted-foreground mb-1">
                                Select a device plugin to pre-fill the credential fields.
                            </p>
                            <button
                                v-for="t in templates"
                                :key="t.id"
                                class="flex flex-col gap-1 rounded-lg border border-border px-3 py-2.5 text-left hover:border-primary/40 hover:bg-muted/30 transition-colors"
                                @click="applyTemplate(t)"
                            >
                                <span class="text-xs font-medium">{{ t.name }}</span>
                                <span class="text-[10px] text-muted-foreground font-mono">
                                    {{ t.fields.map(f => f.field).join(', ') }}
                                </span>
                            </button>
                            <div v-if="!templates.length" class="flex items-center justify-center py-6 text-xs text-muted-foreground">
                                No device plugins loaded
                            </div>
                        </div>
                    </template>

                    <!-- Credential form -->
                    <template v-else>
                        <div class="flex flex-col gap-4 overflow-y-auto min-h-0">

                            <!-- Name -->
                            <div class="flex flex-col gap-1.5">
                                <label class="text-xs font-medium">Name</label>
                                <Input v-model="name" placeholder="e.g. Bambu Lab A1 – Home" autofocus @keydown.enter="submit" />
                            </div>

                            <!-- Fields -->
                            <div class="flex flex-col gap-2">
                                <div class="flex items-center justify-between">
                                    <label class="text-xs font-medium">Fields</label>
                                    <div class="flex items-center gap-1">
                                        <Button
                                            v-if="templates.length"
                                            variant="ghost"
                                            size="sm"
                                            class="gap-1 h-6 px-1.5 text-muted-foreground"
                                            @click="step = 'templates'"
                                        >
                                            <RiLayoutGridLine class="size-3" />
                                            Use template
                                        </Button>
                                        <Button variant="ghost" size="sm" class="gap-1 h-6 px-1.5 text-muted-foreground" @click="addField">
                                            <RiAddLine class="size-3" />
                                            Add field
                                        </Button>
                                    </div>
                                </div>

                                <div v-if="fields.length === 0" class="flex items-center justify-center rounded-md border border-dashed border-border py-5 text-[11px] text-muted-foreground">
                                    No fields yet — use a template or add manually
                                </div>

                                <div v-for="(field, idx) in fields" :key="idx" class="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/20 px-3 py-2.5">
                                    <div class="flex items-center gap-1.5">
                                        <Input v-model="field.key" placeholder="key" class="font-mono text-[11px] h-6 flex-1" />
                                        <button
                                            type="button"
                                            class="shrink-0 flex items-center gap-1 text-[10px] px-1.5 py-1 rounded border transition-colors"
                                            :class="field.secret ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground'"
                                            @click="toggleSecret(idx)"
                                        >
                                            <RiEyeOffLine class="size-3" />
                                            secret
                                        </button>
                                        <button type="button" class="shrink-0 text-muted-foreground hover:text-destructive transition-colors" @click="removeField(idx)">
                                            <RiDeleteBinLine class="size-3.5" />
                                        </button>
                                    </div>
                                    <div class="relative">
                                        <Input
                                            v-model="field.value"
                                            :type="field.secret && !revealed[idx] ? 'password' : 'text'"
                                            placeholder="value"
                                            class="font-mono text-[11px] h-6"
                                            :class="field.secret ? 'pr-7' : ''"
                                        />
                                        <button v-if="field.secret" type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors" @click="toggleReveal(idx)">
                                            <RiEyeLine v-if="!revealed[idx]" class="size-3" />
                                            <RiEyeOffLine v-else class="size-3" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Error -->
                            <div v-if="error" class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs">
                                <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                                {{ error }}
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="flex gap-2 justify-end mt-4 shrink-0">
                            <Button variant="outline" size="sm" @click="close">Cancel</Button>
                            <Button size="sm" class="gap-1.5" :disabled="saving || !name.trim()" @click="submit">
                                <RiLoader4Line v-if="saving" class="size-3.5 animate-spin" />
                                <RiAddLine v-else class="size-3.5" />
                                Create
                            </Button>
                        </div>
                    </template>

                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>