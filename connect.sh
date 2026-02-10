#!/bin/bash
# LibreCalc AI Asistanı - Mevcut LibreOffice'e Bağlan
# Zaten açık olan LibreOffice Calc'a bağlanır.
#
# ÖNEMLİ: LibreOffice'in socket modunda başlatılmış olması gerekir:
#   libreoffice --calc --accept="socket,host=localhost,port=2002;urp;" dosya.ods
#
# Kullanım: ./connect.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LO_PORT=2002

echo "============================================"
echo "  LibreCalc AI Asistanı - Bağlantı Modu"
echo "============================================"
echo ""

# LibreOffice çalışıyor mu kontrol et
if ! pgrep -f "soffice" > /dev/null 2>&1; then
    echo "UYARI: LibreOffice çalışmıyor!"
    echo ""
    echo "Lütfen önce LibreOffice'i socket modunda başlatın:"
    echo "  libreoffice --calc --accept=\"socket,host=localhost,port=$LO_PORT;urp;\" dosyaniz.ods"
    echo ""
    echo "Veya ./launch.sh kullanarak hem LibreOffice'i hem asistanı başlatın."
    exit 1
fi

# Socket portu dinleniyor mu kontrol et
if ! ss -tlnp 2>/dev/null | grep -q ":$LO_PORT" && ! netstat -tlnp 2>/dev/null | grep -q ":$LO_PORT"; then
    echo "UYARI: LibreOffice çalışıyor ama port $LO_PORT dinlenmiyor!"
    echo ""
    echo "LibreOffice socket modunda başlatılmamış olabilir."
    echo "LibreOffice'i kapatıp şu komutla yeniden başlatın:"
    echo "  libreoffice --calc --accept=\"socket,host=localhost,port=$LO_PORT;urp;\" dosyaniz.ods"
    echo ""
    read -p "Yine de devam etmek ister misiniz? (e/H): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ee]$ ]]; then
        exit 1
    fi
fi

# Virtual environment'ı aktive et
echo "AI Asistanı başlatılıyor..."
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

# UNO Python yolunu PYTHONPATH'e ekle
UNO_PATHS="/usr/lib/python3/dist-packages"
if [ -d "/usr/lib/libreoffice/program" ]; then
    UNO_PATHS="$UNO_PATHS:/usr/lib/libreoffice/program"
fi
export PYTHONPATH="$UNO_PATHS${PYTHONPATH:+:$PYTHONPATH}"

# Socket bağlantısı kullan
export LO_CONNECT_TYPE="socket"

cd "$SCRIPT_DIR"
python main.py

echo ""
echo "Asistan kapatıldı."
