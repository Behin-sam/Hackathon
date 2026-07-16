"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { isAuthenticated } from "@/lib/auth";

/**
 * Client-side gate for the (dashboard) route group. Without this, any
 * visitor could open /dashboard directly with no access token and the
 * shell would render as if signed in (Navbar just quietly showed "Not
 * signed in"). Redirects to /login when no access token is present.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setChecked(true);
  }, [router]);

  if (!checked) {
    return null;
  }

  return <>{children}</>;
}
