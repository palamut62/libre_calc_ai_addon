# LibreCalc AI Assistant

An intelligent, modern AI assistant sidebar for LibreOffice Calc, designed with the **Claude Code** aesthetic. This add-on allows you to chat with an AI utilizing data from your spreadsheets, analyze cells, and generate formulas, all within a sleek, professional interface.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![LibreOffice](https://img.shields.io/badge/LibreOffice-Calc-green)

## ✨ Features

### Core Features
*   **Modern & Streamlined UI**: A clean interface focusing purely on the chat experience.
*   **Multi-Language Support**: Full Turkish and English interface support with instant language switching.
*   **Theme Support**: Light, Dark, and System theme options.

### AI Providers
*   **OpenRouter (Cloud)**: Access to Claude, GPT, Gemini, Llama and 100+ models via API.
*   **Groq (Cloud)**: Ultra-fast inference via Groq API (e.g. `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`).
*   **NVIDIA NIM (Cloud)**: NVIDIA-hosted models via `integrate.api.nvidia.com` (e.g. `meta/llama-3.3-70b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`). Get your API key at [build.nvidia.com](https://build.nvidia.com).
*   **Gemini (Google)**: Google Gemini models via API.
*   **Ollama (Local)**: Run AI models locally for privacy and offline use.
    *   Automatic model fetching from Ollama server
    *   Tool support detection with visual warnings
    *   Fallback mode for models without tool support

### Spreadsheet Integration
*   **Live Selection Tracking**: The status bar instantly reflects your selection (`A1`, `A1:B5`, or `A1, C5`).
*   **Deep Integration via UNO**:
    *   Read/Write cell values & formulas
    *   Apply styles (Bold, Italic, Color, Font Size)
    *   Cell merging and unmerging
    *   Advanced borders and grid styles
    *   Text alignment and wrapping
    *   Analyze formulas and detect errors

### Visual Designer Mode
*   **Borders & Grids**: Create professional-looking tables
*   **Text Alignment**: Right-align numbers, center headers, wrap text
*   **Color Palettes**: Harmonious background and font colors
*   **Cell Merging**: Combine cells for headers and labels

## 🚀 Installation

### Prerequisites

*   Linux (Tested on Ubuntu/Debian based systems)
*   Python 3.10+
*   LibreOffice Calc
*   `python3-uno` package (Crucial for connection)

### Setup

1.  **Install System Dependencies:**

    ```bash
    sudo apt update
    sudo apt install libreoffice python3-uno python3-venv
    ```

    > **Note:** If you are using the Snap version of LibreOffice, it is highly recommended to switch to the `apt` version for better compatibility with external Python scripts.

2.  **Clone the Repository:**

    ```bash
    git clone https://github.com/palamut62/libre_calc_ai_addon.git
    cd libre_calc_ai_addon
    ```

3.  **Create Virtual Environment & Install Requirements:**

    ```bash
    # Create venv with access to system site-packages (needed for uno)
    python3 -m venv venv --system-site-packages

    # Activate
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt
    ```

4.  **Configuration:**

    Create a `.env` file in the root directory (optional - can also configure via Settings UI):

    ```env
    # Options: openrouter, ollama, gemini, groq, nvidia
    LLM_PROVIDER=openrouter

    # If using OpenRouter
    OPENROUTER_API_KEY=your_api_key_here

    # If using Ollama (local)
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_DEFAULT_MODEL=llama3.2
    ```

## 💡 Usage

### Option 1: Launch Both (Recommended for New Sessions)

```bash
./launch.sh                    # Opens LibreOffice + Assistant
./launch.sh my_spreadsheet.ods # Opens specific file + Assistant
```

### Option 2: Connect to Existing LibreOffice

If you already have LibreOffice open, you need to restart it in **socket mode**:

```bash
# Step 1: Close your current LibreOffice
# Step 2: Reopen it with socket listening enabled
libreoffice --calc --accept="socket,host=localhost,port=2002;urp;" your_file.ods

# Step 3: Run the assistant only
./connect.sh
```

### Option 3: Add Socket Mode to LibreOffice Startup

To always start LibreOffice with socket support, create an alias:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias localc='libreoffice --calc --accept="socket,host=localhost,port=2002;urp;"'

# Then use:
localc my_file.ods
./connect.sh
```

Or search for "LibreCalc AI Assistant" in your application menu.

### Option 4: OXT Extension (LibreOffice Add-on)

You can also install ArasAI as a native LibreOffice extension:

1. Build the extension: `cd oxt && bash build_oxt.sh`
2. Install the generated `.oxt` file via **Tools > Extension Manager** in LibreOffice
3. Restart LibreOffice
4. Open Calc and use the **AI Assistant** menu
5. If PyQt5/httpx/python-dotenv are missing, the extension offers automatic installation

### Settings

Access **File > Settings** to configure:

| Tab | Options |
|-----|---------|
| **AI (LLM)** | Provider selection, API keys, model selection, Ollama URL |
| **LibreOffice** | Connection host and port |
| **General** | Theme (Light/Dark/System), Language (TR/EN/System) |

### Ollama Setup

1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull a model: `ollama pull llama3.2`
3. In Settings, select "Ollama (Local)" and click "Fetch Models"

#### Tool-Supported Models

For full functionality (cell editing, formula writing), use models with tool/function calling support:

| Model | Tool Support |
|-------|-------------|
| `llama3.1`, `llama3.2`, `llama3.3` | ✅ Yes |
| `qwen2.5`, `qwen2` | ✅ Yes |
| `mistral` | ✅ Yes |
| `command-r` | ✅ Yes |
| `gemma3`, `phi3` | ❌ No (chat only) |

> Models without tool support will show a warning in Settings and can only be used for chat conversations.

### Example Capabilities

*   **Design**: "Create a monthly budget table with bold headers, blue background, and borders."
*   **Merge Cells**: "Merge cells A1:D1 and center the title."
*   **Formulas**: "Write a formula in C1 to sum A1 and B1."
*   **Analysis**: "What does the formula in D5 do? Explain it simply."
*   **Errors**: "Why is there a #DIV/0! error in column E?"

## Testing

For LibreOffice integration regression checks, use the smoke tests in `tests/`:

1. Start isolated headless LibreOffice, run full test suite, then close it:

   ```powershell
   powershell -ExecutionPolicy Bypass -File tests\run_lo_smoke.ps1
   ```

2. Run the same tests against an already-running LibreOffice listener (default `127.0.0.1:2002`):

   ```powershell
   powershell -ExecutionPolicy Bypass -File tests\run_smoke_against_running_lo.ps1 -LoHost 127.0.0.1 -Port 2002
   ```

3. Stability loop (run smoke test multiple times):

   ```powershell
   powershell -ExecutionPolicy Bypass -File tests\run_lo_smoke_loop.ps1 -Count 3
   ```

Latest local validation: `23/23 PASS`.

## 🔧 Architecture

```
libre_calc_ai_addon/
├── main.py              # Application entry point
├── launch.sh            # Smart launcher script
├── config/
│   └── settings.py      # Configuration management
├── core/
│   ├── cell_manipulator.py   # UNO cell operations
│   └── event_listener.py     # Selection tracking
├── llm/
│   ├── base_provider.py      # Abstract LLM interface
│   ├── openrouter_provider.py
│   ├── ollama_provider.py    # Local Ollama support
│   ├── tool_definitions.py   # Function calling schemas
│   └── prompt_templates.py
├── oxt/
│   ├── interface.py          # LibreOffice Script Provider bridge
│   └── CalcAI/              # Bundled application for OXT
└── ui/
    ├── main_window.py        # Main application window
    ├── chat_widget.py        # Chat interface
    ├── settings_dialog.py    # Settings UI
    ├── help_dialog.py        # Help & user guide dialog
    ├── styles.py             # Theme definitions
    └── i18n.py               # Translations (TR/EN)
```

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 👤 Developer

*   **GitHub**: [github.com/palamut62](https://github.com/palamut62)
*   **X (Twitter)**: [x.com/palamut62](https://x.com/palamut62)

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
