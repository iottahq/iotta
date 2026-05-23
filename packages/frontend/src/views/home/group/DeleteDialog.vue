<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Group } from "@/lib/api";
import { RiDeleteBinLine, RiLoader4Line, RiErrorWarningLine } from "@remixicon/vue";

const props = defineProps<{
    show: boolean;
    group: Group | null;
    deleting: boolean;
    deviceCount: number;
}>();

const emit = defineEmits<{
    cancel: [];
    confirm: [];
}>();

const nameInput = ref("");
const confirmed = ref(false);

watch(() => props.show, (v) => {
    if (v) {
        nameInput.value = "";
        confirmed.value = false;
    }
});

const nameMatches = computed(() =>
    nameInput.value.trim() === props.group?.name
);

const canDelete = computed(() => nameMatches.value && confirmed.value);
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show && group"
                class="fixed inset-0 z-[60] flex items-center justify-center"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('cancel')" />
                <div class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 flex flex-col gap-4">

                    <!-- Header -->
                    <div>
                        <h2 class="text-sm font-semibold">Delete group</h2>
                        <p class="text-xs text-muted-foreground mt-1">
                            This will permanently delete
                            <span class="font-medium text-foreground">{{ group.name }}</span>
                            <template v-if="deviceCount > 0">
                                and
                                <span class="font-medium text-destructive">
                                    {{ deviceCount }} device{{ deviceCount !== 1 ? "s" : "" }}
                                </span>
                                in this group
                            </template>.
                            This action cannot be undone.
                        </p>
                    </div>

                    <!-- Name confirmation -->
                    <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium">
                            Type <span class="font-mono text-foreground bg-muted px-1 py-0.5 rounded">{{ group.name }}</span> to confirm
                        </label>
                        <Input
                            v-model="nameInput"
                            :placeholder="group.name"
                            :class="nameInput && !nameMatches ? 'border-destructive focus-visible:border-destructive' : ''"
                            autofocus
                        />
                    </div>

                    <!-- Checkbox confirmation -->
                    <label class="flex items-start gap-2.5 cursor-pointer select-none group">
                        <div class="relative mt-0.5 shrink-0">
                            <input
                                type="checkbox"
                                v-model="confirmed"
                                class="peer sr-only"
                            />
                            <div class="w-4 h-4 rounded border border-border bg-background peer-checked:bg-destructive peer-checked:border-destructive transition-colors flex items-center justify-center">
                                <svg v-if="confirmed" class="size-2.5 text-white" viewBox="0 0 10 8" fill="none">
                                    <path d="M1 4L3.5 6.5L9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </div>
                        </div>
                        <span class="text-xs text-muted-foreground leading-relaxed">
                            Yes, I want to delete this group
                            <template v-if="deviceCount > 0">
                                and all <span class="text-destructive font-medium">{{ deviceCount }} device{{ deviceCount !== 1 ? "s" : "" }}</span> in it
                            </template>
                        </span>
                    </label>

                    <!-- Actions -->
                    <div class="flex gap-2 justify-end">
                        <Button variant="outline" size="sm" @click="emit('cancel')">
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            size="sm"
                            class="gap-1.5"
                            :disabled="!canDelete || deleting"
                            @click="emit('confirm')"
                        >
                            <RiLoader4Line v-if="deleting" class="size-3.5 animate-spin" />
                            <RiDeleteBinLine v-else class="size-3.5" />
                            Delete group{{ deviceCount > 0 ? ` & ${deviceCount} device${deviceCount !== 1 ? "s" : ""}` : "" }}
                        </Button>
                    </div>

                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>