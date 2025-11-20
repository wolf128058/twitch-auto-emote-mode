#!/bin/bash

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Twitch say.py Starter ===${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
PYTHON_BIN="$VENV_DIR/bin/python"

setup_if_needed() {
    if [ ! -f "$PYTHON_BIN" ]; then
        echo -e "${YELLOW}Virtual Environment wird eingerichtet...${NC}"
        [ -d "$VENV_DIR" ] && rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR" || {
            echo -e "${RED}❌ Fehler beim Erstellen des Virtual Environments.${NC}"
            exit 1
        }
        source "$VENV_DIR/bin/activate"
        if [ -f "requirements.txt" ]; then
            pip install -q --upgrade pip
            pip install -q -r requirements.txt
        else
            pip install -q python-dotenv requests
        fi
        deactivate
    fi
}

setup_if_needed

# Aktivieren
source "$VENV_DIR/bin/activate"

# Warnung wenn .env fehlt
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env-Datei nicht gefunden! Bitte erstellen.${NC}"
fi

# Parameter an say.py durchreichen
echo -e "${GREEN}Starte say.py mit Parametern: $@${NC}"
python say.py "$@"
EXIT_CODE=$?

# Deaktivieren
deactivate

echo -e "${GREEN}=== say.py beendet mit Code ${EXIT_CODE} ===${NC}"
exit $EXIT_CODE
