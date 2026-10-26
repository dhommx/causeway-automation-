import { themeQuartz, type ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { useMemo } from "react";

const theme = themeQuartz.withParams({
  fontFamily: "inherit",
  fontSize: 13,
  headerFontWeight: 600,
  headerBackgroundColor: "#eef2f6",
  borderColor: "#dde4eb",
  accentColor: "#3fc1c9",
  foregroundColor: "#0f1f2e",
  rowHoverColor: "#f3f8fb",
  wrapperBorderRadius: 0,
  wrapperBorder: false,
  spacing: 6,
});

/**
 * Spreadsheet-style grid for columns + rows as the API returns them. Virtualised, so large
 * previews stay fast. Fills its parent; give the parent a height (flex-1 min-h-0).
 */
export default function DataGrid({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  const columnDefs = useMemo<ColDef[]>(
    () =>
      columns.map((name, i) => ({
        headerName: name || `Column ${i + 1}`,
        field: String(i),
        filter: true,
        sortable: true,
        resizable: true,
        minWidth: 110,
        cellClass: (p) => (typeof p.value === "number" ? "tabular-nums text-right" : undefined),
      })),
    [columns],
  );
  const rowData = useMemo(
    () => rows.map((r) => Object.fromEntries(r.map((v, i) => [String(i), v]))),
    [rows],
  );

  return (
    <div className="h-full min-h-0 w-full">
      <AgGridReact
        theme={theme}
        columnDefs={columnDefs}
        rowData={rowData}
        autoSizeStrategy={{ type: "fitCellContents" }}
        enableCellTextSelection
        suppressDragLeaveHidesColumns
      />
    </div>
  );
}
