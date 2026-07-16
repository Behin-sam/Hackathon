"use client";

import { motion } from "framer-motion";
import { Fingerprint, ShieldAlert, UserCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Identity shell. Displays structural placeholder metrics only — no
 * live data wiring yet, since business/domain logic is out of scope for
 * this phase. Mirrors the layout grid used on the Overview page.
 */
const metrics = [
  { label: "Verified identities", value: "—", icon: Fingerprint, status: "Pending integration" },
  { label: "Pending verification", value: "—", icon: UserCheck, status: "Pending integration" },
  { label: "Flagged for review", value: "—", icon: ShieldAlert, status: "Pending integration" },
];

export default function IdentityPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">Identity</h1>
          <Badge variant="secondary">Foundation build</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Verified identities across the network. This view is a structural placeholder pending
          domain logic.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric, i) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.05 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{metric.label}</CardTitle>
                <metric.icon className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">{metric.value}</div>
                <p className="mt-1 text-xs text-muted-foreground">{metric.status}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Next steps</CardTitle>
          <CardDescription>This view is ready for domain logic to be layered in.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1.5 text-sm text-muted-foreground">
            <li>Wire identity data models to the existing identity endpoints.</li>
            <li>Replace placeholder metrics with live React Query-backed widgets.</li>
            <li>Add an identities table with provider, verification, and risk columns.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
