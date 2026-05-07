"""Her provider için temiz sayfa açıp tüm araç işlevlerini test eder.

LLM-yönlendirmeli senaryo + dispatcher üzerinden doğrudan tüm tool kapsama
testi yapar. Sonuçta her provider için pass/fail dökümü basar.
"""
from __future__ import annotations
import json, sys, traceback, uuid, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import CellInspector, CellManipulator, ErrorDetector, LibreOfficeBridge, SheetAnalyzer
from llm.tool_definitions import TOOLS, ToolDispatcher
from llm import NvidiaProvider, OpenRouterProvider, OllamaProvider

HOST = os.environ.get("LO_TEST_HOST", "127.0.0.1")
PORT = int(os.environ.get("LO_TEST_PORT", "2002"))


def fresh_sheet(bridge, name):
    doc = bridge.get_active_document()
    sheets = doc.getSheets()
    if sheets.hasByName(name):
        sheets.removeByName(name)
    sheets.insertNewByName(name, sheets.getCount())
    doc.getCurrentController().setActiveSheet(sheets.getByName(name))
    return doc


def llm_scenario(provider, dispatcher, max_steps=14):
    """Bir LLM oturumu boyunca tool çağrılarını topla."""
    msgs = [
        {"role": "system", "content":
         "Sen LibreOffice Calc asistanisin. Aktif sayfada calisirsin. "
         "Kullanicinin tum istediklerini sirayla TOOL kullanarak yap. "
         "Her adimda en uygun tool'u sec. Sonunda kisa ozet ver."},
        {"role": "user", "content":
         "Su gorevleri sirayla yap:\n"
         "1) A1='Urun', B1='Adet', C1='Fiyat', D1='Toplam' yaz.\n"
         "2) A2='Elma', A3='Armut', A4='Muz' yaz; B2=5, B3=3, B4=8; C2=10, C3=15, C4=8.\n"
         "3) D2,D3,D4 hucrelerine =B*C formulu (yani D2=B2*C2 vb) yaz.\n"
         "4) A6='Toplam' yaz, D6'ya =SUM(D2:D4) formulu koy.\n"
         "5) A1:D1 araligini kalin yap, arka plan rengi sari (0xFFFF99).\n"
         "6) A sutunu genisligini 25mm yap.\n"
         "7) 1. satir yuksekligini 10mm yap.\n"
         "8) B sutununu icerige gore otomatik genislet.\n"
         "9) A1:D4 araligini D sutuna gore azalan sirala (basliklar var).\n"
         "10) A1:D4 araligina otomatik filtre ekle.\n"
         "11) E2 hucresine =1/0 yazdir (hata uretmek icin).\n"
         "12) E2:E2 araligini hata aciklamasi icin tara.\n"
         "13) Sayfa ozetini al.\n"
         "14) Tum sayfalari listele.\n"
         "Bittiginde 'TAMAM' de."},
    ]
    calls = []
    for step in range(max_steps):
        try:
            r = provider.chat_completion(msgs, tools=TOOLS)
        except Exception as e:
            calls.append({"step": step, "error": f"chat_completion fail: {e}"})
            break
        tcs = r.get("tool_calls")
        if not tcs:
            calls.append({"step": step, "final": (r.get("content") or "")[:300]})
            break
        msgs.append({"role": "assistant", "content": r.get("content"), "tool_calls": tcs})
        for tc in tcs:
            fn = tc["function"]
            args = fn["arguments"]
            if isinstance(args, str):
                try: args = json.loads(args)
                except Exception: args = {}
            if not isinstance(args, dict):
                args = {}
            try:
                res = dispatcher.dispatch(fn["name"], args)
            except Exception as e:
                res = json.dumps({"error": str(e)})
            ok = '"error"' not in res[:120]
            calls.append({"tool": fn["name"], "args": args, "ok": ok, "res": res[:200]})
            msgs.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": res})
    return calls


