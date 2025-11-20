#!/usr/bin/env python3
import os
import sys
import argparse
import requests
from dotenv import load_dotenv

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
