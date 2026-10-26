import { History, Play, SlidersHorizontal } from "lucide-react";

export type WorkflowTab = "run" | "history" | "rules";

export const WORKFLOW_TABS = [
  { value: "run" as const, label: "Run", icon: <Play className="size-4" /> },
  { value: "history" as const, label: "History", icon: <History className="size-4" /> },
  { value: "rules" as const, label: "Rules", icon: <SlidersHorizontal className="size-4" /> },
];
