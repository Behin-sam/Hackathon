"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { clearTokens, isAuthenticated, setTokens } from "@/lib/auth";
import { isMfaRequired } from "@/types";
import type { LoginPayload, LoginResponse, MfaVerifyPayload, TokenResponse, User } from "@/types";

/** Fetches the currently authenticated user; disabled when no token is present. */
export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const { data } = await apiClient.get<User>("/auth/me");
      return data;
    },
    enabled: isAuthenticated(),
    retry: false,
  });
}

/**
 * Handles login submission, token persistence, and redirect.
 *
 * `/auth/login` returns one of two shapes: a token pair, or (when the
 * account has MFA enabled) an `{ mfa_required, mfa_token }` challenge that
 * must be resolved via `useMfaVerifyLogin` before any tokens exist. Callers
 * should check `login.data` with `isMfaRequired` to branch the UI.
 */
export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const { data } = await apiClient.post<LoginResponse>("/auth/login", payload);
      return data;
    },
    onSuccess: async (data) => {
      if (isMfaRequired(data)) {
        // No tokens yet — the account requires an MFA code before we can
        // authenticate. Leave token storage untouched and let the caller
        // (LoginPage) redirect into the MFA challenge screen.
        return;
      }
      setTokens(data.access_token, data.refresh_token);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      router.push("/dashboard");
    },
  });
}

/** Resolves an MFA login challenge (mfa_token + OTP code) into a real token pair. */
export function useMfaVerifyLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MfaVerifyPayload) => {
      const { data } = await apiClient.post<TokenResponse>("/auth/mfa/verify-login", payload);
      return data;
    },
    onSuccess: async (data) => {
      setTokens(data.access_token, data.refresh_token);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      router.push("/dashboard");
    },
  });
}

/** Clears session state and returns to the login screen. */
export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return () => {
    clearTokens();
    queryClient.clear();
    router.push("/login");
  };
}
