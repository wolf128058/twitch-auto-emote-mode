#!/bin/bash

# Farben für bessere Lesbarkeit
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Auto-Emote Starter ===${NC}"

# Verzeichnis des Scripts ermitteln
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Name des Virtual Environments
VENV_DIR="venv"

# Prüfen, ob python3-venv installiert ist
if ! dpkg -l | grep -q python3.*-venv 2>/dev/null; then
    echo -e "${RED}❌ python3-venv ist nicht installiert!${NC}"
    echo -e "${YELLOW}Bitte installiere es mit:${NC}"
    echo -e "  ${GREEN}sudo apt install python3.12-venv${NC}"
    echo ""
    echo -e "${YELLOW}Oder für die Standard-Python-Version:${NC}"
    echo -e "  ${GREEN}sudo apt install python3-venv${NC}"
    exit 1
fi

# Prüfen, ob Virtual Environment existiert und funktionsfähig ist
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${YELLOW}Virtual Environment nicht gefunden oder unvollständig. Erstelle neues Environment...${NC}"

    # Altes, fehlerhaftes venv-Verzeichnis löschen
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
    fi

    python3 -m venv "$VENV_DIR"

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Fehler beim Erstellen des Virtual Environments${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Virtual Environment erstellt${NC}"
fi

# Virtual Environment aktivieren
echo -e "${YELLOW}Aktiviere Virtual Environment...${NC}"
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Fehler beim Aktivieren des Virtual Environments${NC}"
    exit 1
fi

# Dependencies installieren (falls requirements.txt existiert)
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installiere Dependencies...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installiert${NC}"
fi

# python-dotenv hinzufügen (wird von main.py benötigt)
pip install -q python-dotenv

# Prüfen, ob .env-Datei existiert
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warnung: .env-Datei nicht gefunden!${NC}"
    echo -e "${YELLOW}   Bitte erstelle eine .env-Datei basierend auf .env-example${NC}"
fi

# main.py starten
echo -e "${GREEN}Starte main.py...${NC}"
echo ""
python3 main.py

# Exit-Code speichern
EXIT_CODE=$?

# Virtual Environment deaktivieren
deactivate

exit $EXIT_CODE