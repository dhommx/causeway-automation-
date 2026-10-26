import { ExternalLink, Maximize2, Minimize2 } from "lucide-react";
import { useState } from "react";

import { viewUrl, type StoredFile } from "../../lib/api";
import Button from "../ui/Button";

/**
 * Shows an uploaded image so the user can read values from it (e.g. the AFS and PIE amounts).
 * "Fit" shows the whole image in the panel; "Actual size" lets the user scroll around it.
 */
export default function ImageViewer({ file }: { file: StoredFile }) {
  const [actual, setActual] = useState(false);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-5 py-2.5">
        <span className="text-xs font-medium text-muted-foreground">Image · for reference, not processed</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => setActual((a) => !a)}>
            {actual ? <Minimize2 className="size-4" aria-hidden /> : <Maximize2 className="size-4" aria-hidden />}
            {actual ? "Fit" : "Actual size"}
          </Button>
          <a
            href={viewUrl(file.id)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-9 items-center gap-2 rounded-[var(--radius)] px-3 text-sm font-medium text-primary hover:bg-primary/10"
          >
            <ExternalLink className="size-4" aria-hidden />
            Open
          </a>
        </div>
      </div>
      <div className="scroll-area min-h-0 flex-1 bg-muted/50 p-4">
        <img
          src={viewUrl(file.id)}
          alt={file.original_name}
          className={actual ? "max-w-none" : "mx-auto h-full w-full object-contain"}
        />
      </div>
    </div>
  );
}
