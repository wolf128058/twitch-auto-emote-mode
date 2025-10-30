import requests
import json
import os
from dotenv import load_dotenv, set_key

# =================================================================
#                         KONFIGURATION
# =================================================================

# Lädt Variablen aus der .env-Datei
load_dotenv()

# Variablen aus der .env-Datei
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
MODERATOR_TOKEN = os.getenv("MODERATOR_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
BROADCASTER_ID = os.getenv("BROADCASTER_ID")

# 4. Deine numerische User ID (als Moderator)
MODERATOR_ID = os.getenv("MODERATOR_ID")

# Dateipfad zur .env-Datei
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '.env')


# =================================================================
#                         TOKEN REFRESH FUNKTION
# =================================================================

def refresh_access_token():
    """Fordert mit dem Refresh Token einen neuen Access Token von Twitch an."""
    global MODERATOR_TOKEN, REFRESH_TOKEN

    print("🔄 Access Token abgelaufen oder fehlt. Versuche zu erneuern...")

    url = "https://id.twitch.tv/oauth2/token"

    # Body des POST Requests zur Token-Erneuerung
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()

        data = response.json()

        # Neue Tokens speichern
        new_access_token = data.get("access_token")
        new_refresh_token = data.get("refresh_token", REFRESH_TOKEN)

        if new_access_token:
            # Globale Variablen aktualisieren
            MODERATOR_TOKEN = new_access_token
            REFRESH_TOKEN = new_refresh_token

            # Neue Tokens in der .env-Datei speichern
            set_key(DOTENV_PATH, "MODERATOR_TOKEN", MODERATOR_TOKEN)
            set_key(DOTENV_PATH, "REFRESH_TOKEN", REFRESH_TOKEN)

            print("✅ Access Token erfolgreich erneuert und gespeichert.")
            return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Fehler beim Erneuern des Tokens: {e}")
        print("   Bitte überprüfe CLIENT_SECRET und REFRESH_TOKEN.")
        return False


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

    # NEU: Überprüfung, ob Token gültig ist, und automatische Erneuerung
    if not MODERATOR_TOKEN:
        if not refresh_access_token():
            return False

    headers = get_headers(MODERATOR_TOKEN)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Löst einen Fehler bei 4xx/5xx Status aus
        data = response.json()

        # Twitch gibt bei 401 (Unauthorized) KEINEN Fehler, sondern manchmal nur { "status": 401 }
        if response.status_code == 401:
            raise requests.exceptions.HTTPError("401 Client Error: Unauthorized")

        # Wenn 'data' einen Eintrag enthält, ist der Stream live
        return len(data.get('data', [])) > 0

    except requests.exceptions.HTTPError as e:
        # Fängt den 401-Fehler ab, versucht Token zu erneuern und den Aufruf zu wiederholen
        if response.status_code == 401:
            print("⚠️ 401 (Unauthorized) beim Stream-Check. Token möglicherweise abgelaufen.")
            if refresh_access_token():
                # Erfolgreich erneuert: Wiederhole den API-Call (Rekursion)
                return is_stream_live(broadcaster_id)
            else:
                return False
        else:
            print(f"Fehler beim Abrufen des Stream-Status: {e}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen des Stream-Status: {e}")
        return False


def set_emote_only_mode(broadcaster_id, moderator_id, enable=True):
    """Setzt den Emote-Only Modus für den Chat (ein oder aus)."""

    # NEU: Überprüfung, ob Token gültig ist, und automatische Erneuerung
    if not MODERATOR_TOKEN:
        if not refresh_access_token():
            return False

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
        # Fängt den 401-Fehler ab, versucht Token zu erneuern und den Aufruf zu wiederholen
        if response.status_code == 401:
            print("⚠️ 401 (Unauthorized) beim Chat-Update. Token möglicherweise abgelaufen.")
            if refresh_access_token():
                # Erfolgreich erneuert: Wiederhole den API-Call (Rekursion)
                return set_emote_only_mode(broadcaster_id, moderator_id, enable)
            else:
                return False
        else:
            print(f"❌ HTTP Fehler beim Setzen des Emote-Only Modus: {e}")
            print(f"   Antwort: {response.text}")
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
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, BROADCASTER_ID, MODERATOR_ID]):
        print(
            "⚠️ Konfigurationsfehler: Nicht alle notwendigen API-Variablen (CLIENT_SECRET, REFRESH_TOKEN) konnten aus der .env-Datei geladen werden.")
        print("   Bitte überprüfe die .env-Datei und führe den Initial-Login-Flow durch.")
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