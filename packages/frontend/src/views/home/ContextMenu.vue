<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";

export interface ContextMenuItem {
    label: string;
    icon?: any;
    variant?: "default" | "destructive";
    action: () => void;
    separator?: boolean;
}

const props = defineProps<{
    items: ContextMenuItem[];
    x: number;
    y: number;
}>();

const emit = defineEmits<{
    close: [];
}>();

const menuRef = ref<HTMLElement | null>(null);
const adjustedX = ref(props.x);
const adjustedY = ref(props.y);

onMounted(async () => {
    await nextTick();
    if (!menuRef.value) return;
    const rect = menuRef.value.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    adjustedX.value = props.x + rect.width > vw ? vw - rect.width - 8 : props.x;
    adjustedY.value = props.y + rect.height > vh ? vh - rect.height - 8 : props.y;

    document.addEventListener("mousedown", onOutsideClick);
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("contextmenu", onOutsideClick);
});

onUnmounted(() => {
    document.removeEventListener("mousedown", onOutsideClick);
    document.removeEventListener("keydown", onKeyDown);
    document.removeEventListener("contextmenu", onOutsideClick);
});

function onOutsideClick(e: Event) {
    if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
        emit("close");
    }
}

function onKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") emit("close");
}

function trigger(item: ContextMenuItem) {
    item.action();
    emit("close");
}
</script>

<template>
    <Teleport to="body">
        <div
            ref="menuRef"
            class="fixed z-[100] min-w-[160px] rounded-lg border border-border bg-popover shadow-lg py-1 overflow-hidden"
            :style="{ left: `${adjustedX}px`, top: `${adjustedY}px` }"
        >
            <template v-for="(item, i) in items" :key="i">
                <div v-if="item.separator" class="my-1 h-px bg-border mx-2" />
                <button
                    v-else
                    class="flex items-center gap-2.5 w-full px-3 py-1.5 text-xs transition-colors text-left"
                    :class="
                        item.variant === 'destructive'
                            ? 'text-destructive hover:bg-destructive/10'
                            : 'text-foreground hover:bg-muted/70'
                    "
                    @click="trigger(item)"
                >
                    <component
                        v-if="item.icon"
                        :is="item.icon"
                        class="size-3.5 shrink-0"
                        :class="item.variant === 'destructive' ? 'text-destructive' : 'text-muted-foreground'"
                    />
                    {{ item.label }}
                </button>
            </template>
        </div>
    </Teleport>
</template>