from unittest.mock import MagicMock, patch

from django.core.mail import send_mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings
from django_mail_admin.mail import send
from django_mail_admin.settings import get_backend
from django_mail_admin.backends import CustomEmailBackend, GmailOAuth2Backend
from django_mail_admin.models import Outbox, OutgoingEmail


class ErrorRaisingBackend(BaseEmailBackend):
    """
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    """

    def send_messages(self, email_messages):
        raise Exception("Fake Error")


class BackendTest(TestCase):
    # @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_get_invalid_backend(self):
        with self.assertRaises(ValueError):
            send("from@example.com", backend="some_non_existing")

    @override_settings(DJANGO_MAIL_ADMIN={"EMAIL_BACKEND": "test"})
    def test_old_settings(self):
        backend = get_backend()
        self.assertEqual(backend, "test")

    @override_settings(
        DJANGO_MAIL_ADMIN={},
        EMAIL_BACKEND="django_mail_admin.backends.CustomEmailBackend",
    )
    def test_backend_fallback(self):
        backend = get_backend()
        self.assertEqual(backend, "django_mail_admin.backends.CustomEmailBackend")

    def test_custom_email_backend(self):
        outbox = Outbox.objects.create(
            name="test",
            email_host="example.com",
            email_host_user="to@example.com",
            email_host_password="123456",
            active=True,
        )
        backend = CustomEmailBackend()
        self.assertEqual(backend.host, outbox.email_host)
        self.assertEqual(backend.password, outbox.email_host_password)
        outbox.delete()
        with self.assertRaises(ValueError):
            backend2 = CustomEmailBackend()

    @override_settings(
        DJANGO_MAIL_ADMIN={},
        EMAIL_BACKEND="django_mail_admin.backends.OutboxEmailBackend",
    )
    def test_outbox_email_backend(self):
        count_before = len(OutgoingEmail.objects.all())
        sent_count = send_mail(
            subject="Test subject",
            message="message.",
            from_email="from@example.com",
            recipient_list=["to@example.com"],
            fail_silently=False,
        )
        self.assertEqual(sent_count, 1)
        count_after = len(OutgoingEmail.objects.all())
        self.assertEqual(count_after, count_before + 1)


class GmailOAuth2BackendConnectionFailureTest(TestCase):
    """Regression tests: an unavailable Gmail connection (dead/expired OAuth
    token, refresh_authorization() also failing) must fail the message, not
    silently drop it. Previously send_messages() just `continue`d past it —
    no exception, so OutgoingEmail.dispatch() (which only marks
    STATUS.failed when .send() actually raises) saw a clean return and
    marked the email STATUS.sent even though nothing was delivered.

    Both open() and _initialize_connection() are mocked so these don't need
    a real Outbox/UserSocialAuth/SMTP connection — only send_messages()'s
    own "no connection available" branch is under test.
    """

    def _message(self, from_email="broker@example.com"):
        message = MagicMock()
        message.from_email = from_email
        return message

    def test_raises_when_not_fail_silently(self):
        backend = GmailOAuth2Backend(fail_silently=False)
        with patch.object(backend, "_initialize_connection"), patch.object(
            GmailOAuth2Backend, "open", return_value=None
        ):
            with self.assertRaises(ConnectionError):
                backend.send_messages([self._message()])

    def test_logs_and_continues_when_fail_silently(self):
        """fail_silently=True must still not report a false send — the
        message is skipped (matches every other per-message failure path
        in this loop), not counted as sent."""
        backend = GmailOAuth2Backend(fail_silently=True)
        with patch.object(backend, "_initialize_connection"), patch.object(
            GmailOAuth2Backend, "open", return_value=None
        ):
            sent_count = backend.send_messages([self._message()])
        self.assertEqual(sent_count, 0)
