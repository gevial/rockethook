Rockethook
========================

Simple library for posting to Rocket.Chat via webhooks a.k.a. integrations

The idea behind this library is to create Webhook object and then post Messages with it.
You can create Message object and fulfill it with content (text and/or attachments) later.

Or you can just Webhook.quick_post('Your message') without bothering with Message objects.

It is a very small library indeed, so the best explanation is an example of usage:

>>> import rockethook
>>> my_hook = rockethook.Webhook('https://rocketchat.example.com', my_token)
>>> msg = rockethook.Message(icon_url='http://example.com/icon.png')
>>> msg.append_text('First line.')
>>> msg.append_text('Second line.')
>>> msg.add_attachment(
...     title='Attach',
...     title_link='http://example.com',
...     image_url='http://example.com/img.png'
... )
>>> my_hook.post(msg)

To quickly post simple text messages:

>>> my_hook.quick_post('Hi!')
>>> my_hook.quick_post('Call me back\nPlease')
