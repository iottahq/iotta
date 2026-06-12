<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ApiToken } from "@/lib/api";
import { RiDeleteBinLine, RiLoader4Line } from "@remixicon/vue";

const props = defineProps<{
    show: boolean;
    token: ApiToken | null;
    deleting: boolean;
}>();

const emit = defineEmits<{
    cancel: [];
    confirm: [];
}>();

const nameInput = ref("");

watch(() => props.show, (v) => {
    if (v) nameInput.value = "";
});

const nameMatches = computed(() => nameInput.value.trim() === props.token?.name);
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show && token"
                class="fixed inset-0 z-[60] flex items-center justify-center"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('cancel')" />
                <div class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 flex flex-col gap-4">

                    <div>
                        <h2 class="text-sm font-semibold">Delete token?</h2>
                        <p class="text-xs text-muted-foreground mt-1">
                            Any integration using
                            <span class="font-medium text-foreground">{{ token.name }}</span>
                            will immediately lose access to all
                            <span class="font-medium text-destructive">{{ token.devices.length }} device{{ token.devices.length !== 1 ? "s" : "" }}</span>.
                            This action cannot be undone.
                        </p>
                    </div>

                    <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium">
                            Type <span class="font-mono text-foreground bg-muted px-1 py-0.5 rounded">{{ token.name }}</span> to confirm
                        </label>
                        <Input
                            v-model="nameInput"
                            :placeholder="token.name"
                            :class="nameInput && !nameMatches ? 'border-destructive focus-visible:border-destructive' : ''"
                            autofocus
                            @keydown.enter="nameMatches && !deleting && emit('confirm')"
                        />
                    </div>

                    <div class="flex gap-2 justify-end">
                        <Button variant="outline" size="sm" @click="emit('cancel')">Cancel</Button>
                        <Button
                            variant="destructive"
                            size="sm"
                            class="gap-1.5"
                            :disabled="!nameMatches || deleting"
                            @click="emit('confirm')"
                        >
                            <RiLoader4Line v-if="deleting" class="size-3.5 animate-spin" />
                            <RiDeleteBinLine v-else class="size-3.5" />
                            Delete token
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
