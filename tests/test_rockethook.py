import json
import http.client
from unittest.mock import MagicMock, patch, call
from urllib.parse import unquote_plus

import pytest

import rockethook
from rockethook import Message, Webhook, WebhookError


# ---------------------------------------------------------------------------
# WebhookError
# ---------------------------------------------------------------------------

class TestWebhookError:
    def test_is_exception(self):
        assert issubclass(WebhookError, Exception)

    def test_message_format(self):
        err = WebhookError(404, "not found")
        assert err.message == "Rocket.Chat server error, code 404: not found"

    def test_status_stored(self):
        err = WebhookError(500, "oops")
        assert err.status == 500

    def test_str_representation(self):
        err = WebhookError(403, "forbidden")
        assert "403" in str(err)
        assert "forbidden" in str(err)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(WebhookError) as exc_info:
            raise WebhookError(401, "unauthorized")
        assert exc_info.value.status == 401


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class TestMessage:
    def test_default_construction(self):
        msg = Message()
        assert msg.text == ""
        assert msg.channel is None
        assert msg.icon_url is None
        assert msg.attachments == []

    def test_construction_with_all_args(self):
        msg = Message(text="hi", channel="#general", icon_url="http://example.com/icon.png")
        assert msg.text == "hi"
        assert msg.channel == "#general"
        assert msg.icon_url == "http://example.com/icon.png"

    def test_append_text_to_empty(self):
        msg = Message()
        msg.append_text("first")
        assert msg.text == "first"

    def test_append_text_default_delimiter(self):
        msg = Message(text="first")
        msg.append_text("second")
        assert msg.text == "first\nsecond"

    def test_append_text_custom_delimiter(self):
        msg = Message(text="A")
        msg.append_text("B", delimiter=" | ")
        assert msg.text == "A | B"

    def test_append_text_multiple(self):
        msg = Message()
        msg.append_text("line1")
        msg.append_text("line2")
        msg.append_text("line3")
        assert msg.text == "line1\nline2\nline3"

    def test_add_attachment_single(self):
        msg = Message()
        msg.add_attachment(title="T", title_link="http://x.com", color="#ff0000")
        assert len(msg.attachments) == 1
        assert msg.attachments[0] == {"title": "T", "title_link": "http://x.com", "color": "#ff0000"}

    def test_add_attachment_multiple(self):
        msg = Message()
        msg.add_attachment(title="first")
        msg.add_attachment(title="second")
        assert len(msg.attachments) == 2
        assert msg.attachments[0]["title"] == "first"
        assert msg.attachments[1]["title"] == "second"

    def test_add_attachment_arbitrary_kwargs(self):
        msg = Message()
        msg.add_attachment(image_url="http://img.png", text="caption")
        assert msg.attachments[0]["image_url"] == "http://img.png"
        assert msg.attachments[0]["text"] == "caption"


# ---------------------------------------------------------------------------
# Webhook construction
# ---------------------------------------------------------------------------

class TestWebhookInit:
    def test_https_url(self):
        hook = Webhook("https://chat.example.com", "mytoken")
        assert hook.scheme == "https"
        assert hook.server_fqdn == "chat.example.com"
        assert hook.token == "mytoken"

    def test_http_url(self):
        hook = Webhook("http://chat.example.com", "tok")
        assert hook.scheme == "http"
        assert hook.server_fqdn == "chat.example.com"

    def test_url_with_path(self):
        hook = Webhook("https://chat.example.com/some/path", "tok")
        assert hook.server_fqdn == "chat.example.com"

    def test_url_with_port(self):
        hook = Webhook("https://chat.example.com:8443", "tok")
        assert hook.server_fqdn == "chat.example.com:8443"


# ---------------------------------------------------------------------------
# Webhook.post — helpers
# ---------------------------------------------------------------------------

