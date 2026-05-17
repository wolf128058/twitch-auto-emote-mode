#!/usr/bin/env python3
import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key


API_BASE = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
DEFAULT_CHANNEL = "xyz"
REQUIRED_SCOPE = "moderator:manage:suspicious_users"

SCRIPT_DIR = Path(__file__).resolve().parent
DOTENV_PATH = SCRIPT_DIR / ".env"


def load_env():
    load_dotenv(DOTENV_PATH)
    env = {
        "CLIENT_ID": os.getenv("CLIENT_ID"),
        "CLIENT_SECRET": os.getenv("CLIENT_SECRET"),
        "MODERATOR_ID": os.getenv("MODERATOR_ID"),
        "MODERATOR_TOKEN": os.getenv("MODERATOR_TOKEN"),
        "REFRESH_TOKEN": os.getenv("REFRESH_TOKEN"),
    }
    missing = [key for key, value in env.items() if not value]
    if missing:
        print("Config fehlt in .env: " + ", ".join(missing), file=sys.stderr)
        sys.exit(2)
    return env


def save_token(env, access_token, refresh_token=None):
    env["MODERATOR_TOKEN"] = access_token
    os.environ["MODERATOR_TOKEN"] = access_token
    set_key(str(DOTENV_PATH), "MODERATOR_TOKEN", access_token)

    if refresh_token:
        env["REFRESH_TOKEN"] = refresh_token
        os.environ["REFRESH_TOKEN"] = refresh_token
        set_key(str(DOTENV_PATH), "REFRESH_TOKEN", refresh_token)


def refresh_access_token(env):
    print("Token abgelaufen oder ungueltig. Erneuere Access Token...")
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": env["REFRESH_TOKEN"],
        "client_id": env["CLIENT_ID"],
        "client_secret": env["CLIENT_SECRET"],
    }
    response = requests.post(TOKEN_URL, data=payload, timeout=20)
    if response.status_code != 200:
        print("Token-Refresh fehlgeschlagen:", response.text, file=sys.stderr)
        sys.exit(1)

    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        print("Token-Refresh lieferte keinen access_token.", file=sys.stderr)
        sys.exit(1)

    save_token(env, access_token, data.get("refresh_token"))
    print("Token erneuert und in .env gespeichert.")


def headers(env):
    return {
        "Client-ID": env["CLIENT_ID"],
        "Authorization": f"Bearer {env['MODERATOR_TOKEN']}",
    }


def twitch_request(env, method, path, *, retry=True, **kwargs):
    request_headers = headers(env)
    if "json" in kwargs:
        request_headers["Content-Type"] = "application/json"
    request_headers.update(kwargs.pop("headers", {}))

    response = requests.request(
        method,
        f"{API_BASE}{path}",
        headers=request_headers,
        timeout=20,
        **kwargs,
    )
    if response.status_code == 401 and retry:
        refresh_access_token(env)
        return twitch_request(env, method, path, retry=False, **kwargs)
    return response


def validate_scope(env):
    response = requests.get(
        VALIDATE_URL,
        headers={"Authorization": f"Bearer {env['MODERATOR_TOKEN']}"},
        timeout=20,
    )
    if response.status_code == 401:
        refresh_access_token(env)
        response = requests.get(
            VALIDATE_URL,
            headers={"Authorization": f"Bearer {env['MODERATOR_TOKEN']}"},
            timeout=20,
        )

    if response.status_code != 200:
        print("Konnte Token nicht validieren:", response.text, file=sys.stderr)
        return

    scopes = response.json().get("scopes", [])
    if REQUIRED_SCOPE not in scopes:
        print(
            f"Warnung: Token hat Scope '{REQUIRED_SCOPE}' nicht. "
            "Der API-Aufruf wird wahrscheinlich mit 401 fehlschlagen.",
            file=sys.stderr,
        )


def normalize_login(name):
    return name.strip().lstrip("@").lower()


def load_usernames(args):
    names = [normalize_login(name) for name in args.usernames]
    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            for line in handle:
                clean = normalize_login(line.split("#", 1)[0])
                if clean:
                    names.append(clean)

    seen = set()
    unique = []
    for name in names:
        if name and name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def get_users_by_login(env, logins):
    found = {}
    for offset in range(0, len(logins), 100):
        chunk = logins[offset : offset + 100]
        params = [("login", login) for login in chunk]
        response = twitch_request(env, "GET", "/users", params=params)
        if response.status_code != 200:
            print("Fehler beim Aufloesen von Usernamen:", response.text, file=sys.stderr)
            sys.exit(1)

        for user in response.json().get("data", []):
            found[user["login"].lower()] = user
    return found


