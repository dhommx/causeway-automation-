import { themeQuartz, type ColDef, type GridApi } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { useMemo, useRef } from "react";

const theme = themeQuartz.withParams({
  fontFamily: "inherit",
  fontSize: 14,
  headerFontWeight: 600,
  headerBackgroundColor: "#eef2f6",
  borderColor: "#dde4eb",
  accentColor: "#3fc1c9",
  foregroundColor: "#0f1f2e",
  rowHoverColor: "#f3f8fb",
  wrapperBorderRadius: 0,
  wrapperBorder: false,
  spacing: 5,
});

/** Cell texts that are notes, not values (e.g. "From ERP": the ERP fills it in). They can't be
 *  selected or copied, so nobody pastes them into the ERP by mistake. */
const NOT_COPYABLE = new Set(["From ERP"]);

/** Excel column letter for a 0-based index: 0 -> A, 26 -> AA. */
function columnLetter(i: number): string {
  let s = "";
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

/** Fit columns to their contents; if that leaves empty space on the right, stretch them to fill it. */
function fitColumns(api: GridApi, box: HTMLElement | null) {
  // Wait a frame so new columns (e.g. after switching result tabs) are rendered before measuring.
  requestAnimationFrame(() => {
    if (api.isDestroyed()) return;
    api.autoSizeAllColumns();
    const width = api.getColumns()?.reduce((sum, c) => sum + c.getActualWidth(), 0) ?? 0;
    if (box && width < box.clientWidth) api.sizeColumnsToFit();
  });
}

/**
 * Spreadsheet-style grid for columns + rows as the API returns them. Virtualised, so large
 * previews stay fast. Fills its parent; give the parent a height (flex-1 min-h-0).
 */
export default function DataGrid({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  const box = useRef<HTMLDivElement>(null);
  const columnDefs = useMemo<ColDef[]>(
    () =>
      columns.map((name, i) => ({
        // Sheets without a header row get "__UNNAMED__n" names when read; show Excel letters instead.
        headerName: !name || name.startsWith("__UNNAMED__") ? columnLetter(i) : name,
        field: String(i),
        // Mixed columns (a number, then a blank total row) must not be forced to one type.
        cellDataType: false,
        filter: true,
        sortable: true,
        resizable: true,
        minWidth: 72,
        tooltipValueGetter: (p) => (p.value == null ? undefined : String(p.value)),
        cellClass: (p) =>
          typeof p.value === "number"
            ? "tabular-nums text-right"
            : NOT_COPYABLE.has(String(p.value))
              ? "select-none italic text-muted-foreground"
              : undefined,
      })),
    [columns],
  );
  const rowData = useMemo(
    () => rows.map((r) => Object.fromEntries(r.map((v, i) => [String(i), v]))),
    [rows],
  );

  return (
    <div ref={box} className="h-full min-h-0 w-full">
      <AgGridReact
        theme={theme}
        columnDefs={columnDefs}
        rowData={rowData}
        onFirstDataRendered={(e) => fitColumns(e.api, box.current)}
        onGridSizeChanged={(e) => fitColumns(e.api, box.current)}
        onRowDataUpdated={(e) => fitColumns(e.api, box.current)}
        onDisplayedColumnsChanged={(e) => fitColumns(e.api, box.current)}
        enableCellTextSelection
        suppressDragLeaveHidesColumns
      />
    </div>
  );
}