def _make_response(status: int, body: object) -> MagicMock:
    """Return a mock HTTPResponse with the given status and JSON body."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body).encode()
    return resp


def _decode_payload(raw_payload: str) -> dict:
    """Decode a form-encoded 'payload=<json>' string back to a dict."""
    assert raw_payload.startswith("payload=")
    return json.loads(unquote_plus(raw_payload[len("payload="):]))


# ---------------------------------------------------------------------------
# Webhook.post — behaviour
# ---------------------------------------------------------------------------

class TestWebhookPost:
    @patch("http.client.HTTPSConnection")
    def test_post_uses_https_for_https_scheme(self, mock_https_cls):
        mock_https_cls.return_value.getresponse.return_value = _make_response(200, {"success": True})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hi"))
        mock_https_cls.assert_called_once_with("chat.example.com")

    @patch("http.client.HTTPConnection")
    def test_post_uses_http_for_http_scheme(self, mock_http_cls):
        mock_http_cls.return_value.getresponse.return_value = _make_response(200, {"success": True})
        hook = Webhook("http://chat.example.com", "tok")
        hook.post(Message(text="hi"))
        mock_http_cls.assert_called_once_with("chat.example.com")

    @patch("http.client.HTTPSConnection")
    def test_post_sends_to_correct_path(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "mytoken")
        hook.post(Message(text="hello"))
        args = conn.request.call_args
        assert args[0][1] == "/hooks/mytoken"

    @patch("http.client.HTTPSConnection")
    def test_post_sends_correct_content_type(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hi"))
        headers = conn.request.call_args[0][3]
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"

    @patch("http.client.HTTPSConnection")
    def test_post_encodes_text(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hello world"))
        payload = conn.request.call_args[0][2]
        data = _decode_payload(payload)
        assert data["text"] == "hello world"

    @patch("http.client.HTTPSConnection")
    def test_post_encodes_channel(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hi", channel="#general"))
        payload = conn.request.call_args[0][2]
        data = _decode_payload(payload)
        assert data["channel"] == "#general"

    @patch("http.client.HTTPSConnection")
    def test_post_encodes_icon_url(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hi", icon_url="http://img.png"))
        payload = conn.request.call_args[0][2]
        data = _decode_payload(payload)
        assert data["icon_url"] == "http://img.png"

    @patch("http.client.HTTPSConnection")
    def test_post_encodes_attachments(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        msg = Message(text="hi")
        msg.add_attachment(title="A", color="#fff")
        hook.post(msg)
        payload = conn.request.call_args[0][2]
        data = _decode_payload(payload)
        assert data["attachments"] == [{"title": "A", "color": "#fff"}]

    @patch("http.client.HTTPSConnection")
    def test_post_omits_empty_optional_fields(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hi"))
        payload = conn.request.call_args[0][2]
        data = _decode_payload(payload)
        assert "channel" not in data
        assert "icon_url" not in data
        assert "attachments" not in data

    @patch("http.client.HTTPSConnection")
    def test_post_closes_connection(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(200, {})
        hook = Webhook("https://chat.example.com", "tok")
        hook.post(Message(text="hi"))
        conn.close.assert_called_once()

    @patch("http.client.HTTPSConnection")
    def test_post_raises_on_non_200(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(400, {"error": "bad request"})
        hook = Webhook("https://chat.example.com", "tok")
        with pytest.raises(WebhookError) as exc_info:
            hook.post(Message(text="hi"))
        assert exc_info.value.status == 400
        assert "bad request" in exc_info.value.message

    @patch("http.client.HTTPSConnection")
    def test_post_raises_on_error_in_message_field(self, mock_https_cls):
        conn = mock_https_cls.return_value
        conn.getresponse.return_value = _make_response(500, {"message": "server error"})
        hook = Webhook("https://chat.example.com", "tok")
        with pytest.raises(WebhookError) as exc_info:
            hook.post(Message(text="hi"))
        assert "server error" in exc_info.value.message

    @patch("http.client.HTTPSConnection")
    def test_post_raises_on_non_json_response(self, mock_https_cls):
        conn = mock_https_cls.return_value
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b"not json at all"
        conn.getresponse.return_value = resp
        hook = Webhook("https://chat.example.com", "tok")
        with pytest.raises(WebhookError) as exc_info:
            hook.post(Message(text="hi"))
        assert "token" in exc_info.value.message.lower()

    def test_post_raises_type_error_for_non_message(self):
        hook = Webhook("https://chat.example.com", "tok")
        with pytest.raises(TypeError):
            hook.post("not a message")  # type: ignore[arg-type]

    def test_post_raises_type_error_for_none(self):
        hook = Webhook("https://chat.example.com", "tok")
        with pytest.raises(TypeError):
            hook.post(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Webhook.quick_post
# ---------------------------------------------------------------------------

class TestWebhookQuickPost:
    @patch.object(Webhook, "post")
    def test_quick_post_delegates_to_post(self, mock_post):
        hook = Webhook("https://chat.example.com", "tok")
        hook.quick_post("hello")
        mock_post.assert_called_once()
        msg_arg = mock_post.call_args[0][0]
        assert isinstance(msg_arg, Message)
        assert msg_arg.text == "hello"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TestPublicApi:
    def test_all_exports(self):
        assert set(rockethook.__all__) == {"Webhook", "Message", "WebhookError"}
