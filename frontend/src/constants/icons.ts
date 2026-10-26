import { Banknote, Bell, Receipt, Wallet, Workflow, type LucideIcon } from "lucide-react";

/** Workflow.icon names from the backend, mapped to icons. Add an entry when a workflow uses a new one. */
export const WORKFLOW_ICONS: Record<string, LucideIcon> = {
  receipt: Receipt,
  banknote: Banknote,
  wallet: Wallet,
  bell: Bell,
  workflow: Workflow,
};

export const iconFor = (name: string): LucideIcon => WORKFLOW_ICONS[name] ?? Workflow;
