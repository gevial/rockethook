Simple library for posting to Rocket.Chat via webhooks a.k.a. integrations
========================

It is a very small library indeed, so the best explanation is an example of usage:

>>> import rockethook
>>> my_hook = rockethook.Webhook('https://rocketchat.example.com', my_token)
>>> msg = rockethook.Message(icon_url='http://example.com/icon.png')
>>> msg.append_text('First line.')
...
>>> msg.append_text('Second line.')
...
>>> msg.add_attachment(title='Attach', title_link='http://example.com', image_url='http://example.com/img.png')
>>> my_hook.post(msg)

To post quick simple messages:

>>> my_hook.quick_post('Hi!')
>>> my_hook.quick_post('What\'s up?')
