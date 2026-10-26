import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

import EmptyState from "../components/ui/EmptyState";

export default function NotFoundPage() {
  return (
    <EmptyState
      icon={<Compass className="size-5" />}
      title="Page not found"
      action={
        <Link to="/" className="text-sm font-medium text-primary hover:underline">
          Back to automations
        </Link>
      }
    >
      This page does not exist.
    </EmptyState>
  );
}
