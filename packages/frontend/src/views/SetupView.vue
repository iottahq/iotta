<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api, tokenStore, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { RiLoader4Line, RiErrorWarningLine } from "@remixicon/vue";

const router = useRouter();

const form = ref({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    password_confirm: "",
});

const loading = ref(false);
const error = ref<string | null>(null);

async function submit() {
    error.value = null;
    
    if (form.value.password !== form.value.password_confirm) {
        error.value = "Passwords don't match.";
        return;
    }
    if (form.value.password.length < 8) {
        error.value = "Password must be at least 8 characters.";
        return;
    }
    
    loading.value = true;
    try {
        const res = await api.auth.setup({
            first_name: form.value.first_name.trim(),
            last_name: form.value.last_name.trim(),
            email: form.value.email.trim(),
            password: form.value.password,
        });
        tokenStore.set(res.access_token);
        router.replace("/");
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Setup failed.";
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="min-h-svh flex items-center justify-center bg-background px-4">
        <div class="w-full max-w-sm">
            <div class="mb-8 text-center">
                <h1 class="text-2xl font-semibold tracking-tight">iotta.</h1>
                <p class="mt-1.5 text-sm text-muted-foreground">Create your admin account to get started.</p>
            </div>
            <div class="rounded-xl border border-border bg-card px-6 py-8 shadow-sm">
                <form @submit.prevent="submit" class="flex flex-col gap-4">
                    <div class="grid grid-cols-2 gap-3">
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">First name</label>
                            <Input v-model="form.first_name" placeholder="Ada" required autocomplete="given-name" />
                        </div>
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Last name</label>
                            <Input v-model="form.last_name" placeholder="Lovelace" required autocomplete="family-name" />
                        </div>
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium">Email</label>
                        <Input v-model="form.email" type="email" placeholder="ada@example.com" required autocomplete="email" />
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium">Password</label>
                        <Input v-model="form.password" type="password" placeholder="Min. 8 characters" required autocomplete="new-password" />
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-medium">Confirm password</label>
                        <Input v-model="form.password_confirm" type="password" placeholder="Repeat password" required autocomplete="new-password" />
                    </div>
                    <div v-if="error" class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs">
                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        {{ error }}
                    </div>
                    <Button type="submit" class="w-full mt-1" :disabled="loading">
                        <RiLoader4Line v-if="loading" class="size-3.5 animate-spin" />
                        {{ loading ? "Creating account…" : "Create account" }}
                    </Button>
                </form>
            </div>
        </div>
    </div>
</template>