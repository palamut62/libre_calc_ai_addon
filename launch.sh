#!/bin/bash
# LibreCalc AI Asistanı - Launcher
# LibreOffice Calc'ı dinleme modunda başlatır ve AI asistanını açar.
# Kullanım: ./launch.sh [dosya.ods]

LOG="$HOME/.librecalc_ai_launcher.log"
exec >>"$LOG" 2>&1
echo "=== $(date) ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LO_PORT=2002

# LibreOffice zaten çalışıyor mu kontrol et
LO_RUNNING=false
if pgrep -f "soffice" > /dev/null 2>&1; then
    LO_RUNNING=true
    echo "LibreOffice zaten çalışıyor."
fi

# LibreOffice'i arka planda başlat (dinleme modu ile)
if [ "$LO_RUNNING" = false ]; then
    echo "LibreOffice Calc başlatılıyor (port: $LO_PORT)..."
    if [ -n "$1" ]; then
        libreoffice --calc --accept="socket,host=localhost,port=$LO_PORT;urp;" "$1" &
    else
        libreoffice --calc --accept="socket,host=localhost,port=$LO_PORT;urp;" &
    fi
    LO_PID=$!

    echo "LibreOffice hazırlanıyor..."
    sleep 3
fi

# LibreOffice zaten çalışıyorsa da görünür bir Calc belgesi açmayı zorla.
# Aksi halde arka planda çalışan soffice süreci varken kullanıcı pencere göremeyebilir.
if [ "$LO_RUNNING" = true ]; then
    echo "Mevcut LibreOffice oturumunda Calc belgesi açılıyor..."
    if [ -n "$1" ]; then
        libreoffice --calc "$1" &
    else
        libreoffice --calc &
    fi
    echo "Calc belgesi hazırlanıyor..."
    sleep 2
fi

# Virtual environment'ı aktive et
echo "AI Asistanı başlatılıyor..."
PY_BIN=""
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    if [ -x "$VENV_DIR/bin/python" ]; then
        PY_BIN="$VENV_DIR/bin/python"
    fi
fi

if [ -z "$PY_BIN" ]; then
    PY_BIN="$(command -v python3)"
fi
if [ -z "$PY_BIN" ]; then
    PY_BIN="$(command -v python)"
fi

# UNO Python yolunu PYTHONPATH'e ekle (venv sistem paketlerini göremez)
UNO_PATHS="/usr/lib/python3/dist-packages"
if [ -d "/usr/lib/libreoffice/program" ]; then
    UNO_PATHS="$UNO_PATHS:/usr/lib/libreoffice/program"
fi
export PYTHONPATH="$UNO_PATHS${PYTHONPATH:+:$PYTHONPATH}"
echo "UNO yolu ayarlandı: $UNO_PATHS"

# Socket bağlantısı kullan (apt LibreOffice)
export LO_CONNECT_TYPE="socket"

cd "$SCRIPT_DIR"
if [ -z "$PY_BIN" ]; then
    echo "Python bulunamadı. Lütfen python3 yükleyin."
    exit 1
fi
$PY_BIN main.py &
AI_PID=$!

echo ""
echo "Aras Asistan hazır!"
echo "  LibreOffice PID: ${LO_PID:-zaten çalışıyor}"
echo "  AI Asistanı PID: $AI_PID"
echo ""
echo "Kapatmak için her iki pencereyi de kapatın veya Ctrl+C yapın."

# AI süreci kapanana kadar bekle
wait $AI_PID 2>/dev/null
