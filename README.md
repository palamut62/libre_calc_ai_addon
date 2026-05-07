# LibreCalc AI Assistant

An AI sidebar assistant for **LibreOffice Calc** that lets you ask questions, generate formulas, format tables, build charts, and detect errors — all through natural-language chat. Pluggable across **NVIDIA NIM, OpenRouter, Google Gemini, Groq, and local Ollama** providers, with full tool-calling so the AI directly drives your spreadsheet via the UNO bridge.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![LibreOffice](https://img.shields.io/badge/LibreOffice-Calc-green)
![Status](https://img.shields.io/badge/status-active-brightgreen)

---

## Table of Contents

- [Features](#features)
- [Supported AI Providers](#supported-ai-providers)
- [Tool Catalogue](#tool-catalogue-what-the-ai-can-do)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Project Layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Chat & Reasoning
- Streaming chat with conversation history scoped to the active workbook.
- Tool-calling loop: the model picks the right action, the dispatcher executes it on Calc, the result is fed back, and the model decides what to do next.
- Markdown rendering, code blocks, and structured responses.
- Token / cost tracking on providers that expose it (OpenRouter).

### Spreadsheet Automation (28 tools)
- **Cells & Values** — read ranges, write text/numbers/formulas, clear ranges.
- **Formatting** — bold, italic, font size & color, background color, alignment, wrap, borders, merge/unmerge.
- **Layout** — column width, row height, auto-fit, insert/delete rows & columns.
- **Tables** — sort, auto-filter, conditional formatting, data validation (drop-downs, ranges).
- **Sheets** — list, switch, create, rename.
- **Analysis** — full sheet summary, structure analysis (input/output cells), cell details, precedents & dependents, formula inventory.
- **Errors** — detect `#DIV/0!`, `#NAME?`, `#REF!`, `#VALUE!`, `#N/A`, etc., with human-readable explanations and fix suggestions.
- **Charts** — bar, column, line, pie, scatter charts placed at any cell.
- **Copy** — duplicate any range to a new location.

### UI / UX
- Clean side-panel UI with light/dark/system theme.
- English & Turkish localization with instant switching.
- Live selection tracker — your current cell or range is always visible to the AI.
- Settings dialog with per-provider API keys, model picker, temperature, and max-tokens controls.
- Help dialog with quick-start prompts.

### Reliability
- Robust input coercion: numeric arguments from any provider (JSON `int`, `float`, or string) are normalized before hitting Calc.
- Clear error surfaces in chat instead of silent failures.
- Conversation auto-trim to stay inside model context windows.

---

## Supported AI Providers

| Provider | Default model | Hosting | Tool-calling | Notes |
|---|---|---|---|---|
| **OpenRouter** | `google/gemini-2.5-flash` | Cloud | ✅ | Best price / quality default. Switch to `gemini-2.5-flash-lite`, `gpt-5.3-mini`, `claude-haiku-4.5`, etc. from settings. |
| **NVIDIA NIM** | `nvidia/llama-3.3-nemotron-super-49b-v1` | Cloud | ✅ | Free-tier friendly. Get a key at [build.nvidia.com](https://build.nvidia.com). |
| **Google Gemini** | `gemini-2.5-flash` | Cloud | ✅ | Native Gemini API, vision-capable variants supported. |
| **Groq** | `llama-3.3-70b-versatile` | Cloud | ✅ | Ultra-low latency. |
| **Ollama** | `gemma4:31b-cloud` (configurable) | Local / Ollama Cloud | ✅* | Set any pulled model. *Tool-calling requires a tool-capable model (e.g. Llama 3.1+, Qwen 2.5+, Mistral, Gemma 3+). |

API keys are entered through the Settings dialog and stored under `~/.config/libre_calc_ai/settings.json`. The `.env` file is for development overrides only — keys typed in the UI take precedence.

---

## Tool Catalogue (what the AI can do)

The dispatcher exposes 28 OpenAI-compatible function tools. The AI selects them automatically based on your prompt.

| Group | Tools |
|---|---|
| Read | `read_cell_range`, `get_cell_details`, `get_cell_precedents`, `get_cell_dependents`, `get_all_formulas`, `get_sheet_summary`, `analyze_spreadsheet_structure`, `list_sheets` |
| Write | `write_formula`, `clear_range`, `copy_range` |
| Format | `set_cell_style`, `merge_cells`, `set_conditional_format`, `set_data_validation` |
| Layout | `set_column_width`, `set_row_height`, `auto_fit_column`, `insert_rows`, `insert_columns`, `delete_rows`, `delete_columns` |
| Table | `sort_range`, `set_auto_filter` |
| Sheet | `create_sheet`, `switch_sheet`, `rename_sheet` |
| Diagnose | `detect_and_explain_errors` |
| Visual | `create_chart` |

Schemas live in `llm/tool_definitions.py`. The same definitions are sent to every provider — switching providers does not change the AI's capabilities.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│   PyQt5 Sidebar (ui/)                                    │
│   • chat widget   • settings dialog   • i18n / themes    │
└─────────────────────┬────────────────────────────────────┘
                      │ user prompt
┌─────────────────────▼────────────────────────────────────┐
│   LLM layer (llm/)                                       │
│   • base_provider  • openrouter / nvidia / gemini /      │
│     groq / ollama  • tool_definitions.TOOLS              │
│     (OpenAI-compatible function-calling schema)          │
└─────────────────────┬────────────────────────────────────┘
                      │ tool_calls[]
┌─────────────────────▼────────────────────────────────────┐
│   ToolDispatcher                                         │
│   routes each call to the right Core module              │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│   Core (core/)                                           │
│   • CellInspector   • CellManipulator                    │
│   • SheetAnalyzer   • ErrorDetector                      │
│   • LibreOfficeBridge (UNO socket / PyUNO)               │
└─────────────────────┬────────────────────────────────────┘
                      │
                ┌─────▼──────┐
                │ LibreOffice│
                │   Calc     │
                └────────────┘
```

The same code path is used by both the **standalone PyQt5 app** (`main.py`) and the **OXT add-on** packaged under `oxt/`.

---

## Installation

### Prerequisites
- Python **3.10+**
- LibreOffice **7.4+** (Calc)
- For the standalone app: PyQt5 + `httpx` + `python-dotenv` (see `requirements.txt`)
- For the OXT add-on: just LibreOffice — the bundle is self-contained.

### Option A — Standalone Python app

```bash
git clone https://github.com/palamut62/libre_calc_ai_addon.git
cd libre_calc_ai_addon

python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Start LibreOffice in socket mode so the assistant can connect:

```bash
# Linux / macOS
libreoffice --calc --accept="socket,host=localhost,port=2002;urp;"

# Windows
"C:\Program Files\LibreOffice\program\soffice.exe" --calc --accept="socket,host=127.0.0.1,port=2002;urp;"
```

Run the assistant:

```bash
python main.py
```

### Option B — Install as a LibreOffice extension (OXT)

```bash
cd oxt
./build_oxt.sh        # produces libre_calc_ai-<version>.oxt
```

Then in LibreOffice: **Tools → Extension Manager → Add…** and select the `.oxt` file. Restart LibreOffice. The assistant appears as a Calc sidebar button.

---

## Configuration

All settings persist to `~/.config/libre_calc_ai/settings.json` and can be edited from the in-app **Settings** dialog.

| Key | Description | Default |
|---|---|---|
| `llm_provider` | Active provider (`openrouter`, `ollama`, `gemini`, `groq`, `nvidia`) | `openrouter` |
| `openrouter_api_key` | OpenRouter key | _(empty)_ |
| `openrouter_default_model` | Default OpenRouter model | `google/gemini-2.5-flash` |
| `nvidia_api_key` | NVIDIA NIM key | _(empty)_ |
| `nvidia_default_model` | Default NVIDIA model | `nvidia/llama-3.3-nemotron-super-49b-v1` |
| `gemini_api_key` | Google Gemini key | _(empty)_ |
| `gemini_default_model` | Default Gemini model | `gemini-2.5-flash` |
| `groq_api_key` | Groq key | _(empty)_ |
| `groq_default_model` | Default Groq model | `llama-3.3-70b-versatile` |
| `ollama_base_url` | Ollama server URL | `http://localhost:11434` |
| `ollama_default_model` | Default Ollama model | `gemma4:31b-cloud` |
| `llm_temperature` | Sampling temperature | `0.1` |
| `llm_max_tokens` | Output token cap | `8192` |
| `libreoffice_host` / `libreoffice_port` | UNO socket | `localhost` / `2002` |
| `ui_theme` | `light`, `dark`, `system` | `light` |
| `ui_language` | `en`, `tr`, `system` | `en` |

API keys can also be supplied via `.env` (see `.env.example`) for headless / CI runs. UI-entered keys override `.env`.

---

## Usage

Open a Calc workbook and the assistant sidebar, then try prompts like:

- _"Sum column C and put the result in C100."_
- _"Format A1:D1 as a header row — bold, white text, dark blue background, centered."_
- _"Find every #DIV/0! error in the sheet and explain the cause."_
- _"Sort the table by Revenue descending."_
- _"Create a column chart of A1:B12 titled 'Q4 Sales' at F2."_
- _"What does cell H22 depend on?"_
- _"Add a drop-down to E2:E50 with values: Low, Medium, High."_
- _"Insert 3 empty rows above row 5."_

The model may chain multiple tool calls in one turn — e.g. write headers, fill values, apply styles, then reply with a summary.

---

## Testing

### Live LibreOffice smoke test
Connects to a running LibreOffice on `127.0.0.1:2002` and exercises 23 core operations end to end.

```powershell
# Windows
.\tests\run_smoke_against_running_lo.ps1 -LoHost 127.0.0.1 -Port 2002
```

### Full provider × tool matrix
Spins up a clean sheet for each provider, runs an LLM-driven scenario, and directly dispatches every remaining tool. Verifies `chat_completion`, `stream_completion`, `get_available_models`, and the full tool surface against real LibreOffice.

```powershell
$env:LO_TEST_HOST="127.0.0.1"; $env:LO_TEST_PORT="2002"
& "C:\Program Files\LibreOffice\program\python.exe" tests\full_provider_e2e.py
```

Latest run (NVIDIA + OpenRouter + Ollama with default models):

| Provider | list_models | streaming | chat | LLM scenario | Direct tool coverage |
|---|---|---|---|---|---|
| NVIDIA `nemotron-super-49b` | ✅ | ✅ | ✅ | 14/14 | 22/23 |
| OpenRouter `gemini-2.5-flash` | ✅ | ✅ | ✅ | 8/8 | 22/23 |
| Ollama `gemma4:31b-cloud` | ✅ | ✅ | ✅ | 14/14 | 22/23 |

The single coverage miss is `create_chart` when called with a single-column range and `has_header=true`; the schema now documents the ≥2-column requirement, and the production smoke test validates `create_chart` with proper inputs.

---

## Project Layout

```
libre_calc_ai_addon/
├── main.py                     # Standalone PyQt5 entry point
├── config/settings.py          # Singleton settings, schema versioning
├── core/
│   ├── uno_bridge.py           # LibreOffice socket / PyUNO bridge
│   ├── cell_inspector.py       # Reads
│   ├── cell_manipulator.py     # Writes / formatting / layout / charts
│   ├── sheet_analyzer.py       # Sheet-wide analysis
│   ├── error_detector.py       # #DIV/0! etc. with explanations
│   ├── address_utils.py        # A1 ↔ row/col helpers
│   └── event_listener.py       # Selection tracking
├── llm/
│   ├── base_provider.py        # Abstract LLMProvider
│   ├── openrouter_provider.py
│   ├── nvidia_provider.py
│   ├── gemini_provider.py
│   ├── groq_provider.py
│   ├── ollama_provider.py
│   ├── prompt_templates.py
│   └── tool_definitions.py     # 28 tools + ToolDispatcher
├── ui/                         # PyQt5 sidebar, settings, themes, i18n
├── oxt/                        # OXT extension package
│   ├── description.xml
│   ├── Addons.xcu
│   ├── CalcAI/                 # Extension entry points
│   └── build_oxt.sh
├── tests/
│   ├── libreoffice_smoke_test.py
│   ├── full_provider_e2e.py    # Provider × tool matrix
│   └── run_smoke_against_running_lo.ps1
├── requirements.txt
├── .env.example
└── README.md
```

---

## Troubleshooting

**`Couldn't connect to LibreOffice` on startup.**
LibreOffice must be running with `--accept="socket,host=...,port=2002;urp;"`. The standalone app does not start LibreOffice for you.

**Ollama answers "model not found".**
Run `ollama list` to see what's pulled, then either `ollama pull <model>` or pick an installed one in Settings.

**OpenRouter says model `X` is unavailable.**
Some OpenRouter models are gated, paid-only, or temporarily down. Pick another from the model dropdown in Settings; tool-calling-capable models are recommended.

**Tool calls succeed but cells stay empty.**
Check that the active sheet at the time of the call is the one the AI thinks it is. Use `list_sheets` / `switch_sheet` in your prompt, or ask the AI to confirm the current sheet first.

**Add-on icon missing after install.**
Restart LibreOffice fully (close *all* windows including the Quickstarter tray icon).

---

## Roadmap

- [ ] Pivot table tool
- [ ] Image-aware prompts (paste a screenshot of a sheet, get back a plan)
- [ ] Per-workbook memory (named ranges, business glossary)
- [ ] Macro recording → reusable AI playbooks
- [ ] More provider adapters (Anthropic native, Azure OpenAI, OpenAI native)

---

## Contributing

Pull requests welcome. Please:
1. Run the smoke + full provider tests against a live LibreOffice before opening a PR.
2. Keep tool schemas and dispatcher handlers in lock-step (parameter names must match).
3. Add a row to the test matrix for any new provider or tool.

---

## License

MIT — see [LICENSE](LICENSE).
