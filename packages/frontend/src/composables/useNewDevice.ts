/**
 * useNewDevice.ts – shared composable to trigger the new device dialog
 * from anywhere in the app (e.g. sidebar, home view).
 *
 * The ref lives outside the function so it's a true singleton across components.
 */

import { ref } from "vue";

const open = ref(false);
const targetGroupId = ref<string | null>(null);

export function useNewDevice() {
    function openDialog(groupId: string | null = null) {
        targetGroupId.value = groupId;
        open.value = true;
    }

    function closeDialog() {
        open.value = false;
        targetGroupId.value = null;
    }

    return { open, targetGroupId, openDialog, closeDialog };
}