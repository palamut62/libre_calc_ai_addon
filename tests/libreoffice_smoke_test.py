"""Manual integration smoke test for LibreOffice Calc automation.

Run with LibreOffice Python, for example:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" tests\\libreoffice_smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import CellInspector, CellManipulator, ErrorDetector, LibreOfficeBridge, SheetAnalyzer
from llm.tool_definitions import ToolDispatcher


def _ensure_calc_document(bridge: LibreOfficeBridge):
    """Ensure there is an active Calc document; create one if needed."""
    try:
        doc = bridge.get_active_document()
        if doc and doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
            return doc
    except Exception:
        pass

    return bridge._desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, ())


def _activate_sheet(doc, sheet_name: str):
    sheets = doc.getSheets()
    if not sheets.hasByName(sheet_name):
        sheets.insertNewByName(sheet_name, sheets.getCount())
    sheet = sheets.getByName(sheet_name)
    doc.getCurrentController().setActiveSheet(sheet)
    return sheet


def main() -> int:
    host = os.environ.get("LO_TEST_HOST", "127.0.0.1")
    port = int(os.environ.get("LO_TEST_PORT", "2003"))

    bridge = LibreOfficeBridge(host=host, port=port)
    results = []

    def run_test(name, fn):
        try:
            detail = fn()
            results.append({"test": name, "status": "PASS", "detail": detail})
        except Exception as exc:
            results.append(
                {
                    "test": name,
                    "status": "FAIL",
                    "detail": f"{exc}\n{traceback.format_exc()}",
                }
            )

    if not bridge.connect():
        print(
            json.dumps(
                {
                    "connected": False,
                    "host": host,
                    "port": port,
                    "results": [],
                    "error": "LibreOffice bridge connect() returned False.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    inspector = CellInspector(bridge)
    manipulator = CellManipulator(bridge)
    analyzer = SheetAnalyzer(bridge)
    detector = ErrorDetector(bridge, inspector)
    dispatcher = ToolDispatcher(inspector, manipulator, analyzer, detector)
    uniq = uuid.uuid4().hex[:6]
    new_sheet_name = f"Smoke_{uniq}"
    renamed_sheet_name = f"SmokeR_{uniq}"

    def run_dispatch(tool_name, args):
        raw = dispatcher.dispatch(tool_name, args)
        parsed = json.loads(raw)
        if "error" in parsed:
            raise RuntimeError(parsed["error"])
        return raw

    doc = _ensure_calc_document(bridge)
    _activate_sheet(doc, "CodexSmoke")

    run_test("write_formula", lambda: manipulator.write_formula("A1", "Gelir"))
    run_test("write_number_1", lambda: manipulator.write_formula("A2", "120"))
    run_test("write_number_2", lambda: manipulator.write_formula("A3", "80"))
    run_test("write_formula_calc", lambda: manipulator.write_formula("B2", "=A2*1.2"))
    run_test("read_range", lambda: inspector.read_range("A1:B3"))
    run_test(
        "set_cell_style",
        lambda: manipulator.set_range_style(
            "A1:B1",
            bold=True,
            bg_color=0xFFF2CC,
            border_color=0x333333,
            h_align="center",
        ),
    )
    run_test("set_column_width", lambda: manipulator.set_column_width("A", 28))
    run_test("set_row_height", lambda: manipulator.set_row_height(1, 9))
    run_test("auto_fit_column", lambda: manipulator.auto_fit_column("B"))
    run_test("sheet_summary", lambda: analyzer.get_sheet_summary())
    run_test("sort_range", lambda: manipulator.sort_range("A1:B3", sort_column=0, ascending=False, has_header=True))
    run_test("set_auto_filter", lambda: manipulator.set_auto_filter("A1:B3", enable=True))
    run_test(
        "dispatcher_write_formula",
        lambda: run_dispatch("write_formula", {"cell": "C2", "formula": "=B2-A2"}),
    )
    run_test(
        "dispatcher_get_cell_details",
        lambda: run_dispatch("get_cell_details", {"address": "C2"}),
    )
    run_test(
        "dispatcher_create_sheet",
        lambda: run_dispatch("create_sheet", {"sheet_name": new_sheet_name}),
    )
    run_test(
        "dispatcher_switch_sheet",
        lambda: run_dispatch("switch_sheet", {"sheet_name": new_sheet_name}),
    )
    run_test(
        "dispatcher_rename_sheet",
        lambda: run_dispatch("rename_sheet", {"old_name": new_sheet_name, "new_name": renamed_sheet_name}),
    )
    run_test(
        "dispatcher_switch_back",
        lambda: run_dispatch("switch_sheet", {"sheet_name": "CodexSmoke"}),
    )
    run_test("copy_range", lambda: manipulator.copy_range("A1:B3", "D1"))
    run_test(
        "create_chart",
        lambda: manipulator.create_chart("A1:B3", chart_type="column", title="Smoke Chart", position="F2"),
    )
    run_test("write_error_formula", lambda: manipulator.write_formula("E2", "=1/0"))
    run_test("detect_errors", lambda: detector.detect_and_explain("E2:E2"))
    run_test("list_sheets", lambda: manipulator.list_sheets())

    failed = [r for r in results if r["status"] == "FAIL"]
    output = {
        "connected": True,
        "host": host,
        "port": port,
        "results": results,
        "pass_count": len(results) - len(failed),
        "fail_count": len(failed),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
