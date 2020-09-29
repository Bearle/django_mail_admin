from django.core.mail import send_mail 
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings
from django_mail_admin.mail import send
from django_mail_admin.settings import get_backend
from django_mail_admin.backends import CustomEmailBackend
from django_mail_admin.models import Outbox, OutgoingEmail


class ErrorRaisingBackend(BaseEmailBackend):
    """
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    """

    def send_messages(self, email_messages):
        raise Exception('Fake Error')


class BackendTest(TestCase):
    # @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_get_invalid_backend(self):
        with self.assertRaises(ValueError):
            send('from@example.com', backend='some_non_existing')

    @override_settings(DJANGO_MAIL_ADMIN={'EMAIL_BACKEND': 'test'})
    def test_old_settings(self):
        backend = get_backend()
        self.assertEqual(backend, 'test')

    @override_settings(DJANGO_MAIL_ADMIN={}, EMAIL_BACKEND='django_mail_admin.backends.CustomEmailBackend')
    def test_backend_fallback(self):
        backend = get_backend()
        self.assertEqual(backend, 'django_mail_admin.backends.CustomEmailBackend')

    def test_custom_email_backend(self):
        outbox = Outbox.objects.create(name='test', email_host='example.com',
                                       email_host_user='to@example.com', email_host_password='123456', active=True)
        backend = CustomEmailBackend()
        self.assertEqual(backend.host, outbox.email_host)
        self.assertEqual(backend.password, outbox.email_host_password)
        outbox.delete()
        with self.assertRaises(ValueError):
            backend2 = CustomEmailBackend()

    @override_settings(DJANGO_MAIL_ADMIN={}, EMAIL_BACKEND='django_mail_admin.backends.OutboxEmailBackend')
    def test_outbox_email_backend(self):
        count_before = len(OutgoingEmail.objects.all())
        sent_count = send_mail(
            subject='Test subject', message='message.', 
            from_email='from@example.com', recipient_list=['to@example.com'], 
            fail_silently=False)
        self.assertEqual(sent_count, 1)
        count_after = len(OutgoingEmail.objects.all())
        self.assertEqual(count_after, count_before + 1)
