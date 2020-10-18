from django.dispatch.dispatcher import Signal

message_received = Signal(providing_args=['message'])
email_queued = Signal()   # sender is OutgoingEmail instance
email_sent = Signal(providing_args=['outgoing_email'])
email_failed_to_send = Signal(providing_args=['outgoing_email'])
