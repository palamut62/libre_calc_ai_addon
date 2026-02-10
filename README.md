# LibreCalc AI Assistant

An intelligent, modern AI assistant sidebar for LibreOffice Calc, designed with the **Claude Code** aesthetic. This add-on allows you to chat with an AI utilizing data from your spreadsheets, analyze cells, and generate formulas, all within a sleek, professional interface.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![LibreOffice](https://img.shields.io/badge/LibreOffice-Calc-green)

## Features

*   **Modern UI**: Clean, professional interface inspired by Anthropic's Claude, featuring a dark theme, rust-orange accents, and a "Prompt Box" style input.
*   **Deep Integration**: Connects directly to LibreOffice Calc via UNO.
    *   Read/Write cell values.
    *   Analyze formulas and dependencies (Precedents/Dependents).
    *   Detect errors.
*   **AI-Powered**: Supports multiple LLM providers (OpenRouter, Ollama) to assist with:
    *   Explaining complex formulas.
    *   Generating data analysis.
    *   Automating spreadsheet tasks.
*   **Smart Launcher**: Automatically handles connection to LibreOffice (supports both `apt` and `snap` installations).

## Installation

### Prerequisites

*   Linux (Tested on Ubuntu/Debian based systems)
*   Python 3.8+
*   LibreOffice Calc
*   `python3-uno` package (Crucial for connection)

### Setup

1.  **Install System Dependencies:**

    ```bash
    sudo apt update
    sudo apt install libreoffice python3-uno python3-venv
    ```

    *> **Note:** If you are using the Snap version of LibreOffice, it is highly recommended to switch to the `apt` version for better compatibility with external Python scripts.*

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

    Create a `.env` file in the root directory:

    ```env
    # Options: openrouter, ollama
    LLM_PROVIDER=openrouter
    
    # If using OpenRouter
    OPENROUTER_API_KEY=your_api_key_here
    
    # If using Ollama
    OLLAMA_BASE_URL=http://localhost:11434
    ```

## Usage

The easiest way to run the assistant is using the included launcher script. It will automatically start LibreOffice in listening mode and launch the AI sidebar.

```bash
./launch.sh
```

Or, if you installed the desktop shortcut:
1.  Search for "LibreCalc AI Assistant" in your application menu.
2.  Launch it.

## How it Works

The application uses the **UNO (Universal Network Objects)** bridge to communicate with a running LibreOffice instance.
*   **`launch.sh`**: Sets up the environment (PYTHONPATH) and ensures LibreOffice is started with `--accept="socket,host=localhost,port=2002;urp;"`.
*   **`main.py`**: The entry point for the PyQt5 application.
*   **`core/`**: Contains the logic for UNO communication, cell inspection, and manipulation.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
