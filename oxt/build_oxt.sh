#!/bin/bash
#
# LibreCalc AI - OXT Build Script
#
# Kullanim:
#   ./build_oxt.sh          # Normal build
#   ./build_oxt.sh --clean  # Temiz build
#   ./build_oxt.sh --install # Build ve kur
#

set -e

# Renkli cikti
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Proje dizini
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Surum bilgisi
VERSION="1.0.0"
NAME="libre_calc_ai"
OXT_FILE="${NAME}-${VERSION}.oxt"

# Build dizini
BUILD_DIR="build"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}LibreCalc AI - OXT Builder${NC}"
echo -e "${GREEN}Surum: ${VERSION}${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Temizlik parametresi
if [[ "$1" == "--clean" ]] || [[ "$1" == "-c" ]]; then
    echo -e "${YELLOW}Temizleniyor...${NC}"
    rm -rf "$BUILD_DIR"
    rm -f "$OXT_FILE"
    echo -e "${GREEN}Temizlik tamamlandi.${NC}"
    exit 0
fi

# Build dizinini olustur
echo -e "${YELLOW}Build dizini hazirlaniyor...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Dosyalari kopyala
echo -e "${YELLOW}Dosyalar kopyalaniyor...${NC}"

# META-INF
cp -r META-INF "$BUILD_DIR/"

# Ana dosyalar
cp description.xml "$BUILD_DIR/"
cp Addons.xcu "$BUILD_DIR/"

# Python paketi
# Python paketi (Scripts/python)
mkdir -p "$BUILD_DIR/Scripts/python"
cp interface.py "$BUILD_DIR/Scripts/python/"
cp parcel-descriptor.xml "$BUILD_DIR/Scripts/python/"


# CalcAI paketi - ana uygulamadan gercek kaynak dosyalari kopyala
MAIN_APP_DIR="$SCRIPT_DIR/.."
CALCAI_DIR="$BUILD_DIR/Scripts/python/CalcAI"
mkdir -p "$CALCAI_DIR"

# Ana modul dosyalari (gercek uygulama kaynaklarindan)
cp "$MAIN_APP_DIR/main.py" "$CALCAI_DIR/"
cp -r "$MAIN_APP_DIR/ui" "$CALCAI_DIR/"
cp -r "$MAIN_APP_DIR/core" "$CALCAI_DIR/"
cp -r "$MAIN_APP_DIR/llm" "$CALCAI_DIR/"
cp -r "$MAIN_APP_DIR/config" "$CALCAI_DIR/"

# OXT-ozel __init__.py (CalcAI paket init)
cp CalcAI/__init__.py "$CALCAI_DIR/"

# Assets (icons.py CalcAI/assets/icons/ yolunu bekler)
cp -r "$MAIN_APP_DIR/assets" "$CALCAI_DIR/"

# Aciklamalar
cp -r description "$BUILD_DIR/"

# Ikonlar
cp -r icons "$BUILD_DIR/"

# Assets
cp -r ../assets "$BUILD_DIR/"


# Gereksiz dosyalari temizle
echo -e "${YELLOW}Gereksiz dosyalar temizleniyor...${NC}"
find "$BUILD_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -name ".DS_Store" -delete 2>/dev/null || true
find "$BUILD_DIR" -name "*.orig" -delete 2>/dev/null || true

# OXT olustur (zip formatinda)
echo -e "${YELLOW}OXT paketi olusturuluyor...${NC}"
rm -f "$OXT_FILE"
cd "$BUILD_DIR"
zip -r "../$OXT_FILE" . -x "*.git*"
cd "$SCRIPT_DIR"

# Boyut bilgisi
SIZE=$(du -h "$OXT_FILE" | cut -f1)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build tamamlandi!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Dosya: ${YELLOW}${OXT_FILE}${NC}"
echo -e "Boyut: ${YELLOW}${SIZE}${NC}"
echo ""

# Kurulum parametresi
if [[ "$1" == "--install" ]] || [[ "$1" == "-i" ]]; then
    echo -e "${YELLOW}LibreOffice'e kuruluyor...${NC}"

    # Mevcut kurulumu kaldir
    unopkg remove "$NAME" 2>/dev/null || true

    # Yeni kurulum
    if unopkg add "$OXT_FILE"; then
        echo -e "${GREEN}Kurulum basarili!${NC}"
        echo -e "${YELLOW}LibreOffice'i yeniden baslatin.${NC}"
    else
        echo -e "${RED}Kurulum basarisiz!${NC}"
        exit 1
    fi
fi

echo ""
echo -e "Manuel kurulum icin:"
echo -e "  ${YELLOW}unopkg add ${OXT_FILE}${NC}"
echo ""
echo -e "Veya LibreOffice'de:"
echo -e "  ${YELLOW}Araclar > Eklenti Yoneticisi > Ekle${NC}"
echo ""
