import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

const styles: Record<Variant, string> = {
  primary:
    "bg-primary text-on-primary font-semibold shadow-sm hover:bg-primary-hover hover:-translate-y-px hover:shadow-md active:translate-y-0 active:scale-[.98]",
  secondary: "border border-border bg-card text-foreground font-medium hover:bg-muted",
  ghost: "text-primary font-medium hover:bg-primary/10",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "md" | "sm" };

export default function Button({ variant = "primary", size = "md", className, ...rest }: Props) {
  return (
    <button
      type="button"
      className={clsx(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-[var(--radius)] text-sm transition-[transform,box-shadow,background-color] duration-200 ease-out",
        "disabled:pointer-events-none disabled:opacity-50 motion-reduce:transform-none",
        size === "md" ? "min-h-11 px-5" : "min-h-9 px-3",
        styles[variant],
        className,
      )}
      {...rest}
    />
  );
}
