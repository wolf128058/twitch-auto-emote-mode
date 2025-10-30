import requests
import json
import os
from dotenv import load_dotenv

# =================================================================
#                         KONFIGURATION
# =================================================================

# Lädt Variablen aus der .env-Datei (muss vor der Nutzung aufgerufen werden)
load_dotenv()

# 1. Deine Twitch Client ID (aus der Twitch Developer Console)
CLIENT_ID = os.getenv("CLIENT_ID")

# 2. Dein User Access Token (dein Moderator-Token mit den Scopes)
#    Dieser muss die Berechtigung 'moderator:manage:chat_settings' haben!
MODERATOR_TOKEN = os.getenv("MODERATOR_TOKEN")

# 3. Die numerische User ID des Streamers (Broadcaster)
BROADCASTER_ID = os.getenv("BROADCASTER_ID")

# 4. Deine numerische User ID (als Moderator)
MODERATOR_ID = os.getenv("MODERATOR_ID")


# =================================================================
#                         HELPER FUNKTIONEN
# =================================================================

def get_headers(token):
    """Gibt die notwendigen HTTP-Header für die Twitch API zurück."""
    return {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def is_stream_live(broadcaster_id):
    """Prüft, ob der Broadcaster online ist."""
    url = f"https://api.twitch.tv/helix/streams?user_id={broadcaster_id}"
    headers = get_headers(MODERATOR_TOKEN)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Löst einen Fehler bei 4xx/5xx Status aus
        data = response.json()

        # Wenn 'data' einen Eintrag enthält, ist der Stream live
        return len(data.get('data', [])) > 0

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen des Stream-Status: {e}")
        return False


def set_emote_only_mode(broadcaster_id, moderator_id, enable=True):
    """Setzt den Emote-Only Modus für den Chat (ein oder aus)."""

    # Twitch API Endpunkt zum Ändern der Chat-Einstellungen
    url = f"https://api.twitch.tv/helix/chat/settings?broadcaster_id={broadcaster_id}&moderator_id={moderator_id}"
    headers = get_headers(MODERATOR_TOKEN)

    # Body des Requests: setzt 'emote_mode' auf 'True' oder 'False'
    payload = {
        "emote_mode": enable
    }

    try:
        response = requests.patch(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        mode = "aktiviert" if enable else "deaktiviert"
        print(f"✅ Emote-Only Modus erfolgreich {mode}.")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Fehler beim Setzen des Emote-Only Modus: {e}")
        print(f"   Antwort: {response.text}")
        print(
            "   Stelle sicher, dass dein Moderator Token aktuell ist und den Scope 'moderator:manage:chat_settings' hat!")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Fehler beim Setzen des Emote-Only Modus: {e}")
        return False


# =================================================================
#                            HAUPT-LOGIK
# =================================================================

def main():
    """Prüft den Stream-Status und setzt den Emote-Only Modus, falls offline."""

    # Prüfe, ob die notwendigen Variablen geladen wurden
    if not all([CLIENT_ID, MODERATOR_TOKEN, BROADCASTER_ID, MODERATOR_ID]):
        print("⚠️ Konfigurationsfehler: Nicht alle Variablen konnten aus der .env-Datei geladen werden.")
        print("   Bitte überprüfe die .env-Datei.")
        return

    print("Überprüfe Stream-Status...")
    if is_stream_live(BROADCASTER_ID):
        print("🟢 Streamer ist LIVE. Emote-Only Modus wird DEAKTIVIERT (falls er an war).")
        # Optional: Den Modus deaktivieren, wenn der Streamer live ist
        set_emote_only_mode(BROADCASTER_ID, MODERATOR_ID, enable=False)
    else:
        print("🔴 Streamer ist OFFLINE. Emote-Only Modus wird AKTIVIERT.")
        # Setzt den Modus auf Emote-Only
        set_emote_only_mode(BROADCASTER_ID, MODERATOR_ID, enable=True)


if __name__ == "__main__":
    main()