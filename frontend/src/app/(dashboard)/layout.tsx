import { DashboardShell } from "@/components/layout/dashboard-shell";
import { AuthGuard } from "@/components/providers/auth-guard";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <DashboardShell>{children}</DashboardShell>
    </AuthGuard>
  );
}
