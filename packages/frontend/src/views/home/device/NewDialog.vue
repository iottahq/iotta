<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Group } from "@/lib/api";
import {
    RiCheckLine,
    RiCloseLine,
    RiErrorWarningLine,
    RiLoader4Line,
} from "@remixicon/vue";

defineProps<{
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
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
    "update:name": [v: string];
    "update:plugin": [v: string];
    "update:credential": [v: string];
    create: [];
}>();
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
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h2 class="text-sm font-semibold">New device</h2>
                            <p class="text-xs text-muted-foreground mt-0.5">
                                {{
                                    targetGroupId
                                        ? `Group: ${groups.find((g) => g.id === targetGroupId)?.name ?? "—"}`
                                        : "No group"
                                }}
                            </p>
                        </div>
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            @click="emit('update:show', false)"
                        >
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>
                    <div class="flex flex-col gap-3">
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <Input
                                :model-value="name"
                                placeholder="e.g. Bambu A1 #1"
                                @update:model-value="
                                    emit('update:name', $event as string)
                                "
                            />
                        </div>
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Plugin</label>
                            <select
                                :value="plugin"
                                @change="
                                    emit(
                                        'update:plugin',
                                        ($event.target as HTMLSelectElement)
                                            .value,
                                    )
                                "
                                class="bg-input/20 dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/30 h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none"
                            >
                                <option
                                    v-for="p in plugins"
                                    :key="p.id"
                                    :value="p.id"
                                >
                                    {{ p.name }}
                                </option>
                                <option
                                    v-if="!plugins.length"
                                    value=""
                                    disabled
                                >
                                    No plugins loaded
                                </option>
                            </select>
                        </div>
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium"
                                >Credential</label
                            >
                            <select
                                :value="credential"
                                @change="
                                    emit(
                                        'update:credential',
                                        ($event.target as HTMLSelectElement)
                                            .value,
                                    )
                                "
                                class="bg-input/20 dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/30 h-7 rounded-md border px-2 py-0.5 text-xs w-full outline-none"
                            >
                                <option
                                    v-for="c in credentials"
                                    :key="c.id"
                                    :value="c.id"
                                >
                                    {{ c.name }}
                                </option>
                                <option
                                    v-if="!credentials.length"
                                    value=""
                                    disabled
                                >
                                    No credentials
                                </option>
                            </select>
                        </div>
                        <div
                            v-if="error"
                            class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                        >
                            <RiErrorWarningLine
                                class="size-3.5 shrink-0 mt-px"
                            />
                            {{ error }}
                        </div>
                        <div class="flex gap-2 justify-end mt-1">
                            <Button
                                variant="outline"
                                size="sm"
                                @click="emit('update:show', false)"
                                >Cancel</Button
                            >
                            <Button
                                size="sm"
                                :disabled="
                                    saving ||
                                    !name.trim() ||
                                    !plugin ||
                                    !credential
                                "
                                @click="emit('create')"
                                class="gap-1.5"
                            >
                                <RiLoader4Line
                                    v-if="saving"
                                    class="size-3.5 animate-spin"
                                />
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
