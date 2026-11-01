import json
import os
import tempfile
from functools import partial
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from openai import OpenAI

from main import StepLimitExceeded, run_agent
from state import load_history, save_history


def load_cursor(path: str) -> int | None:
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return None

    if not isinstance(data, dict):
        raise ValueError("Telegram cursor file must contain an object with next_offset.")
    next_offset = data.get("next_offset")
    if type(next_offset) is not int or next_offset < 0:
        raise ValueError("Telegram next_offset must be a nonnegative integer.")
    return next_offset


def save_cursor(path: str, next_offset: int) -> None:
    if type(next_offset) is not int or next_offset < 0:
        raise ValueError("Telegram next_offset must be a nonnegative integer.")
    _save_json(path, {"next_offset": next_offset})


def _save_json(path: str, data: dict) -> None:
    destination = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, indent=2)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_inflight(path: str) -> int | None:
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return None
    if not isinstance(data, dict):
        raise ValueError("Telegram in-flight file must contain an update_id object.")
    update_id = data.get("update_id")
    if type(update_id) is not int or update_id < 0:
        raise ValueError("Telegram in-flight update_id must be a nonnegative integer.")
    return update_id


def check_inflight(offset: int | None, path: str) -> None:
    update_id = load_inflight(path)
    if update_id is None:
        return
    if offset is not None and update_id < offset:
        # The reply and checkpoint completed before marker cleanup was interrupted.
        Path(path).unlink()
        return
    raise RuntimeError(
        f"Telegram update {update_id} was interrupted and may have performed actions. "
        "Automatic replay is blocked. Inspect task state and Telegram history, then "
        "resolve the pending update and checkpoint before restarting."
    )


def get_updates(token: str, offset: int | None = None) -> list:
    parameters = {"timeout": 20, "allowed_updates": json.dumps(["message"])}
    if offset is not None:
        parameters["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urlencode(parameters)}"

    try:
        with urlopen(url, timeout=30) as response:
            data = json.load(response)
    except (URLError, TimeoutError):
        raise RuntimeError("Could not receive Telegram updates. Check your connection and bot configuration.") from None

    if not data.get("ok"):
        raise RuntimeError("Telegram getUpdates request failed.")
    if not isinstance(data.get("result"), list):
        raise RuntimeError("Telegram getUpdates returned an invalid update list.")
    return data["result"]


def poll_updates(
    token: str, handle_update, cursor_path: str = "telegram_cursor.json",
    inflight_path: str = "telegram_inflight.json",
) -> None:
    offset = load_cursor(cursor_path)
    check_inflight(offset, inflight_path)
    while True:
        updates = get_updates(token, offset)
        for update in updates:
            if offset is not None and update["update_id"] < offset:
                continue
            handle_update(update)
            # Checkpoint before acknowledging this update in the next request.
            next_offset = update["update_id"] + 1
            save_cursor(cursor_path, next_offset)
            offset = next_offset
            pending = load_inflight(inflight_path)
            if pending is not None:
                if pending != update["update_id"]:
                    raise RuntimeError("Telegram in-flight update does not match the checkpoint.")
                Path(inflight_path).unlink()


def send_message(token: str, chat_id: int, text: str) -> None:
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            data = json.load(response)
    except (URLError, TimeoutError):
        raise RuntimeError("Could not send Telegram reply. Delivery status may be unknown.") from None

    if not data.get("ok"):
        raise RuntimeError("Telegram sendMessage request failed.")


def handle_update(
    update: dict, *, token: str, allowed_user_id: int, client: OpenAI, history: list,
    history_path: str = "telegram_conversation.json",
    inflight_path: str = "telegram_inflight.json",
) -> None:
    message = update.get("message")
    if not isinstance(message, dict):
        return
    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return
    if chat.get("type") != "private" or sender.get("id") != allowed_user_id:
        return
    text = message.get("text")
    if not isinstance(text, str) or not text:
        return
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return

    update_id = update["update_id"]
    if type(update_id) is not int or update_id < 0:
        raise ValueError("Telegram update_id must be a nonnegative integer.")
    if load_inflight(inflight_path) is not None:
        raise RuntimeError("An unresolved Telegram update already exists; automatic replay is blocked.")
    # Record intent before the agent can perform a task write.
    _save_json(inflight_path, {"update_id": update_id})
    try:
        response = run_agent(client, text, history=history)
    except StepLimitExceeded:
        response = (
            "This request reached the step limit without a final answer. "
            "Some actions may already have been performed. You can continue sending messages."
        )
        history.append({"role": "assistant", "content": response})
    save_history(history_path, history)
    send_message(token, chat_id, response)


def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if token is None or not token.strip():
        raise ValueError("TELEGRAM_BOT_TOKEN must not be missing or blank.")
    token = token.strip()

    owner = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
    try:
        allowed_user_id = int(owner)
    except ValueError:
        raise ValueError("TELEGRAM_ALLOWED_USER_ID must be a positive integer.") from None
    if allowed_user_id <= 0:
        raise ValueError("TELEGRAM_ALLOWED_USER_ID must be a positive integer.")

    check_inflight(load_cursor("telegram_cursor.json"), "telegram_inflight.json")
    history = load_history("telegram_conversation.json")
    client = OpenAI()

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
    print("Listening for updates. Press Ctrl+C to stop.")
    try:
        handler = partial(
            handle_update, token=token, allowed_user_id=allowed_user_id,
            client=client, history=history,
        )
        poll_updates(token, handler)
    except KeyboardInterrupt:
        print("\nStopped listening.")


if __name__ == "__main__":
    main()
