<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { RiCloseLine, RiLoader4Line, RiCheckLine, RiCodeLine } from "@remixicon/vue";

const props = defineProps<{
    name: string;
    id: string;
    idManual: boolean;
    version: string;
    status: "alpha" | "beta" | "stable";
    description: string;
    authorName: string;
    authorOrg: string;
    authorUrl: string;
    tagInput: string;
    tags: string[];
    minIotta: string;
    availableProtocols: { id: string; name: string }[];
    selectedProtocols: string[];
    loadingProtocols: boolean;
}>();

const emit = defineEmits<{
    "update:yamlOpen":          [v: boolean];
    "update:name":              [v: string];
    "update:id":                [v: string];
    "update:idManual":          [v: boolean];
    "update:version":           [v: string];
    "update:status":            [v: "alpha" | "beta" | "stable"];
    "update:description":       [v: string];
    "update:authorName":        [v: string];
    "update:authorOrg":         [v: string];
    "update:authorUrl":         [v: string];
    "update:tagInput":          [v: string];
    "update:tags":              [v: string[]];
    "update:minIotta":          [v: string];
    "update:selectedProtocols": [v: string[]];
}>();

const showYaml = ref(false);
watch(showYaml, (v) => emit("update:yamlOpen", v));

watch(() => props.name, (val) => {
    if (props.idManual) return;
    emit("update:id", val
        .toLowerCase().trim()
        .replace(/[^a-z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, ""),
    );
});

function addTag() {
    const t = props.tagInput.trim().toLowerCase();
    if (t && !props.tags.includes(t)) emit("update:tags", [...props.tags, t]);
    emit("update:tagInput", "");
}
function removeTag(t: string) {
    emit("update:tags", props.tags.filter((x) => x !== t));
}
function onTagKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addTag(); }
}
function toggleProtocol(protocolId: string) {
    const next = props.selectedProtocols.includes(protocolId)
        ? props.selectedProtocols.filter((p) => p !== protocolId)
        : [...props.selectedProtocols, protocolId];
    emit("update:selectedProtocols", next);
}

const yamlPreview = computed(() => toYamlString(buildPluginYaml()));

function buildPluginYaml(): Record<string, unknown> {
    const yaml: Record<string, unknown> = {
        id: props.id, name: props.name, version: props.version,
        status: props.status, scope: "community",
    };
    if (props.description.trim()) yaml.description = props.description.trim();
    const author: Record<string, string> = {};
    if (props.authorName.trim()) author.name         = props.authorName.trim();
    if (props.authorOrg.trim())  author.organisation = props.authorOrg.trim();
    if (props.authorUrl.trim())  author.url          = props.authorUrl.trim();
    if (Object.keys(author).length) yaml.author = author;
    if (props.tags.length) yaml.tags = [...props.tags];
    yaml.dependencies = { protocols: [...props.selectedProtocols] };
    if (props.minIotta.trim()) yaml.min_iotta_version = props.minIotta.trim();
    return yaml;
}

