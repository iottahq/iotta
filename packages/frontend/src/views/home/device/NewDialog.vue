<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Group } from "@/lib/api";
import {
    RiAddLine,
    RiArrowLeftLine,
    RiCheckLine,
    RiCloseLine,
    RiErrorWarningLine,
    RiGroupLine,
    RiLoader4Line,
} from "@remixicon/vue";

const props = defineProps<{
    show: boolean;
    targetGroupId: string | null;
    name: string;
    plugin: string;
    credential: string;
    saving: boolean;
    error: string | null;
    plugins: { id: string; name: string }[];
    credentials: { id: string; name: string }[];
    groups: Group[];
    creatingGroup: boolean;
    createGroupError: string | null;
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
    "update:name": [v: string];
    "update:plugin": [v: string];
    "update:credential": [v: string];
    "update:targetGroupId": [v: string | null];
    create: [];
    "create-group": [name: string];
}>();

const noGroups = computed(() => props.groups.length === 0);
const newGroupName = ref("");

// Reset inline group form whenever dialog opens
watch(
    () => props.show,
    (v) => {
        if (v) newGroupName.value = "";
    },
);

// Once groups go from 0 → 1, auto-select the new group
watch(
    () => props.groups,
    (groups) => {
        if (groups.length === 1 && !props.targetGroupId) {
            emit("update:targetGroupId", groups[0].id);
        }
    },
);

function submitGroup() {
    if (!newGroupName.value.trim()) return;
    emit("create-group", newGroupName.value.trim());
    newGroupName.value = "";
}
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="emit('update:show', false)"
            >
                <div
                    class="absolute inset-0 bg-black/50"
                    @click="emit('update:show', false)"
                />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4"
                >
                    <!-- Header -->
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold">New device</h2>
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            @click="emit('update:show', false)"
                        >
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>

                    <!-- No groups state -->
                    <div v-if="noGroups" class="flex flex-col gap-4">
                        <div class="flex flex-col items-center gap-2 py-3 text-center">
                            <div class="flex items-center justify-center size-10 rounded-full bg-muted">
                                <RiGroupLine class="size-5 text-muted-foreground" />
                            </div>
                            <div>
                                <p class="text-xs font-medium">No groups yet</p>
                                <p class="text-xs text-muted-foreground mt-0.5">
                                    Devices need a group. Create one first.
                                </p>
                            </div>
                        </div>

                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Group name</label>
                            <Input
                                v-model="newGroupName"
                                placeholder="e.g. 3D Printers"
                                autofocus
                                @keydown.enter="submitGroup"
                            />
                        </div>

                        <div
                            v-if="createGroupError"
                            class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                        >
                            <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                            {{ createGroupError }}
                        </div>

                        <div class="flex gap-2 justify-end">
                            <Button
                                variant="outline"
                                size="sm"
                                @click="emit('update:show', false)"
                            >
                                Cancel
                            </Button>
                            <Button
                                size="sm"
                                class="gap-1.5"
                                :disabled="creatingGroup || !newGroupName.trim()"
                                @click="submitGroup"
                            >
                                <RiLoader4Line v-if="creatingGroup" class="size-3.5 animate-spin" />
                                <RiAddLine v-else class="size-3.5" />
                                Create group
                            </Button>
                        </div>
                    </div>

                    <!-- Normal device form -->
                    <div v-else class="flex flex-col gap-3">
                        <!-- Group selector -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Group</label>
                            <select
                                :value="targetGroupId ?? ''"
                                @change="emit('update:targetGroupId', ($event.target as HTMLSelectElement).value || null)"
                                class="bg-input/20 dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/30 h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none"
                            >
                                <option value="" disabled>Select a group…</option>
                                <option
                                    v-for="g in groups"
                                    :key="g.id"
                                    :value="g.id"
                                >
                                    {{ g.name }}
                                </option>
                            </select>
                        </div>

                        <!-- Name -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <Input
                                :model-value="name"
                                placeholder="e.g. Bambu A1 #1"
                                @update:model-value="emit('update:name', $event as string)"
                            />
                        </div>

                        <!-- Plugin -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Plugin</label>
                            <select
                                :value="plugin"
                                @change="emit('update:plugin', ($event.target as HTMLSelectElement).value)"
                                class="bg-input/20 dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/30 h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none"
                            >
                                <option v-for="p in plugins" :key="p.id" :value="p.id">
                                    {{ p.name }}
                                </option>
                                <option v-if="!plugins.length" value="" disabled>
                                    No plugins loaded
                                </option>
                            </select>
                        </div>

                        <!-- Credential -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Credential</label>
                            <select
                                :value="credential"
                                @change="emit('update:credential', ($event.target as HTMLSelectElement).value)"
                                class="bg-input/20 dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/30 h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none"
                            >
                                <option v-for="c in credentials" :key="c.id" :value="c.id">
                                    {{ c.name }}
                                </option>
                                <option v-if="!credentials.length" value="" disabled>
                                    No credentials
                                </option>
                            </select>
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
                        <div class="flex gap-2 justify-end mt-1">
                            <Button
                                variant="outline"
                                size="sm"
                                @click="emit('update:show', false)"
                            >
                                Cancel
                            </Button>
                            <Button
                                size="sm"
                                :disabled="saving || !name.trim() || !plugin || !credential || !targetGroupId"
                                @click="emit('create')"
                                class="gap-1.5"
                            >
                                <RiLoader4Line v-if="saving" class="size-3.5 animate-spin" />
                                <RiCheckLine v-else class="size-3.5" />
                                Create
                            </Button>
                        </div>
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