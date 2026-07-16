"use client";

import { motion } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Settings shell. Displays structural placeholder rows only — no live
 * data wiring yet, since business/domain logic is out of scope for this
 * phase. Mirrors the card layout used elsewhere in the console.
 */
const settings = [
  { label: "Workspace name", value: "SettlementNetwork" },
  { label: "Default region", value: "Pending integration" },
  { label: "Role-based access control", value: "Not yet enabled" },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <Badge variant="secondary">Foundation build</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Workspace and access configuration. This view is a structural placeholder pending domain
          logic.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Core settings for this console instance.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {settings.map((row, i) => (
            <motion.div
              key={row.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
              className="flex items-center justify-between rounded-md border border-border px-4 py-3"
            >
              <span className="text-sm text-muted-foreground">{row.label}</span>
              <span className="text-sm font-medium">{row.value}</span>
            </motion.div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Next steps</CardTitle>
          <CardDescription>This view is ready for domain logic to be layered in.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1.5 text-sm text-muted-foreground">
            <li>Add role-based access control on top of the existing JWT auth.</li>
            <li>Wire workspace and region configuration to the backend.</li>
            <li>Add editable form fields backed by React Query mutations.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
