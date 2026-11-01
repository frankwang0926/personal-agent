from io import BytesIO
import json
import traceback
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

import telegram_bot


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

    telegram_bot.main()

    request.assert_called_once_with(
        "https://api.telegram.org/botfake-test-token/getMe", timeout=10,
    )
    output = capsys.readouterr().out
    assert "example_test_bot" in output and "123" in output
    assert "fake-test-token" not in output


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