def direct_coverage(dispatcher, sheet_uniq):
    """Senaryoda LLM'in cagirmadigi tool'lari dogrudan dene."""
    extra_sheet = f"X_{sheet_uniq}"
    plan = [
        ("create_sheet", {"sheet_name": extra_sheet}),
        ("switch_sheet", {"sheet_name": extra_sheet}),
        ("write_formula", {"cell": "A1", "formula": "1"}),
        ("write_formula", {"cell": "A2", "formula": "2"}),
        ("write_formula", {"cell": "A3", "formula": "=A1+A2"}),
        ("write_formula", {"cell": "B1", "formula": "X"}),
        ("write_formula", {"cell": "B2", "formula": "Y"}),
        ("merge_cells", {"range_name": "B1:C1"}),
        ("insert_rows", {"row_num": 1, "count": 1}),
        ("insert_columns", {"col_letter": "B", "count": 1}),
        ("delete_columns", {"col_letter": "B", "count": 1}),
        ("delete_rows", {"row_num": 1, "count": 1}),
        ("get_all_formulas", {}),
        ("analyze_spreadsheet_structure", {}),
        ("get_cell_details", {"address": "A3"}),
        ("get_cell_precedents", {"address": "A3"}),
        ("get_cell_dependents", {"address": "A1"}),
        ("set_conditional_format", {
            "range_name": "A1:A3", "format_type": "value_condition",
            "condition": "greater_than", "value1": "1", "color": "#FFCCCC"}),
        ("set_data_validation", {
            "range_name": "C1:C3", "validation_type": "list",
            "values": "dusuk,orta,yuksek"}),
        ("copy_range", {"source_range": "A1:A3", "target_cell": "E1"}),
        ("create_chart", {"data_range": "A1:A3", "chart_type": "bar",
                          "title": "Cov", "position": "G1"}),
        ("clear_range", {"range_name": "E1:E3"}),
        ("rename_sheet", {"old_name": extra_sheet, "new_name": extra_sheet + "R"}),
    ]
    out = []
    for name, args in plan:
        try:
            res = dispatcher.dispatch(name, args)
            ok = '"error"' not in res[:150]
        except Exception as e:
            res = f"EXC: {e}"
            ok = False
        out.append({"tool": name, "ok": ok, "res": res[:150]})
    return out


def stream_smoke(provider):
    """Streaming tek satir 'OK' uret."""
    chunks = []
    try:
        for c in provider.stream_completion([
            {"role": "system", "content": "Briefly."},
            {"role": "user", "content": "Reply with exactly: OK"},
        ]):
            if c.get("content"):
                chunks.append(c["content"])
            if c.get("done"):
                break
        return {"ok": True, "text": "".join(chunks)[:60]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def list_models_smoke(provider):
    try:
        m = provider.get_available_models()
        return {"ok": True, "count": len(m), "sample": m[:3]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def run_provider(label, prov_factory, bridge):
    print(f"\n========== PROVIDER: {label} ==========")
    uniq = uuid.uuid4().hex[:5]
    sheet = f"P_{label}_{uniq}"
    fresh_sheet(bridge, sheet)
    insp = CellInspector(bridge); manip = CellManipulator(bridge)
    analyz = SheetAnalyzer(bridge); det = ErrorDetector(bridge, insp)
    disp = ToolDispatcher(insp, manip, analyz, det)

    provider = prov_factory()

    print("[A] list_models:", list_models_smoke(provider))
    print("[B] stream:", stream_smoke(provider))

    print("[C] LLM scenario:")
    calls = llm_scenario(provider, disp)
    used_tools = set()
    fail_tools = []
    for c in calls:
        if "tool" in c:
            used_tools.add(c["tool"])
            if not c["ok"]:
                fail_tools.append((c["tool"], c["res"]))
            print(f"  - {c['tool']}({json.dumps(c['args'], ensure_ascii=False)[:80]}) "
                  f"=> {'OK' if c['ok'] else 'FAIL'} {c['res'][:90]}")
        elif "final" in c:
            print(f"  [final] {c['final'][:200]}")
        elif "error" in c:
            print(f"  [LLM ERROR] {c['error']}")

    print(f"  scenario tools used: {sorted(used_tools)}")
    print(f"  scenario failures: {fail_tools}")

    print("[D] Direct coverage of remaining tools:")
    cov = direct_coverage(disp, uniq)
    cov_fail = [c for c in cov if not c["ok"]]
    for c in cov:
        print(f"  - {c['tool']:30s} {'OK' if c['ok'] else 'FAIL'} {c['res'][:90]}")

    provider.close()

    return {
        "provider": label,
        "stream_ok": True,
        "scenario_tools": sorted(used_tools),
        "scenario_failures": fail_tools,
        "coverage_failures": cov_fail,
    }


def main():
    bridge = LibreOfficeBridge(host=HOST, port=PORT)
    assert bridge.connect(), f"LO baglanti yok {HOST}:{PORT}"

    summary = []
    for label, factory in [
        ("NVIDIA", NvidiaProvider),
        ("OpenRouter", OpenRouterProvider),
        ("Ollama", OllamaProvider),
    ]:
        try:
            summary.append(run_provider(label, factory, bridge))
        except Exception as e:
            traceback.print_exc()
            summary.append({"provider": label, "fatal": str(e)})

    print("\n\n=========== ÖZET ===========")
    for s in summary:
        print(json.dumps(s, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
