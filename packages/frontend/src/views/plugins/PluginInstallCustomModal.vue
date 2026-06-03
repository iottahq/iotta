<script setup lang="ts">
import { ref, watch } from "vue";
import { api, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    RiCloseLine,
    RiGitRepositoryLine,
    RiUploadLine,
    RiDownloadLine,
    RiLoader4Line,
    RiErrorWarningLine,
    RiCheckLine,
    RiFileLine,
} from "@remixicon/vue";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{
    "update:show": [value: boolean];
    installed: [];
}>();

type Tab = "git" | "zip";

const activeTab = ref<Tab>("git");

// Git tab
const gitUrl = ref("");

// Zip tab
const zipFile = ref<File | null>(null);
const dropActive = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

// Shared state
const installing = ref(false);
const error = ref<string | null>(null);
const success = ref<{ name: string; version: string } | null>(null);

function reset() {
    gitUrl.value = "";
    zipFile.value = null;
    error.value = null;
    success.value = null;
    installing.value = false;
    activeTab.value = "git";
}

watch(() => props.show, (val) => { if (val) reset(); });

// Zip drag & drop
function onDrop(e: DragEvent) {
    dropActive.value = false;
    const f = e.dataTransfer?.files[0];
    if (f?.name.endsWith(".zip")) {
        zipFile.value = f;
        error.value = null;
    } else {
        error.value = "Only .zip files are supported";
    }
}

function onFileChange(e: Event) {
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f) {
        zipFile.value = f;
        error.value = null;
    }
}

async function install() {
    error.value = null;
    success.value = null;
    installing.value = true;
    try {
        let result;
        if (activeTab.value === "git") {
            if (!gitUrl.value.trim()) {
                error.value = "Please enter a git repository URL";
                return;
            }
            result = await api.plugins.registry.installGit(gitUrl.value.trim());
        } else {
            if (!zipFile.value) {
                error.value = "Please select a zip file";
                return;
            }
            result = await api.plugins.registry.installZip(zipFile.value);
        }
        success.value = { name: result.name, version: result.version };
        emit("installed");
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Installation failed";
    } finally {
        installing.value = false;
    }
}
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="show" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
                <div class="absolute inset-0 bg-black/50" @click="emit('update:show', false)" />

                <div class="relative z-10 flex flex-col w-full max-w-md rounded-xl border border-border bg-card shadow-2xl overflow-hidden">

                    <!-- Header -->
                    <div class="flex items-center gap-3 px-5 py-4 border-b border-border shrink-0">
                        <RiUploadLine class="size-4 text-muted-foreground shrink-0" />
                        <div class="flex-1 min-w-0">
                            <h2 class="text-sm font-semibold">Install from source</h2>
                            <p class="text-xs text-muted-foreground">Git repository or zip archive</p>
                        </div>
                        <button class="text-muted-foreground hover:text-foreground transition-colors" @click="emit('update:show', false)">
                            <RiCloseLine class="size-4" />
                        </button>
                    </div>

                    <!-- Tabs -->
                    <div class="flex items-center gap-px bg-muted mx-5 mt-4 rounded-md p-0.5 w-fit">
                        <button
                            v-for="tab in ['git', 'zip'] as Tab[]"
                            :key="tab"
                            @click="activeTab = tab; error = null; success = null;"
                            :class="[
                                'flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-colors',
                                activeTab === tab
                                    ? 'bg-background text-foreground shadow-xs'
                                    : 'text-muted-foreground hover:text-foreground',
                            ]"
                        >
                            <RiGitRepositoryLine v-if="tab === 'git'" class="size-3.5" />
                            <RiFileLine v-else class="size-3.5" />
                            {{ tab === 'git' ? 'Git URL' : 'ZIP Upload' }}
                        </button>
                    </div>

                    <!-- Body -->
                    <div class="px-5 py-4 flex flex-col gap-4">

                        <!-- Git URL input -->
                        <div v-if="activeTab === 'git'" class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium text-foreground">Repository URL</label>
                            <Input
                                v-model="gitUrl"
                                placeholder="https://github.com/you/my-plugin.git"
                                class="text-xs font-mono"
                                @keydown.enter="install"
                            />
                            <p class="text-[11px] text-muted-foreground">
                                The repository root must contain a <span class="font-mono">plugin.yaml</span> with an <span class="font-mono">id</span> field. The plugin type is detected automatically.
                            </p>
                        </div>

                        <!-- ZIP upload -->
                        <div v-else class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium text-foreground">Zip archive</label>
                            <div
                                class="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed transition-colors cursor-pointer px-4 py-6 text-center"
                                :class="dropActive ? 'border-primary bg-primary/5' : 'border-border hover:border-foreground/20'"
                                @dragover.prevent="dropActive = true"
                                @dragleave="dropActive = false"
                                @drop.prevent="onDrop"
                                @click="fileInput?.click()"
                            >
                                <RiFileLine v-if="!zipFile" class="size-6 text-muted-foreground/40" />
                                <RiCheckLine v-else class="size-6 text-emerald-500" />
                                <p class="text-xs text-muted-foreground">
                                    <span v-if="zipFile" class="font-medium text-foreground">{{ zipFile.name }}</span>
                                    <span v-else>Drop a <span class="font-mono">.zip</span> here or <span class="underline">browse</span></span>
                                </p>
                                <p v-if="zipFile" class="text-[11px] text-muted-foreground">
                                    {{ (zipFile.size / 1024).toFixed(0) }} KB — click to replace
                                </p>
                            </div>
                            <input ref="fileInput" type="file" accept=".zip" class="hidden" @change="onFileChange" />
                        </div>

                        <!-- Error -->
                        <div v-if="error" class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs">
                            <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                            {{ error }}
                        </div>

                        <!-- Success -->
                        <div v-if="success" class="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 px-3 py-2 text-xs">
                            <RiCheckLine class="size-3.5 shrink-0 mt-px" />
                            <span>
                                <span class="font-medium">{{ success.name }}</span>
                                <span v-if="success.version"> v{{ success.version }}</span>
                                installed successfully.
                            </span>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div class="flex items-center justify-end gap-2 px-5 py-3 border-t border-border shrink-0">
                        <Button variant="outline" size="sm" @click="emit('update:show', false)">Cancel</Button>
                        <Button size="sm" class="gap-1.5" :disabled="installing" @click="install">
                            <RiLoader4Line v-if="installing" class="size-3.5 animate-spin" />
                            <RiDownloadLine v-else class="size-3.5" />
                            {{ installing ? 'Installing…' : 'Install' }}
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
</style>
