from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings

from django_mail_admin.models import OutgoingEmail, STATUS, PRIORITY
from django_mail_admin.settings import get_backend


class ErrorRaisingBackend(BaseEmailBackend):
    """
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    """

    def send_messages(self, email_messages):
        raise Exception('Fake Error')
