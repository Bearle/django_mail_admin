import base64
import email
import gzip
from email.encoders import encode_base64
from email.message import Message as EmailMessage
from email.utils import formatdate, parseaddr
from io import BytesIO
from quopri import encode as encode_quopri

from django.core.exceptions import ValidationError
from django.core.mail.message import make_msgid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_mail_admin.models import Mailbox, OutgoingEmail
from django_mail_admin.settings import get_attachment_interpolation_header, get_altered_message_header
from django_mail_admin.utils import get_body_from_message, get_attachment_save_path, \
    convert_header_to_unicode


class UnreadMessageManager(models.Manager):
    def get_queryset(self):
        return super(UnreadMessageManager, self).get_queryset().filter(
            read=None
        )


class IncomingEmail(models.Model):
    mailbox = models.ForeignKey(
        Mailbox,
        related_name='messages',
        verbose_name=_('Mailbox'),
        on_delete=models.CASCADE
    )

    subject = models.CharField(
        _('Subject'),
        max_length=255
    )

    message_id = models.CharField(
        _('IncomingEmail ID'),
        max_length=255
    )

    in_reply_to = models.ForeignKey(
        OutgoingEmail,
        related_name='replies',
        blank=True,
        null=True,
        verbose_name=_('In reply to'),
        on_delete=models.CASCADE
    )

    from_header = models.CharField(
        _('From header'),
        max_length=255,
    )

    to_header = models.TextField(
        _('To header'),
    )

    body = models.TextField(
        _('Body'),
    )

    encoded = models.BooleanField(
        _('Encoded'),
        default=False,
        help_text=_('True if the e-mail body is Base64 encoded'),
    )

    processed = models.DateTimeField(
        _('Processed'),
        auto_now_add=True
    )

    read = models.DateTimeField(
        _('Read'),
        default=None,
        blank=True,
        null=True,
    )

    eml = models.FileField(
        _('Raw message contents'),
        null=True,
        upload_to="messages",
        help_text=_('Original full content of message')
    )
    objects = models.Manager()
    unread_messages = UnreadMessageManager()

    @property
    def address(self):
        """Property allowing one to get the relevant address(es).

        In earlier versions of this library, the model had an `address` field
        storing the e-mail address from which a message was received.  During
        later refactorings, it became clear that perhaps storing sent messages
        would also be useful, so the address field was replaced with two
        separate fields.

        """
        addresses = []
        addresses = self.to_addresses + self.from_address
        return addresses

    @property
    def from_address(self):
        """Returns the address (as a list) from which this message was received

        .. note::

           This was once (and probably should be) a string rather than a list,
           but in a pull request received long, long ago it was changed;
           presumably to make the interface identical to that of
           `to_addresses`.

        """
        if self.from_header:
            return [parseaddr(self.from_header)[1].lower()]
        else:
            return []

    @property
    def to_addresses(self):
        """Returns a list of addresses to which this message was sent."""
        addresses = []
        for address in self.to_header.split(','):
            if address:
                addresses.append(
                    parseaddr(
                        address
                    )[1].lower()
                )
        return addresses

    def get_reply_headers(self, headers=None):
        headers = headers or {}
        headers['Message-ID'] = make_msgid()
        headers['Date'] = formatdate()
        headers['In-Reply-To'] = self.message_id.strip()
        return headers

    def reply(self, **kwargs):
        """Sends a message as a reply to this message instance.

        Although Django's e-mail processing will set both IncomingEmail-ID
        and Date upon generating the e-mail message, we will not be able
        to retrieve that information through normal channels, so we must
        pre-set it.

        """
        from django_mail_admin.mail import send
        if 'sender' not in kwargs:
            if len(self.from_address) == 0 and not self.mailbox.from_email:
                raise ValidationError('No sender address to reply from, %s' % str(self))
            else:
                kwargs['sender'] = self.from_address[0] or self.mailbox.from_email
        headers = self.get_reply_headers(kwargs.get('headers'))
        kwargs['headers'] = headers
        return send(**kwargs)

    @property
    def text(self):
        """
        Returns the message body matching content type 'text/plain'.
        """
        return get_body_from_message(
            self.get_email_object(), 'text', 'plain'
        ).replace('=\n', '').strip()

    @property
    def html(self):
        """
        Returns the message body matching content type 'text/html'.
        """
        return get_body_from_message(
            self.get_email_object(), 'text', 'html'
        ).replace('\n', '').strip()

    def _rehydrate(self, msg):
        new = EmailMessage()

        if msg.is_multipart():
            for header, value in msg.items():
                new[header] = value
            for part in msg.get_payload():
                new.attach(
                    self._rehydrate(part)
                )
        elif get_attachment_interpolation_header() in msg.keys():
            try:
                attachment = IncomingAttachment.objects.get(
                    pk=msg[get_attachment_interpolation_header()]
                )
                for header, value in attachment.items():
                    new[header] = value
                encoding = new['Content-Transfer-Encoding']
                if encoding and encoding.lower() == 'quoted-printable':
                    # Cannot use `email.encoders.encode_quopri due to
                    # bug 14360: http://bugs.python.org/issue14360
                    output = BytesIO()
                    encode_quopri(
                        BytesIO(
                            attachment.document.read()
                        ),
                        output,
                        quotetabs=True,
                        header=False,
                    )
                    new.set_payload(
                        output.getvalue().decode().replace(' ', '=20')
                    )
                    del new['Content-Transfer-Encoding']
                    new['Content-Transfer-Encoding'] = 'quoted-printable'
                else:
                    new.set_payload(
                        attachment.document.read()
                    )
                    del new['Content-Transfer-Encoding']
                    encode_base64(new)
            except IncomingAttachment.DoesNotExist:
                new[get_altered_message_header()] = (
                    'Missing; Attachment %s not found' % (
                    msg[get_attachment_interpolation_header()]
                )
                )
                new.set_payload('')
        else:
            for header, value in msg.items():
                new[header] = value
            new.set_payload(
                msg.get_payload()
            )
        return new

    def get_body(self):
        """Returns the `body` field of this record.

        This will automatically base64-decode the message contents
        if they are encoded as such.

        """
        if self.encoded:
            return base64.b64decode(self.body.encode('ascii'))
        return self.body.encode('utf-8')

    def set_body(self, body):
        """Set the `body` field of this record.

        This will automatically base64-encode the message contents to
        circumvent a limitation in earlier versions of Django in which
        no fields existed for storing arbitrary bytes.

        """
        body = body.encode('utf-8')
        self.encoded = True
        self.body = base64.b64encode(body).decode('ascii')

    def get_email_object(self):
        """Returns an `email.message.Message` instance representing the
        contents of this message and all attachments.

        See [email.Message.Message]_ for more information as to what methods
        and properties are available on `email.message.Message` instances.

        .. note::

           Depending upon the storage methods in use (specifically --
           whether ``DJANGO_MAILBOX_STORE_ORIGINAL_MESSAGE`` is set
           to ``True``, this may either create a "rehydrated" message
           using stored attachments, or read the message contents stored
           on-disk.

        .. [email.Message.Message]: Python's `email.message.Message` docs
           (https://docs.python.org/2/library/email.message.html)

        """
        if self.eml:
            if self.eml.name.endswith('.gz'):
                body = gzip.GzipFile(fileobj=self.eml).read()
            else:
                self.eml.open()
                body = self.eml.file.read()
                self.eml.close()
        else:
            body = self.get_body()
        flat = email.message_from_bytes(body)
        return self._rehydrate(flat)

    def delete(self, *args, **kwargs):
        """Delete this message and all stored attachments."""
        for attachment in self.attachments.all():
            # This attachment is attached only to this message.
            attachment.delete()
        return super(IncomingEmail, self).delete(*args, **kwargs)

    def __str__(self):
        return self.subject + ' from ' + ','.join(self.from_address)

    class Meta:
        verbose_name = _('Incoming email')
        verbose_name_plural = _('Incoming emails')


