"""Make a results workbook readable on first open (the user's rule, 23 Oct 2026): Arial, wrapped bold headers,
widths that fit, Rs as #,##0 and % to one decimal, frozen top row, filters."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def tidy(path: Path) -> None:
    wb = load_workbook(path)
    head, fill = Font(name="Arial", bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
    body, thin = Font(name="Arial", size=10), Side(style="thin", color="C8C8C8")
    for ws in wb.worksheets:
        for c in ws[1]:
            c.font, c.fill = head, fill
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.row_dimensions[1].height = 42
        ws.freeze_panes = "B2"
        for col in ws.columns:
            name = str(col[0].value or "")
            ws.column_dimensions[col[0].column_letter].width = max(12, min(30, max(len(str(c.value or "")) for c in col[1:200]) + 3)) if ws.max_row > 1 else 16
            for c in col[1:]:
                c.font, c.border = body, Border(top=thin, bottom=thin, left=thin, right=thin)
                if isinstance(c.value, (int, float)) and not isinstance(c.value, bool):
                    c.number_format = "#,##0;-#,##0;0" if "Rs" in name else "0.0" if "%" in name else "General"
        if ws.max_row > 1:
            ws.auto_filter.ref = ws.dimensions
    wb.save(path)
