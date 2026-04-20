"""Simple library for posting to Rocket.Chat via webhooks a.k.a. integrations.

The idea behind this library is to create Webhook object and then
post Messages with it. You can create Message object and fulfill it
with content (text and/or attachments) later.

Or you can just Webhook.quick_post('Your message') without bothering with Message objects.
"""

from __future__ import annotations

import http.client
import json
from urllib.parse import urlparse, quote_plus

__all__ = ["Webhook", "Message", "WebhookError"]


class WebhookError(Exception):
    """Raised when Rocket.Chat server responds with non-JSON or an explicit error."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = f"Rocket.Chat server error, code {status}: {message}"
        super().__init__(self.message)


class Webhook:
    """Usage example:

    >>> import rockethook
    >>> my_hook = rockethook.Webhook('https://rocketchat.example.com', token)
    >>> msg = rockethook.Message(icon_url='http://example.com/icon.png')
    >>> msg.append_text('First line.')
    >>> msg.append_text('Second line.')
    >>> msg.add_attachment(
    ...     title='Attach',
    ...     title_link='http://example.com',
    ...     image_url='http://example.com/img.png'
    ... )
    >>> my_hook.post(msg)
    >>>
    >>> my_hook.quick_post('Hi!')
    >>> my_hook.quick_post('What\\'s up?')
    """

    def __init__(self, server_url: str, token: str) -> None:
        """Create a Webhook suitable for posting multiple messages.

        server_url should be a valid URL starting with a scheme.
        token is a token given by a Rocket.Chat server.
        """
        parsed = urlparse(server_url)
        self.scheme = parsed.scheme
        self.server_fqdn = parsed.netloc or parsed.path.split("/")[0]
        self.token = token

    def quick_post(self, text: str) -> None:
        """Post a simple text message."""
        self.post(Message(text=text))

    def post(self, message: Message) -> None:
        """Send a message to Rocket.Chat.

        message must be a rockethook.Message instance.
        For plain text messages, use quick_post() instead.
        """
        if not isinstance(message, Message):
            raise TypeError(f"Expected a Message instance, got {type(message).__name__}")

        payload_dict: dict[str, object] = {}
        if message.text:
            payload_dict["text"] = message.text
        if message.channel:
            payload_dict["channel"] = message.channel
        if message.icon_url:
            payload_dict["icon_url"] = message.icon_url
        if message.attachments:
            payload_dict["attachments"] = message.attachments

        payload = "payload=" + quote_plus(json.dumps(payload_dict))
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if self.scheme == "https":
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(self.server_fqdn)
        else:
            conn = http.client.HTTPConnection(self.server_fqdn)

        conn.request("POST", f"/hooks/{self.token}", payload, headers)
        response = conn.getresponse()
        status = response.status
        response_data = response.read()
        conn.close()

        try:
            data = json.loads(response_data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise WebhookError(status, "Not an API response, check your token.") from exc

        if status != 200:
            if "error" in data:
                err_msg = data["error"]
            elif "message" in data:
                err_msg = data["message"]
            else:
                err_msg = data
            raise WebhookError(status, err_msg)


class Message:
    """Usage example:

    >>> import rockethook
    >>> my_hook = rockethook.Webhook('https://rocketchat.example.com', token)
    >>> msg = rockethook.Message(icon_url='http://example.com/icon.png')
    >>> msg.append_text('First line.')
    >>> msg.append_text('Second line.')
    >>> msg.add_attachment(
    ...     title='Attach',
    ...     title_link='http://example.com',
    ...     image_url='http://example.com/img.png'
    ... )
    >>> my_hook.post(msg)
    """

    def __init__(self, text: str = "", channel: str | None = None, icon_url: str | None = None) -> None:
        """Create a Message.

        You can provide content immediately:
        >>> msg = rockethook.Message(text='Hi there')

        Or create an empty message and populate it later via append_text() and add_attachment().
        """
        self.text = text
        self.channel = channel
        self.icon_url = icon_url
        self.attachments: list[dict[str, object]] = []

    def append_text(self, text_to_append: str, delimiter: str = "\n") -> None:
        """Append text to the message body."""
        if self.text:
            self.text = self.text + delimiter + text_to_append
        else:
            self.text = text_to_append

    def add_attachment(self, **kwargs: object) -> None:
        """Add an attachment to the message.

        As of Rocket.Chat version 0.20, valid attachment arguments are:
            * title
            * title_link
            * text
            * image_url
            * color
        Multiple attachments are supported.
        """
        self.attachments.append(kwargs)