class IncomingAttachment(models.Model):
    message = models.ForeignKey(
        IncomingEmail,
        related_name='attachments',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('IncomingEmail'),
    )

    headers = models.TextField(
        _('Headers'),
        null=True,
        blank=True,
    )

    document = models.FileField(
        _('Document'),
        upload_to=get_attachment_save_path,
    )

    def delete(self, *args, **kwargs):
        """Deletes the attachment."""
        self.document.delete()
        return super(IncomingAttachment, self).delete(*args, **kwargs)

    def _get_rehydrated_headers(self):
        headers = self.headers
        if headers is None:
            return EmailMessage()
        return email.message_from_string(headers)

    def _set_dehydrated_headers(self, email_object):
        self.headers = email_object.as_string()

    def __delitem__(self, name):
        rehydrated = self._get_rehydrated_headers()
        del rehydrated[name]
        self._set_dehydrated_headers(rehydrated)

    def __setitem__(self, name, value):
        rehydrated = self._get_rehydrated_headers()
        rehydrated[name] = value
        self._set_dehydrated_headers(rehydrated)

    def get_filename(self):
        """Returns the original filename of this attachment."""
        file_name = self._get_rehydrated_headers().get_filename()
        if isinstance(file_name, str):
            result = convert_header_to_unicode(file_name)
            if result is None:
                return file_name
            return result
        else:
            return None

    def items(self):
        return self._get_rehydrated_headers().items()

    def __getitem__(self, name):
        value = self._get_rehydrated_headers()[name]
        if value is None:
            raise KeyError('Header %s does not exist' % name)
        return value

    def __str__(self):
        return self.document.url

    class Meta:
        verbose_name = _('IncomingEmail attachment')
        verbose_name_plural = _('IncomingEmail attachments')