function toYamlString(obj: unknown, indent = 0): string {
    const pad = "  ".repeat(indent);
    if (obj === null || obj === undefined) return "null";
    if (typeof obj === "boolean") return obj ? "true" : "false";
    if (typeof obj === "number")  return String(obj);
    if (typeof obj === "string") {
        if (obj.includes("\n")) return `|\n${obj.split("\n").map(l => `${pad}  ${l}`).join("\n")}`;
        if (/[:{}\[\],&*?|<>=!%@`#'"\\]/.test(obj) || obj === "") return JSON.stringify(obj);
        return obj;
    }
    if (Array.isArray(obj)) {
        if (!obj.length) return "[]";
        return obj.map((item) => `\n${pad}- ${toYamlString(item, indent + 1)}`).join("");
    }
    if (typeof obj === "object") {
        const entries = Object.entries(obj as Record<string, unknown>).filter(([, v]) => v !== undefined);
        if (!entries.length) return "{}";
        return entries.map(([k, v]) => {
            if (typeof v === "object" && v !== null && !Array.isArray(v)) {
                return `\n${pad}${k}:\n${pad}  ${toYamlString(v, indent + 1).trimStart().replace(/\n/g, `\n${pad}  `)}`;
            }
            return `\n${pad}${k}: ${toYamlString(v, indent)}`;
        }).join("").trimStart();
    }
    return String(obj);
}
</script>

<template>
    <div class="flex items-stretch w-full">

        <div class="flex-1 min-w-0 flex flex-col gap-4 px-6 py-5">

            <div class="grid grid-cols-2 gap-3">
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-medium">Name <span class="text-destructive">*</span></label>
                    <Input :model-value="name" placeholder="e.g. Shelly Plug S" autofocus
                        @update:model-value="emit('update:name', $event as string)" />
                </div>
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-medium flex items-center gap-1.5">
                        Plugin ID <span class="text-destructive">*</span>
                        <span class="text-[10px] font-normal text-muted-foreground">(auto-generated)</span>
                    </label>
                    <Input :model-value="id" placeholder="shelly-plug-s" class="font-mono"
                        @update:model-value="emit('update:id', $event as string)"
                        @input="emit('update:idManual', true)" />
                </div>
            </div>

            <!-- Version + Status + Min iotta -->
            <div class="grid grid-cols-3 gap-3">
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-medium">Version <span class="text-destructive">*</span></label>
                    <Input :model-value="version" placeholder="1.0.0" class="font-mono"
                        @update:model-value="emit('update:version', $event as string)" />
                </div>
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-medium">Status</label>
                    <select :value="status"
                        class="bg-input/20 dark:bg-input/30 border-input h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none"
                        @change="emit('update:status', ($event.target as HTMLSelectElement).value as 'alpha' | 'beta' | 'stable')">
                        <option value="alpha">alpha</option>
                        <option value="beta">beta</option>
                        <option value="stable">stable</option>
                    </select>
                </div>
                <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-medium">Min iotta version</label>
                    <Input :model-value="minIotta" placeholder="0.1.0" class="font-mono"
                        @update:model-value="emit('update:minIotta', $event as string)" />
                </div>
            </div>

            <!-- Description -->
            <div class="flex flex-col gap-1.5">
                <label class="text-xs font-medium">Description</label>
                <textarea :value="description" rows="3"
                    placeholder="Short description of what this plugin does and which device it supports."
                    class="w-full rounded-md border border-border bg-input/20 dark:bg-input/30 px-2.5 py-2 text-xs text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors placeholder:text-muted-foreground"
                    @input="emit('update:description', ($event.target as HTMLTextAreaElement).value)" />
            </div>

            <!-- Author -->
            <div class="flex flex-col gap-1.5">
                <label class="text-xs font-medium">Author</label>
                <div class="grid grid-cols-3 gap-2">
                    <Input :model-value="authorName" placeholder="Name"
                        @update:model-value="emit('update:authorName', $event as string)" />
                    <Input :model-value="authorOrg" placeholder="Organisation"
                        @update:model-value="emit('update:authorOrg', $event as string)" />
                    <Input :model-value="authorUrl" placeholder="https://…"
                        @update:model-value="emit('update:authorUrl', $event as string)" />
                </div>
            </div>

            <!-- Tags -->
            <div class="flex flex-col gap-1.5">
                <label class="text-xs font-medium">Tags</label>
                <div class="flex flex-wrap gap-1.5 min-h-[28px] rounded-md border border-border bg-input/20 dark:bg-input/30 px-2 py-1.5 focus-within:border-ring focus-within:ring-1 focus-within:ring-ring/30 transition-colors">
                    <span v-for="tag in tags" :key="tag"
                        class="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-foreground">
                        {{ tag }}
                        <button type="button" class="text-muted-foreground hover:text-destructive transition-colors" @click="removeTag(tag)">
                            <RiCloseLine class="size-2.5" />
                        </button>
                    </span>
                    <input :value="tagInput" placeholder="Add tag…"
                        class="flex-1 min-w-[80px] bg-transparent text-xs outline-none placeholder:text-muted-foreground"
                        @input="emit('update:tagInput', ($event.target as HTMLInputElement).value)"
                        @keydown="onTagKeydown" @blur="addTag" />
                </div>
                <p class="text-[10px] text-muted-foreground">Press Enter or comma to add a tag.</p>
            </div>

            <!-- Protocol dependencies -->
            <div class="flex flex-col gap-1.5">
                <label class="text-xs font-medium">Protocol dependencies</label>
                <div v-if="loadingProtocols" class="flex items-center gap-2 text-xs text-muted-foreground py-2">
                    <RiLoader4Line class="size-3.5 animate-spin" /> Loading protocols…
                </div>
                <div v-else-if="availableProtocols.length === 0" class="text-xs text-muted-foreground py-2">
                    No protocol plugins loaded.
                </div>
                <div v-else class="flex flex-wrap gap-1.5">
                    <button v-for="proto in availableProtocols" :key="proto.id" type="button"
                        class="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-md border transition-colors font-mono"
                        :class="selectedProtocols.includes(proto.id)
                            ? 'border-primary/50 bg-primary/10 text-primary'
                            : 'border-border text-muted-foreground hover:text-foreground'"
                        @click="toggleProtocol(proto.id)">
                        <RiCheckLine v-if="selectedProtocols.includes(proto.id)" class="size-3" />
                        {{ proto.id }}
                    </button>
                </div>
            </div>

            <!-- View YAML toggle -->
            <div class="pt-1">
                <Button variant="ghost" size="sm" class="gap-1.5 -ml-2"
                    :class="showYaml ? 'text-primary' : 'text-muted-foreground'"
                    @click="showYaml = !showYaml">
                    <RiCodeLine class="size-3.5" />
                    {{ showYaml ? "Hide YAML" : "View YAML" }}
                </Button>
            </div>

        </div>

        <Transition name="slide-right">
            <div v-if="showYaml"
                class="flex-1 min-w-0 self-stretch border-l border-border bg-muted/20 flex flex-col overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2.5 border-b border-border shrink-0">
                    <span class="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">plugin.yaml</span>
                    <button class="text-muted-foreground hover:text-foreground transition-colors" @click="showYaml = false">
                        <RiCloseLine class="size-3.5" />
                    </button>
                </div>
                <pre class="flex-1 overflow-y-auto overflow-x-auto px-4 py-3 font-mono text-[10px] text-foreground whitespace-pre leading-relaxed">{{ yamlPreview }}</pre>
            </div>
        </Transition>

    </div>
</template>

<style scoped>
.slide-right-enter-active,
.slide-right-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.slide-right-enter-from,
.slide-right-leave-to { opacity: 0; transform: translateX(8px); }
.slide-right-enter-to,
.slide-right-leave-from { opacity: 1; transform: translateX(0); }
</style>