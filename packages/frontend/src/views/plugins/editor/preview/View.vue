<script setup lang="ts">
import { ref, computed } from "vue";
import { Button } from "@/components/ui/button";
import {
    RiUploadLine,
    RiDeleteBinLine,
    RiInformationLine,
    RiImageLine,
    RiCheckLine,
} from "@remixicon/vue";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface IconAsset {
    /** Original filename */
    filename: string;
    /** base64 data URL for preview */
    dataUrl: string;
    /** raw base64 string (no prefix) for upload */
    base64: string;
    /** mime type */
    mimeType: string;
}

// ── Props / Emits ─────────────────────────────────────────────────────────────

const props = defineProps<{
    icon: IconAsset | null;
    /** Plugin ID – used to show the existing asset URL when editing */
    pluginId?: string | null;
}>();

const emit = defineEmits<{
    "update:icon": [v: IconAsset | null];
}>();

// ── State ─────────────────────────────────────────────────────────────────────

const dragOver   = ref(false);
const fileInput  = ref<HTMLInputElement | null>(null);
const sizeError  = ref<string | null>(null);

const MAX_SIZE_BYTES = 512 * 1024; // 512 KB

// Existing icon URL when editing a saved plugin
const existingIconUrl = computed(() =>
    props.pluginId
        ? `http://localhost:8000/plugins/devices/${props.pluginId}/assets/icon`
        : null
);

