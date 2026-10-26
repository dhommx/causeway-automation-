import { ExternalLink, Scan, ZoomIn, ZoomOut } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { viewUrl, type StoredFile } from "../../lib/api";
import Button from "../ui/Button";

const MIN = 0.1;
const MAX = 8;
const STEP = 1.25;
const PAD = 16; // the viewport's padding, so a fitted image doesn't touch the edges

type Size = { w: number; h: number };
type Anchor = { x: number; y: number; cx: number; cy: number };

/**
 * Shows an uploaded image so the user can read values from it (e.g. the AFS and PIE amounts).
 * Wheel zooms at the cursor, drag pans, double-click toggles 200% / fit, and + / - / 0 work from
 * the keyboard. "Fit" shows the whole image in the panel.
 */
export default function ImageViewer({ file }: { file: StoredFile }) {
  const box = useRef<HTMLDivElement>(null);
  const img = useRef<HTMLImageElement>(null);
  const [natural, setNatural] = useState<Size | null>(null);
  const [view, setView] = useState<Size>({ w: 0, h: 0 });
  const [zoom, setZoom] = useState<number | null>(null); // null = fit to the panel
  const anchor = useRef<Anchor | null>(null);
  const drag = useRef<{ x: number; y: number; left: number; top: number; moved: boolean } | null>(null);
  const [dragging, setDragging] = useState(false);

  // Track the viewport size so "fit" follows panel resizes.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setView({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const fit = natural && view.w
    ? Math.min((view.w - PAD * 2) / natural.w, (view.h - PAD * 2) / natural.h, 1)
    : 1;
  const scale = zoom ?? fit;

  /** Change zoom, keeping the image point under (cx, cy) (viewport coords) in place. */
  const zoomTo = useCallback(
    (next: number | null, cx?: number, cy?: number) => {
      const el = box.current;
      const pic = img.current;
      if (!el || !pic) return;
      const px = cx ?? el.clientWidth / 2;
      const py = cy ?? el.clientHeight / 2;
      anchor.current = {
        x: (el.scrollLeft + px - pic.offsetLeft) / scale,
        y: (el.scrollTop + py - pic.offsetTop) / scale,
        cx: px,
        cy: py,
      };
      setZoom(next === null ? null : Math.min(MAX, Math.max(MIN, next)));
    },
    [scale],
  );

  // After a zoom renders, scroll so the anchored point is back under the cursor.
  useLayoutEffect(() => {
    const el = box.current;
    const pic = img.current;
    const a = anchor.current;
    if (!el || !pic || !a) return;
    anchor.current = null;
    el.scrollLeft = a.x * scale + pic.offsetLeft - a.cx;
    el.scrollTop = a.y * scale + pic.offsetTop - a.cy;
  }, [scale]);

  // Wheel zoom needs a non-passive listener so the panel doesn't scroll at the same time.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomTo(scale * Math.pow(STEP, -e.deltaY / 100), e.clientX - r.left, e.clientY - r.top);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [scale, zoomTo]);

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    const el = box.current;
    if (!el || e.button !== 0) return;
    drag.current = { x: e.clientX, y: e.clientY, left: el.scrollLeft, top: el.scrollTop, moved: false };
    el.setPointerCapture(e.pointerId);
    setDragging(true);
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const el = box.current;
    const d = drag.current;
    if (!el || !d) return;
    if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 3) d.moved = true;
    el.scrollLeft = d.left - (e.clientX - d.x);
    el.scrollTop = d.top - (e.clientY - d.y);
  };
  const onPointerUp = () => {
    drag.current = null;
    setDragging(false);
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "+" || e.key === "=") zoomTo(scale * STEP);
    else if (e.key === "-") zoomTo(scale / STEP);
    else if (e.key === "0") zoomTo(null);
    else return;
    e.preventDefault();
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-2.5">
        <span className="text-xs font-medium text-muted-foreground">
          Image · scroll to zoom, drag to move
        </span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => zoomTo(scale / STEP)} aria-label="Zoom out" disabled={scale <= MIN}>
            <ZoomOut className="size-4" aria-hidden />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => zoomTo(1)}
            title="Actual size"
            className="w-16 tabular-nums"
          >
            {Math.round(scale * 100)}%
          </Button>
          <Button variant="ghost" size="sm" onClick={() => zoomTo(scale * STEP)} aria-label="Zoom in" disabled={scale >= MAX}>
            <ZoomIn className="size-4" aria-hidden />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => zoomTo(null)} disabled={zoom === null}>
            <Scan className="size-4" aria-hidden />
            Fit
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
      <div
        ref={box}
        tabIndex={0}
        aria-label={`${file.original_name}, zoom ${Math.round(scale * 100)}%`}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onDoubleClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          zoomTo(zoom === null ? Math.max(2, fit * 2) : null, e.clientX - r.left, e.clientY - r.top);
        }}
        className={`relative grid min-h-0 flex-1 touch-none overflow-auto bg-muted/50 select-none ${
          dragging ? "cursor-grabbing" : "cursor-grab"
        }`}
        style={{ padding: PAD }}
      >
        <img
          ref={img}
          src={viewUrl(file.id)}
          alt={file.original_name}
          draggable={false}
          onLoad={(e) => setNatural({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
          className="m-auto max-w-none"
          style={natural ? { width: natural.w * scale, height: natural.h * scale } : { maxWidth: "100%" }}
        />
      </div>
    </div>
  );
}
