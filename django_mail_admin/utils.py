import datetime
import email.header
import logging
import os
from collections import namedtuple
from django_mail_admin.settings import get_default_priority
from django.conf import settings
from .validators import validate_email_with_name
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


# TODO: merge post_office and these settings into 1
def get_settings():
    return {
        'strip_unallowed_mimetypes': getattr(
            settings,
            'DJANGO_MAILBOX_STRIP_UNALLOWED_MIMETYPES',
            False
        ),
        'allowed_mimetypes': getattr(
            settings,
            'DJANGO_MAILBOX_ALLOWED_MIMETYPES',
            [
                'text/plain',
                'text/html'
            ]
        ),
        'text_stored_mimetypes': getattr(
            settings,
            'DJANGO_MAILBOX_TEXT_STORED_MIMETYPES',
            [
                'text/plain',
                'text/html'
            ]
        ),
        'altered_message_header': getattr(
            settings,
            'DJANGO_MAILBOX_ALTERED_MESSAGE_HEADER',
            'X-Django-Mailbox-Altered-Message'
        ),
        'attachment_interpolation_header': getattr(
            settings,
            'DJANGO_MAILBOX_ATTACHMENT_INTERPOLATION_HEADER',
            'X-Django-Mailbox-Interpolate-Attachment'
        ),
        'attachment_upload_to': getattr(
            settings,
            'DJANGO_MAILBOX_ATTACHMENT_UPLOAD_TO',
            'mailbox_attachments/%Y/%m/%d/'
        ),
        'store_original_message': getattr(
            settings,
            'DJANGO_MAILBOX_STORE_ORIGINAL_MESSAGE',
            False
        ),
        'compress_original_message': getattr(
            settings,
            'DJANGO_MAILBOX_COMPRESS_ORIGINAL_MESSAGE',
            False
        ),
        'original_message_compression': getattr(
            settings,
            'DJANGO_MAILBOX_ORIGINAL_MESSAGE_COMPRESSION',
            6
        ),
        'default_charset': getattr(
            settings,
            'DJANGO_MAILBOX_default_charset',
            'iso8859-1',
        )
    }


def convert_header_to_unicode(header):
    default_charset = get_settings()['default_charset']

    def _decode(value, encoding):
        if isinstance(value, str):
            return value
        if not encoding or encoding == 'unknown-8bit':
            encoding = default_charset
        return value.decode(encoding, 'replace')

    try:
        return ''.join(
            [
                (
                    _decode(bytestr, encoding)
                ) for bytestr, encoding in email.header.decode_header(header)
            ]
        )
    except UnicodeDecodeError:
        logger.exception(
            'Errors encountered decoding header %s into encoding %s.',
            header,
            default_charset,
        )
        return header.decode(default_charset, 'replace')


def get_body_from_message(message, maintype, subtype):
    """
    Fetchs the body message matching main/sub content type.
    """
    body = ''
    for part in message.walk():
        if part.get_content_maintype() == maintype and \
                part.get_content_subtype() == subtype:
            charset = part.get_content_charset()
            this_part = part.get_payload(decode=True)
            if charset:
                try:
                    this_part = this_part.decode(charset, 'replace')
                except LookupError:
                    this_part = this_part.decode('ascii', 'replace')
                    logger.warning(
                        'Unknown encoding %s encountered while decoding '
                        'text payload.  Interpreting as ASCII with '
                        'replacement, but some data may not be '
                        'represented as the sender intended.',
                        charset
                    )
                except ValueError:
                    this_part = this_part.decode('ascii', 'replace')
                    logger.warning(
                        'Error encountered while decoding text '
                        'payload from an incorrectly-constructed '
                        'e-mail; payload was converted to ASCII with '
                        'replacement, but some data may not be '
                        'represented as the sender intended.'
                    )
            else:
                this_part = this_part.decode('ascii', 'replace')

            body += this_part

    return body


# TODO: deal with saving - links in admin seem to be broken
def get_attachment_save_path(instance, filename):
    _settings = get_settings()
    if hasattr(instance, 'name'):
        if not instance.name:
            instance.name = filename  # set original filename
    path = _settings['attachment_upload_to']
    if '%' in path:
        path = datetime.datetime.utcnow().strftime(path)

    return os.path.join(
        path,
        filename,
    )


def parse_priority(priority):
    if priority is None:
        priority = get_default_priority()
    # If priority is given as a string, returns the enum representation
    if isinstance(priority, str):
        priority = getattr(PRIORITY, priority, None)

        if priority is None:
            raise ValueError('Invalid priority, must be one of: %s' %
                             ', '.join(PRIORITY._fields))
    return priority


def parse_emails(emails):
    """
    A function that returns a list of valid email addresses.
    This function will also convert a single email address into
    a list of email addresses.
    None value is also converted into an empty list.
    """

    if isinstance(emails, str):
        emails = [emails]
    elif emails is None:
        emails = []

    for i in emails:
        try:
            validate_email_with_name(i)
        except ValidationError:
            raise ValidationError('%s is not a valid email address' % i)

    return emails


def split_emails(emails, split_count=1):
    # Group emails into X sublists
    # taken from http://www.garyrobinson.net/2008/04/splitting-a-pyt.html
    # Strange bug, only return 100 email if we do not evaluate the list
    if list(emails):
        return [emails[i::split_count] for i in range(split_count)]