def apply_suspicious_status(env, broadcaster_id, user_id, status):
    params = {
        "broadcaster_id": broadcaster_id,
        "moderator_id": env["MODERATOR_ID"],
    }
    payload = {"user_id": user_id, "status": status}
    return twitch_request(env, "POST", "/moderation/suspicious_users", params=params, json=payload)


def remove_suspicious_status(env, broadcaster_id, user_id):
    params = {
        "broadcaster_id": broadcaster_id,
        "moderator_id": env["MODERATOR_ID"],
        "user_id": user_id,
    }
    return twitch_request(env, "DELETE", "/moderation/suspicious_users", params=params)


def print_api_error(action, login, response):
    print(f"FEHLER {action} fuer {login}: HTTP {response.status_code}", file=sys.stderr)
    if response.text:
        print(response.text, file=sys.stderr)


def wait_seconds_from_rate_limit(response, fallback):
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass
    return fallback


def run_update_with_retries(env, args, broadcaster_id, user):
    for attempt in range(args.max_retries + 1):
        if args.remove:
            response = remove_suspicious_status(env, broadcaster_id, user["id"])
        else:
            response = apply_suspicious_status(env, broadcaster_id, user["id"], args.status)

        if response.status_code != 429:
            return response

        if attempt >= args.max_retries:
            return response

        wait_seconds = wait_seconds_from_rate_limit(response, args.rate_limit_delay)
        print(
            f"Rate limit erreicht bei {user['login']}. "
            f"Warte {wait_seconds:.1f}s und versuche erneut..."
        )
        time.sleep(wait_seconds)

    return response


def main():
    parser = argparse.ArgumentParser(
        description="Setzt Twitch-User im Channel auf Restricted/Monitoring oder entfernt den Status."
    )
    parser.add_argument("usernames", nargs="*", help="Twitch-Usernamen, optional mit @")
    parser.add_argument(
        "-f",
        "--file",
        help="Datei mit einem Usernamen pro Zeile. Kommentare nach # werden ignoriert.",
    )
    parser.add_argument(
        "-c",
        "--channel",
        default=DEFAULT_CHANNEL,
        help=f"Channel-Loginname. Default: {DEFAULT_CHANNEL}",
    )
    parser.add_argument(
        "--status",
        choices=["RESTRICTED", "ACTIVE_MONITORING"],
        default="RESTRICTED",
        help="Suspicious-User-Status, der gesetzt wird. Default: RESTRICTED",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Entfernt den Suspicious-User-Status statt ihn zu setzen.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt nur, was geaendert wuerde.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.0,
        help="Pause in Sekunden zwischen User-Updates. Default: 4.0",
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=65.0,
        help="Pause in Sekunden nach HTTP 429, falls Twitch keinen Retry-After Header sendet. Default: 65.0",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximale Wiederholungen pro User nach HTTP 429. Default: 3",
    )
    parser.add_argument(
        "--skip-scope-check",
        action="store_true",
        help="Ueberspringt die Token-Scope-Pruefung.",
    )
    args = parser.parse_args()

    env = load_env()
    if not args.skip_scope_check:
        validate_scope(env)

    usernames = load_usernames(args)
    if not usernames:
        print("Bitte mindestens einen Usernamen angeben.", file=sys.stderr)
        return 2

    channel_login = normalize_login(args.channel)
    lookup_logins = [channel_login] + usernames
    users = get_users_by_login(env, lookup_logins)

    broadcaster = users.get(channel_login)
    if not broadcaster:
        print(f"Channel nicht gefunden: {channel_login}", file=sys.stderr)
        return 1

    broadcaster_id = broadcaster["id"]
    action = "remove" if args.remove else args.status
    failures = 0

    for index, login in enumerate(usernames):
        user = users.get(login)
        if not user:
            print(f"FEHLER User nicht gefunden: {login}", file=sys.stderr)
            failures += 1
            continue

        if args.dry_run:
            print(f"DRY-RUN {action}: {login} ({user['id']}) in #{channel_login}")
            continue

        response = run_update_with_retries(env, args, broadcaster_id, user)
        if response.status_code == 200:
            data = response.json().get("data", [{}])[0]
            status = data.get("status", "OK")
            print(f"OK {login}: {status}")
        else:
            print_api_error(action, login, response)
            failures += 1

        if not args.dry_run and args.delay > 0 and index < len(usernames) - 1:
            time.sleep(args.delay)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
