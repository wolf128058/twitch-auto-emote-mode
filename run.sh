#!/bin/bash

# Farben für bessere Lesbarkeit in der manuellen Ausführung
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Twitch Mod Skript Starter ===${NC}"

# Verzeichnis des Scripts ermitteln
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Name des Virtual Environments
VENV_DIR="venv"
PYTHON_BIN="$VENV_DIR/bin/python"

# --- FUNKTION: PRÜFEN UND SETUP DURCHFÜHREN ---
setup_if_needed() {
    # >> Prüfen, ob python3-venv installiert ist (nur bei Cronjobs schwer zu prüfen)
    # Wir überspringen diese OS-Prüfung, da sie in Cronjobs oft fehlschlägt oder unnötig ist.
    
    # >> Prüfen, ob Virtual Environment existiert
    if [ ! -f "$PYTHON_BIN" ]; then
        echo -e "${YELLOW}Virtual Environment nicht gefunden. Führe vollständiges Setup durch...${NC}"

        # Altes, fehlerhaftes venv-Verzeichnis löschen (optional, aber sicher)
        if [ -d "$VENV_DIR" ]; then
            rm -rf "$VENV_DIR"
        fi

        # VENV erstellen
        python3 -m venv "$VENV_DIR"

        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Fehler beim Erstellen des Virtual Environments.${NC}"
            echo -e "${YELLOW}Stelle sicher, dass 'python3' und 'python3-venv' installiert sind.${NC}"
            exit 1
        fi

        # VENV aktivieren, um Installation durchzuführen
        source "$VENV_DIR/bin/activate"

        # Dependencies installieren
        if [ -f "requirements.txt" ]; then
            echo -e "${YELLOW}Installiere Dependencies...${NC}"
            pip install -q --upgrade pip
            pip install -q -r requirements.txt
            echo -e "${GREEN}✓ Dependencies installiert${NC}"
        else
            echo -e "${YELLOW}Warnung: requirements.txt nicht gefunden. Installiere nur python-dotenv.${NC}"
            pip install -q python-dotenv
        fi
        
        # VENV deaktivieren
        deactivate
        echo -e "${GREEN}✓ Setup abgeschlossen.${NC}"
    
    else
        # VENV existiert, keine Installation nötig, nur schneller Check
        if [ -f "requirements.txt" ] && [ ! -f "$VENV_DIR/.installed" ]; then
            echo -e "${YELLOW}VENV existiert, aber Dependencies wurden noch nicht vollständig installiert. Installiere nach...${NC}"
            source "$VENV_DIR/bin/activate"
            pip install -q --upgrade pip
            pip install -q -r requirements.txt
            touch "$VENV_DIR/.installed" # Marker setzen
            deactivate
            echo -e "${GREEN}✓ Dependencies nachinstalliert.${NC}"
        fi
    fi
}
# --- ENDE SETUP FUNKTION ---

# >> Führe Setup nur aus, wenn nötig (sehr schneller Check, wenn venv existiert)
setup_if_needed

# >> Finaler Check: VENV-Aktivierungsskript muss existieren
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${RED}❌ Kritischer Fehler: VENV konnte nicht erstellt oder gefunden werden. Abbruch.${NC}"
    exit 1
fi

# >> Virtual Environment aktivieren für den Hauptlauf
echo -e "${YELLOW}Aktiviere Virtual Environment...${NC}"
source "$VENV_DIR/bin/activate"

# >> Prüfen, ob .env-Datei existiert
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warnung: .env-Datei nicht gefunden!${NC}"
    echo -e "${YELLOW}   Bitte erstelle eine .env-Datei basierend auf .env-example${NC}"
fi

# >> main.py starten
echo -e "${GREEN}Starte main.py (Mod-Logik)...${NC}"
python main.py

# >> Exit-Code speichern
EXIT_CODE=$?

# >> Virtual Environment deaktivieren
deactivate

echo -e "${GREEN}=== Skript beendet mit Code ${EXIT_CODE} ===${NC}"

exit $EXIT_CODE