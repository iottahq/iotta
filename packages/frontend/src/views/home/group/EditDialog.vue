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
  RiCheckLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiErrorWarningLine,
  RiFileCopyLine,
  RiLoader4Line,
  RiRefreshLine,
  RiSave3Line,
} from "@remixicon/vue";

defineProps<{
  group: Group | null;
  name: string;
  savingName: boolean;
  token: string | null;
  loadingToken: boolean;
  rotatingToken: boolean;
  tokenCopied: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  "update:name": [v: string];
  "save-name": [];
  "rotate-token": [];
  "copy-token": [];
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
        <div
          class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4"
        >
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-semibold">Edit Device group</h2>
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
                    :disabled="
                      savingName || !name.trim() || name === group.name
                    "
                    @click="emit('save-name')"
                  >
                    <RiLoader4Line
                      v-if="savingName"
                      class="size-3.5 animate-spin"
                    />
                    <RiSave3Line v-else class="size-3.5" />
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
            </div>

            <!-- API Token -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-medium">API Token</label>
              <div
                v-if="loadingToken"
                class="flex items-center gap-2 text-xs text-muted-foreground"
              >
                <RiLoader4Line class="size-3.5 animate-spin" />
                Loading…
              </div>
              <div v-else-if="token" class="flex flex-col gap-2">
                <div
                  class="rounded-md border border-border bg-muted/30 px-2.5 py-1.5 font-mono text-[10px] text-muted-foreground break-all"
                >
                  {{ token }}
                </div>
                <div class="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    class="gap-1.5 flex-1"
                    @click="emit('copy-token')"
                  >
                    <RiCheckLine
                      v-if="tokenCopied"
                      class="size-3.5 text-emerald-500"
                    />
                    <RiFileCopyLine v-else class="size-3.5" />
                    {{ tokenCopied ? "Copied!" : "Copy" }}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    class="gap-1.5 flex-1"
                    :disabled="rotatingToken"
                    @click="emit('rotate-token')"
                  >
                    <RiLoader4Line
                      v-if="rotatingToken"
                      class="size-3.5 animate-spin"
                    />
                    <RiRefreshLine v-else class="size-3.5" />
                    Rotate
                  </Button>
                </div>
              </div>
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
            <div class="flex gap-2 justify-between pt-1 border-t border-border">
              <Button
                variant="destructive"
                size="sm"
                class="gap-1.5"
                @click="emit('delete')"
              >
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
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
