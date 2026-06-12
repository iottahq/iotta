<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
    InputGroup,
    InputGroupAddon,
    InputGroupButton,
    InputGroupInput,
} from "@/components/ui/input-group";
import type { Group } from "@/lib/api";
import {
    RiCloseLine,
    RiDeleteBinLine,
    RiErrorWarningLine,
    RiLoader4Line,
    RiSave3Line,
    RiShieldLine,
} from "@remixicon/vue";

defineProps<{
    group: Group | null;
    name: string;
    savingName: boolean;
    error: string | null;
}>();

const emit = defineEmits<{
    "update:name": [v: string];
    "save-name": [];
    "manage-tokens": [];
    close: [];
    delete: [];
}>();
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="group"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="emit('close')"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
                <div class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold">Edit group</h2>
                        <Button variant="ghost" size="icon-sm" @click="emit('close')">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>

                    <div class="flex flex-col gap-4">
                        <!-- Name -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <InputGroup>
                                <InputGroupInput
                                    :model-value="name"
                                    @update:model-value="emit('update:name', $event as string)"
                                    @keydown.enter="emit('save-name')"
                                />
                                <InputGroupAddon align="inline-end">
                                    <InputGroupButton
                                        size="icon-sm"
                                        :disabled="savingName || !name.trim() || name === group.name"
                                        @click="emit('save-name')"
                                    >
                                        <RiLoader4Line v-if="savingName" class="size-3.5 animate-spin" />
                                        <RiSave3Line v-else class="size-3.5" />
                                    </InputGroupButton>
                                </InputGroupAddon>
                            </InputGroup>
                        </div>

                        <!-- Access Tokens -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Access Tokens</label>
                            <Button variant="outline" size="sm" class="gap-1.5 justify-start" @click="emit('manage-tokens')">
                                <RiShieldLine class="size-3.5" />
                                Manage tokens
                            </Button>
                        </div>

                        <!-- Error -->
                        <div
                            v-if="error"
                            class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                        >
                            <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                            {{ error }}
                        </div>

                        <!-- Actions -->
                        <div class="flex gap-2 justify-end">
                            <Button variant="destructive" size="sm" class="gap-1.5" @click="emit('delete')">
                                <RiDeleteBinLine class="size-3.5" />
                                Delete
                            </Button>
                        </div>
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
