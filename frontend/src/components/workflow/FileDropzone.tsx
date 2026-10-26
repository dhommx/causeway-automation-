import clsx from "clsx";
import { Upload } from "lucide-react";
import { useRef, useState } from "react";

export default function FileDropzone({
  accept,
  multiple,
  busy,
  onFiles,
}: {
  accept: string[];
  multiple: boolean;
  busy: boolean;
  onFiles: (files: File[]) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const take = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    if (files.length) onFiles(multiple ? files : files.slice(0, 1));
  };

  return (
    <button
      type="button"
      disabled={busy}
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
      className={clsx(
        "flex w-full cursor-pointer flex-col items-center gap-1.5 rounded-[var(--radius)] border border-dashed px-4 py-5 text-center transition-colors duration-150",
        over ? "border-accent bg-accent-soft" : "border-border bg-muted/50 hover:border-accent hover:bg-accent-soft/60",
        busy && "opacity-60",
      )}
    >
      <Upload className="size-5 text-primary" aria-hidden />
      <span className="text-sm font-medium text-foreground">{busy ? "Uploading..." : "Drop files or click to choose"}</span>
      <span className="text-xs text-muted-foreground">{accept.join(" ")}</span>
      <input
        ref={input}
        type="file"
        hidden
        multiple={multiple}
        accept={accept.join(",")}
        onChange={(e) => {
          take(e.target.files);
          e.target.value = "";
        }}
      />
    </button>
  );
}
