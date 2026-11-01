import json
import os
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv


def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if token is None or not token.strip():
        raise ValueError("TELEGRAM_BOT_TOKEN must not be missing or blank.")

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        with urlopen(url, timeout=10) as response:
            data = json.load(response)
    except (URLError, TimeoutError):
        raise RuntimeError("Could not connect to Telegram. Check your bot token and network connection.") from None

    if not data.get("ok"):
        raise RuntimeError("Telegram getMe request failed.")

    bot = data["result"]
    print(f"Bot username: @{bot['username']}, ID: {bot['id']}")


if __name__ == "__main__":
    main()