// What to show in the preview: new upload takes priority, then existing
const previewUrl = computed(() => {
    if (props.icon) return props.icon.dataUrl;
    if (existingIconUrl.value) return existingIconUrl.value;
    return null;
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function triggerPicker() {
    fileInput.value?.click();
}

async function handleFile(file: File) {
    sizeError.value = null;

    if (!file.type.match(/^image\/(png|jpeg|svg\+xml|webp)$/)) {
        sizeError.value = "Only PNG, JPEG, SVG or WebP files are supported.";
        return;
    }
    if (file.size > MAX_SIZE_BYTES) {
        sizeError.value = `File too large (${(file.size / 1024).toFixed(0)} KB). Max 512 KB.`;
        return;
    }

    const reader = new FileReader();
    reader.onload = () => {
        const dataUrl = reader.result as string;
        const base64  = dataUrl.split(",")[1];
        emit("update:icon", {
            filename: file.name,
            dataUrl,
            base64,
            mimeType: file.type,
        });
    };
    reader.readAsDataURL(file);
}

function onFileChange(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) handleFile(file);
}

function onDrop(e: DragEvent) {
    e.preventDefault();
    dragOver.value = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
}

function remove() {
    emit("update:icon", null);
    sizeError.value = null;
    if (fileInput.value) fileInput.value.value = "";
}
</script>

<template>
    <div class="flex-1 min-w-0 flex flex-col gap-5 px-6 py-5 overflow-y-auto">

        <!-- Info banner -->
        <div class="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2.5 text-[11px] text-muted-foreground">
            <RiInformationLine class="size-3.5 shrink-0 mt-px text-muted-foreground/70" />
            <span>
                The plugin icon is shown in the device list, device cards, and the plugin library.
                Use a square image, preferably SVG or PNG with a transparent background.
                Recommended size: <strong class="text-foreground font-medium">128 × 128 px</strong>. Max 512 KB.
            </span>
        </div>

        <div class="flex gap-6 items-start">

            <!-- Drop zone / preview -->
            <div class="flex flex-col gap-3 items-center shrink-0">

                <!-- Icon preview box -->
                <div
                    class="relative w-32 h-32 rounded-xl border-2 transition-colors flex items-center justify-center overflow-hidden cursor-pointer"
                    :class="[
                        dragOver
                            ? 'border-primary bg-primary/5'
                            : previewUrl
                                ? 'border-border hover:border-primary/40'
                                : 'border-dashed border-border hover:border-primary/40 bg-muted/20',
                    ]"
                    @click="triggerPicker"
                    @dragover.prevent="dragOver = true"
                    @dragleave="dragOver = false"
                    @drop="onDrop"
                >
                    <!-- Existing / new icon -->
                    <img
                        v-if="previewUrl"
                        :src="previewUrl"
                        alt="Plugin icon"
                        class="w-full h-full object-contain p-2"
                    />

                    <!-- Empty state -->
                    <div v-else class="flex flex-col items-center gap-1.5 text-muted-foreground/50 select-none">
                        <RiImageLine class="size-8" />
                        <span class="text-[10px]">Drop or click</span>
                    </div>

                    <!-- Drag overlay -->
                    <div
                        v-if="dragOver"
                        class="absolute inset-0 flex items-center justify-center bg-primary/10 rounded-xl"
                    >
                        <RiUploadLine class="size-6 text-primary" />
                    </div>
                </div>

                <!-- Action buttons -->
                <div class="flex gap-1.5">
                    <Button variant="outline" size="sm" class="gap-1.5" @click="triggerPicker">
                        <RiUploadLine class="size-3.5" />
                        {{ previewUrl ? "Replace" : "Upload" }}
                    </Button>
                    <Button
                        v-if="icon"
                        variant="ghost"
                        size="icon"
                        class="text-muted-foreground hover:text-destructive"
                        @click="remove"
                    >
                        <RiDeleteBinLine class="size-3.5" />
                    </Button>
                </div>

                <!-- Hidden file input -->
                <input
                    ref="fileInput"
                    type="file"
                    accept="image/png,image/jpeg,image/svg+xml,image/webp"
                    class="sr-only"
                    @change="onFileChange"
                />
            </div>

            <!-- Metadata + size previews -->
            <div class="flex flex-col gap-4 flex-1 min-w-0">

                <!-- File info -->
                <div v-if="icon" class="flex flex-col gap-1">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">Uploaded</p>
                    <div class="flex items-center gap-2 rounded-md border border-border bg-muted/20 px-3 py-2">
                        <RiCheckLine class="size-3.5 text-emerald-500 shrink-0" />
                        <div class="flex-1 min-w-0">
                            <p class="text-xs font-medium text-foreground truncate">{{ icon.filename }}</p>
                            <p class="text-[10px] text-muted-foreground font-mono">{{ icon.mimeType }}</p>
                        </div>
                    </div>
                </div>

                <div v-else-if="pluginId && !icon" class="flex flex-col gap-1">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">Current icon</p>
                    <p class="text-[11px] text-muted-foreground">
                        Saved on disk. Upload a new file to replace it.
                    </p>
                </div>

                <!-- Size previews -->
                <div class="flex flex-col gap-2">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">Size previews</p>
                    <div class="flex items-end gap-4">

                        <!-- 32px – sidebar -->
                        <div class="flex flex-col items-center gap-1.5">
                            <div class="w-8 h-8 rounded-md border border-border bg-muted/30 flex items-center justify-center overflow-hidden">
                                <img v-if="previewUrl" :src="previewUrl" class="w-full h-full object-contain p-0.5" />
                                <RiImageLine v-else class="size-4 text-muted-foreground/30" />
                            </div>
                            <span class="text-[9px] text-muted-foreground">32 px</span>
                            <span class="text-[9px] text-muted-foreground/50">Sidebar</span>
                        </div>

                        <!-- 48px – device card grid -->
                        <div class="flex flex-col items-center gap-1.5">
                            <div class="w-12 h-12 rounded-lg border border-border bg-muted/30 flex items-center justify-center overflow-hidden">
                                <img v-if="previewUrl" :src="previewUrl" class="w-full h-full object-contain p-1" />
                                <RiImageLine v-else class="size-5 text-muted-foreground/30" />
                            </div>
                            <span class="text-[9px] text-muted-foreground">48 px</span>
                            <span class="text-[9px] text-muted-foreground/50">Device card</span>
                        </div>

                        <!-- 64px – plugin library -->
                        <div class="flex flex-col items-center gap-1.5">
                            <div class="w-16 h-16 rounded-xl border border-border bg-muted/30 flex items-center justify-center overflow-hidden">
                                <img v-if="previewUrl" :src="previewUrl" class="w-full h-full object-contain p-1.5" />
                                <RiImageLine v-else class="size-6 text-muted-foreground/30" />
                            </div>
                            <span class="text-[9px] text-muted-foreground">64 px</span>
                            <span class="text-[9px] text-muted-foreground/50">Library</span>
                        </div>

                        <!-- 128px – detail page -->
                        <div class="flex flex-col items-center gap-1.5">
                            <div class="w-32 h-32 rounded-2xl border border-border bg-muted/30 flex items-center justify-center overflow-hidden">
                                <img v-if="previewUrl" :src="previewUrl" class="w-full h-full object-contain p-2" />
                                <RiImageLine v-else class="size-10 text-muted-foreground/30" />
                            </div>
                            <span class="text-[9px] text-muted-foreground">128 px</span>
                            <span class="text-[9px] text-muted-foreground/50">Full size</span>
                        </div>

                    </div>
                </div>

                <!-- Error -->
                <div
                    v-if="sizeError"
                    class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                >
                    {{ sizeError }}
                </div>

                <!-- Guidelines -->
                <div class="flex flex-col gap-1.5 pt-1">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">Guidelines</p>
                    <ul class="flex flex-col gap-1 text-[11px] text-muted-foreground">
                        <li class="flex items-center gap-1.5"><span class="size-1 rounded-full bg-muted-foreground/40 shrink-0" /> Square aspect ratio (1:1)</li>
                        <li class="flex items-center gap-1.5"><span class="size-1 rounded-full bg-muted-foreground/40 shrink-0" /> SVG preferred for crisp scaling, PNG as fallback</li>
                        <li class="flex items-center gap-1.5"><span class="size-1 rounded-full bg-muted-foreground/40 shrink-0" /> Transparent background recommended</li>
                        <li class="flex items-center gap-1.5"><span class="size-1 rounded-full bg-muted-foreground/40 shrink-0" /> Works on both light and dark backgrounds</li>
                        <li class="flex items-center gap-1.5"><span class="size-1 rounded-full bg-muted-foreground/40 shrink-0" /> Saved as <code class="font-mono bg-muted px-1 rounded text-[10px]">icon.svg</code> / <code class="font-mono bg-muted px-1 rounded text-[10px]">icon.png</code> in the plugin directory</li>
                    </ul>
                </div>

            </div>
        </div>
    </div>
</template>