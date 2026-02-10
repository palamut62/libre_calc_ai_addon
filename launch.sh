#!/bin/bash
# LibreCalc AI Asistanı - Launcher
# LibreOffice Calc'ı dinleme modunda başlatır ve AI asistanını açar.
# Kullanım: ./launch.sh [dosya.ods]

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
    sleep 5
fi

# Virtual environment'ı aktive et
echo "AI Asistanı başlatılıyor..."
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
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
python main.py &
AI_PID=$!

echo ""
echo "LibreCalc AI Asistanı hazır!"
echo "  LibreOffice PID: ${LO_PID:-zaten çalışıyor}"
echo "  AI Asistanı PID: $AI_PID"
echo ""
echo "Kapatmak için her iki pencereyi de kapatın veya Ctrl+C yapın."

# AI süreci kapanana kadar bekle
wait $AI_PID 2>/dev/null
