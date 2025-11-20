#!/usr/bin/env python3
import os
import sys
import argparse
import requests
from dotenv import load_dotenv, set_key
import json

def check_token_scopes(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://id.twitch.tv/oauth2/validate", headers=headers)
    if response.status_code == 200:
        print("✅ Aktive Scopes:", response.json().get("scopes", []))
    elif resp.status_code == 401:
        print('⚠️  Token abgelaufen oder ungültig. Versuche zu erneuern...')
        refresh_access_token()
        env = load_env()
        send_chat_message(broadcaster_id, message, env)
    else:
        print("⚠️ Konnte Token-Scopes nicht prüfen:", response.text)

def refresh_access_token():
    from dotenv import set_key
    print("🔄 Versuche Token zu erneuern...")
    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("REFRESH_TOKEN"),
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET")
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        # Update .env file
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        set_key(dotenv_path, "MODERATOR_TOKEN", access_token)
        set_key(dotenv_path, "REFRESH_TOKEN", refresh_token)
        os.environ["MODERATOR_TOKEN"] = access_token
        os.environ["REFRESH_TOKEN"] = refresh_token
        print("✅ Token erfolgreich erneuert.")
        check_token_scopes(access_token)
        return access_token
    elif resp.status_code == 401:
        print('⚠️  Token abgelaufen oder ungültig. Versuche zu erneuern...')
        refresh_access_token()
        env = load_env()
        send_chat_message(broadcaster_id, message, env)
    else:
        print("❌ Fehler beim Token-Refresh:", response.text)
        sys.exit(1)


def load_env():
    load_dotenv()
    return {
        "CLIENT_ID": os.getenv("CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("CLIENT_SECRET"),
        "MODERATOR_ID": os.getenv("MODERATOR_ID"),
        "MODERATOR_TOKEN": os.getenv("MODERATOR_TOKEN"),
    }

def get_broadcaster_id(channel_name, env):
    """Hole broadcaster_id über den Kanalnamen"""
    headers = {
        "Client-ID": env["CLIENT_ID"],
        "Authorization": f"Bearer {env['MODERATOR_TOKEN']}"
    }
    url = "https://api.twitch.tv/helix/users"
    params = {"login": channel_name}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()["data"]
    if not data:
        print(f"❌ Kanal '{channel_name}' nicht gefunden.")
        sys.exit(1)
    return data[0]["id"]

def send_chat_message(broadcaster_id, message, env):
    """Sendet Nachricht in den Twitch-Chat"""
    url = "https://api.twitch.tv/helix/chat/messages"
    headers = {
        "Client-ID": env["CLIENT_ID"],
        "Authorization": f"Bearer {env['MODERATOR_TOKEN']}",
        "Content-Type": "application/json"
    }
    json = {
        "broadcaster_id": broadcaster_id,
        "sender_id": env["MODERATOR_ID"],
        "message": message
    }
    resp = requests.post(url, headers=headers, json=json)
    if resp.status_code == 200:
        print("✅ Nachricht gesendet.")
    elif resp.status_code == 401:
        print('⚠️  Token abgelaufen oder ungültig. Versuche zu erneuern...')
        refresh_access_token()
        env = load_env()
        send_chat_message(broadcaster_id, message, env)
    else:
        print(f"❌ Fehler beim Senden: {resp.status_code}")
        print(resp.text)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Sende eine Nachricht in einen Twitch-Chat.")
    parser.add_argument("-c", "--channel", required=True, help="Klartextname des Kanals (z. B. 'montanablack')")
    parser.add_argument("-m", "--message", required=True, help="Nachricht, die gesendet werden soll")
    args = parser.parse_args()

    env = load_env()
    broadcaster_id = get_broadcaster_id(args.channel, env)
    send_chat_message(broadcaster_id, args.message, env)

if __name__ == "__main__":
    main()
