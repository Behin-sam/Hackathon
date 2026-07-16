/**
 * Shared domain types mirrored from backend Pydantic schemas.
 * Kept minimal for the foundation phase — no business/domain entities yet.
 */
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  status: string;
  is_active: boolean;
  is_superuser: boolean;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MFARequiredResponse {
  mfa_required: true;
  mfa_token: string;
}

export type LoginResponse = TokenResponse | MFARequiredResponse;

export function isMfaRequired(data: LoginResponse): data is MFARequiredResponse {
  return (data as MFARequiredResponse).mfa_required === true;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface MfaVerifyPayload {
  mfa_token: string;
  code: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface NavItem {
  label: string;
  href: string;
  icon: string;
}
