from io import BytesIO
import json
import traceback
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

import telegram_bot


@pytest.fixture(autouse=True)
def fake_owner(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_ID", "456")
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("token", [None, "", "   "])
def test_missing_token_stops_before_request(monkeypatch, token):
    monkeypatch.setattr(telegram_bot, "load_dotenv", lambda: None)
    if token is None:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    request = Mock()
    monkeypatch.setattr(telegram_bot, "urlopen", request)

    with pytest.raises((ValueError, RuntimeError, SystemExit)):
        telegram_bot.main()
    request.assert_not_called()


def test_getme_prints_identity_without_credentials(monkeypatch, capsys):
    monkeypatch.setattr(telegram_bot, "load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-test-token")
    payload = {"ok": True, "result": {
        "id": 123, "is_bot": True, "username": "example_test_bot",
    }}
    request = Mock(return_value=BytesIO(json.dumps(payload).encode()))
    monkeypatch.setattr(telegram_bot, "urlopen", request)
    polling = Mock()
    monkeypatch.setattr(telegram_bot, "poll_updates", polling)

    telegram_bot.main()

    request.assert_called_once_with(
        "https://api.telegram.org/botfake-test-token/getMe", timeout=10,
    )
    output = capsys.readouterr().out
    assert "example_test_bot" in output and "123" in output
    assert "fake-test-token" not in output
    polling.assert_called_once()
    assert polling.call_args.args[0] == "fake-test-token"
    handler = polling.call_args.args[1]
    assert handler.func is telegram_bot.handle_update
    assert handler.keywords == {"token": "fake-test-token", "allowed_user_id": 456}


@pytest.mark.parametrize("error_type", [HTTPError, URLError, TimeoutError])
def test_transport_failure_stops_with_safe_error(monkeypatch, capsys, error_type):
    monkeypatch.setattr(telegram_bot, "load_dotenv", lambda: None)
    token = "fake-test-token"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    url = f"https://api.telegram.org/bot{token}/getMe"
    error = (HTTPError(url, 401, "Unauthorized", None, None)
             if error_type is HTTPError else error_type("Connection failed"))
    monkeypatch.setattr(telegram_bot, "urlopen", Mock(side_effect=error))

    with pytest.raises((RuntimeError, SystemExit)) as caught:
        telegram_bot.main()

    output = capsys.readouterr()
    displayed = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
    assert token not in output.out + output.err + displayed
    assert "HTTPError:" not in displayed and "URLError:" not in displayed
    assert "TimeoutError:" not in displayed


def test_get_updates_uses_long_poll_and_longer_http_timeout(monkeypatch):
    updates = [{"update_id": 42}]
    response = BytesIO(json.dumps({"ok": True, "result": updates}).encode())
    request = Mock(return_value=response)
    monkeypatch.setattr(telegram_bot, "urlopen", request)

    assert telegram_bot.get_updates("fake-test-token", offset=41) == updates

    query = parse_qs(urlparse(request.call_args.args[0]).query)
    assert query == {"timeout": ["20"], "offset": ["41"],
                     "allowed_updates": ['["message"]']}
    assert request.call_args.kwargs == {"timeout": 30}


def test_polling_processes_batch_in_order_and_keeps_cursor_on_empty_batch(monkeypatch):
    first, second = {"update_id": 40}, {"update_id": 42}
    receive = Mock(side_effect=[[first, second], [], KeyboardInterrupt()])
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    handled = []

    with pytest.raises(KeyboardInterrupt):
        telegram_bot.poll_updates("fake-test-token", handled.append)

    assert handled == [first, second]
    assert [call.args[1] for call in receive.call_args_list] == [None, 43, 43]


def test_failed_handling_stops_before_next_poll(monkeypatch):
    receive = Mock(return_value=[{"update_id": 40}, {"update_id": 41}])
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    handler = Mock(side_effect=RuntimeError("Handler failed"))

    with pytest.raises(RuntimeError, match="Handler failed"):
        telegram_bot.poll_updates("fake-test-token", handler)

    receive.assert_called_once_with("fake-test-token", None)
    handler.assert_called_once_with({"update_id": 40})


@pytest.mark.parametrize("owner", [None, "", "not-a-number", "0", "-1"])
def test_invalid_owner_stops_before_any_request(monkeypatch, owner):
    monkeypatch.setattr(telegram_bot, "load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-test-token")
    if owner is None:
        monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_ALLOWED_USER_ID", owner)
    request = Mock()
    monkeypatch.setattr(telegram_bot, "urlopen", request)

    with pytest.raises(ValueError, match="TELEGRAM_ALLOWED_USER_ID"):
        telegram_bot.main()
    request.assert_not_called()


def test_filter_skips_other_updates_and_echoes_owner_private_text(monkeypatch):
    text = "  Hello 世界 <tag> & *literal*\nSecond line  "
    message = {"from": {"id": 456}, "chat": {"type": "private", "id": 789},
               "text": text}
    skipped = [
        {}, {"edited_message": message}, {"message": None},
        {"message": {**message, "from": {"id": 999}}},
        {"message": {**message, "chat": {"type": "group", "id": -123}}},
        {"message": {**message, "text": None, "photo": []}},
        {"message": {"chat": message["chat"], "text": "No sender"}},
    ]
    updates = [{"update_id": i, **update} for i, update in enumerate(skipped)]
    updates.append({"update_id": len(updates), "message": message})
    receive = Mock(side_effect=[updates, [], KeyboardInterrupt()])
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    send = Mock()
    monkeypatch.setattr(telegram_bot, "send_message", send)

    def handle(update):
        telegram_bot.handle_update(update, token="fake-test-token", allowed_user_id=456)

    with pytest.raises(KeyboardInterrupt):
        telegram_bot.poll_updates("fake-test-token", handle)

    send.assert_called_once_with("fake-test-token", 789, text)
    assert [call.args[1] for call in receive.call_args_list] == [None, len(updates), len(updates)]


def test_send_message_posts_original_text_without_parse_mode(monkeypatch):
    request = Mock(return_value=BytesIO(b'{"ok":true,"result":{}}'))
    monkeypatch.setattr(telegram_bot, "urlopen", request)
    text = "  世界 & *text*\n  "

    telegram_bot.send_message("fake-test-token", 789, text)

    outgoing = request.call_args.args[0]
    assert outgoing.full_url == "https://api.telegram.org/botfake-test-token/sendMessage"
    assert outgoing.get_method() == "POST"
    assert outgoing.get_header("Content-type") == "application/json"
    assert json.loads(outgoing.data) == {"chat_id": 789, "text": text}
    assert request.call_args.kwargs == {"timeout": 10}


@pytest.mark.parametrize("response", [URLError("Network failed"), {"ok": False}])
def test_failed_send_stops_before_acknowledging_update(monkeypatch, response):
    update = {"update_id": 42, "message": {
        "from": {"id": 456}, "chat": {"type": "private", "id": 789}, "text": "Hello",
    }}
    receive = Mock(return_value=[update])
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    if isinstance(response, Exception):
        transport = Mock(side_effect=response)
    else:
        transport = Mock(return_value=BytesIO(json.dumps(response).encode()))
    monkeypatch.setattr(telegram_bot, "urlopen", transport)

    def handle(item):
        telegram_bot.handle_update(item, token="fake-test-token", allowed_user_id=456)

    with pytest.raises(RuntimeError):
        telegram_bot.poll_updates("fake-test-token", handle)
    receive.assert_called_once_with("fake-test-token", None)


def test_cursor_missing_and_round_trip(tmp_path):
    path = str(tmp_path / "cursor.json")
    assert telegram_bot.load_cursor(path) is None
    telegram_bot.save_cursor(path, 0)
    assert telegram_bot.load_cursor(path) == 0
    telegram_bot.save_cursor(path, 43)
    assert telegram_bot.load_cursor(path) == 43


@pytest.mark.parametrize("data", [[], {}, {"next_offset": None},
    {"next_offset": True}, {"next_offset": -1}, {"next_offset": 1.5},
    {"next_offset": "43"}])
def test_invalid_cursor_stops_before_polling(tmp_path, monkeypatch, data):
    path = tmp_path / "cursor.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    receive = Mock()
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    with pytest.raises(ValueError):
        telegram_bot.poll_updates("fake-test-token", Mock(), str(path))
    receive.assert_not_called()


def test_malformed_cursor_is_preserved_and_not_reset(tmp_path, monkeypatch):
    path = tmp_path / "cursor.json"
    path.write_text('{"next_offset":', encoding="utf-8")
    receive = Mock()
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    with pytest.raises(json.JSONDecodeError):
        telegram_bot.poll_updates("fake-test-token", Mock(), str(path))
    receive.assert_not_called()
    assert path.read_text(encoding="utf-8") == '{"next_offset":'


def test_restart_restores_checkpoint_and_ignores_stale_updates(tmp_path, monkeypatch):
    path = str(tmp_path / "cursor.json")
    handled = []

    def handle(update):
        # The checkpoint must still describe the prior completed update here.
        assert telegram_bot.load_cursor(path) == (None if not handled else 41)
        handled.append(update)

    first = Mock(side_effect=[[{"update_id": 40}], KeyboardInterrupt()])
    monkeypatch.setattr(telegram_bot, "get_updates", first)
    with pytest.raises(KeyboardInterrupt):
        telegram_bot.poll_updates("fake-test-token", handle, path)
    assert telegram_bot.load_cursor(path) == 41

    second = Mock(side_effect=[[
        {"update_id": 39}, {"update_id": 40}, {"update_id": 42},
    ], [], KeyboardInterrupt()])
    monkeypatch.setattr(telegram_bot, "get_updates", second)
    with pytest.raises(KeyboardInterrupt):
        telegram_bot.poll_updates("fake-test-token", handle, path)

    assert handled == [{"update_id": 40}, {"update_id": 42}]
    assert [call.args[1] for call in first.call_args_list] == [None, 41]
    assert [call.args[1] for call in second.call_args_list] == [41, 43, 43]
    assert telegram_bot.load_cursor(path) == 43


def test_checkpoint_replacement_failure_preserves_state_and_stops(tmp_path, monkeypatch):
    path = tmp_path / "cursor.json"
    telegram_bot.save_cursor(str(path), 40)
    before = path.read_bytes()
    receive = Mock(return_value=[{"update_id": 40}, {"update_id": 41}])
    monkeypatch.setattr(telegram_bot, "get_updates", receive)
    handler = Mock()
    replace = Mock(side_effect=OSError("Simulated replacement failure"))
    monkeypatch.setattr(telegram_bot.os, "replace", replace)

    with pytest.raises(OSError, match="replacement failure"):
        telegram_bot.poll_updates("fake-test-token", handler, str(path))

    handler.assert_called_once_with({"update_id": 40})
    receive.assert_called_once_with("fake-test-token", 40)
    assert path.read_bytes() == before
    assert set(tmp_path.iterdir()) == {path}
