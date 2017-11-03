import email


# Do *not* remove this, we need to use this in subclasses of EmailTransport
from email.errors import MessageParseError


class EmailTransport(object):
    def get_email_from_bytes(self, contents):
        if six.PY3:
            message = email.message_from_bytes(contents)
        else:
            message = email.message_from_string(contents)

        return message
