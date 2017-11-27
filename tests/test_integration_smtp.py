from django.test import TestCase
from django_mail_admin.models import Outbox, OutgoingEmail, PRIORITY, TemplateVariable, EmailTemplate
from django_mail_admin.mail import send, create
import os


class TestSmtp(TestCase):
    def setUp(self):
        self.test_smtp_server = os.environ.get('EMAIL_SMTP_SERVER')
        self.test_password = os.environ.get('EMAIL_PASSWORD')
        self.test_from_email = os.environ.get('EMAIL_ACCOUNT')
        self.test_account = self.test_from_email
        required_settings = [
            self.test_account,
            self.test_password,
            self.test_smtp_server,
            self.test_from_email,
        ]
        if not all(required_settings):
            self.skipTest(
                "Integration tests are not available without having "
                "the the following environment variables set: "
                "EMAIL_ACCOUNT, EMAIL_PASSWORD, EMAIL_SMTP_SERVER"
            )
        self.outbox = Outbox.objects.create(
            name='Integration Test SMTP',
            email_host=self.test_smtp_server,
            email_host_user=self.test_account,
            email_host_password=self.test_password,
            email_use_tls=True,
            active=True
        )

    def test_send_no_template(self):
        email = send(self.test_from_email, self.test_from_email, subject='Test', message='Testing',
                     priority=PRIORITY.now, backend='custom')

    def test_send_template(self):
        # First try it manually
        template = EmailTemplate.objects.create(name='first', description='desc', subject='{{id}}',
                                                email_html_text='{{id}}')
        email = create(self.test_from_email, self.test_from_email, template=template, priority=PRIORITY.now,
                       backend='custom')
        v = TemplateVariable.objects.create(name='id', value=1, email=email)
        email = OutgoingEmail.objects.get(id=1)
        email.dispatch()

        # Then try it with send()
        email = send(self.test_from_email, self.test_from_email, template=template, priority=PRIORITY.now,
                     backend='custom', variable_dict={'id': 1})
