from django.test import TestCase
from django_mail_admin.models import Outbox
from django.core.exceptions import ValidationError
from django.forms.models import modelform_factory


class OutgoingModelTest(TestCase):
    def test_outbox_save(self):
        outbox1 = Outbox.objects.create(name='first',
                                        email_host='nowhere@example.com',
                                        email_host_user='nobody@example.com',
                                        email_host_password='11111',
                                        active=True)
        self.assertTrue(outbox1.active)
        outbox2 = Outbox(name='second',
                         email_host='nowhere@example.com',
                         email_host_user='nobody@example.com',
                         email_host_password='11111',
                         active=True)
        self.assertTrue(outbox1.active)
        outbox2.save()
        self.assertTrue(outbox2.active)
        outbox1 = Outbox.objects.get(name='first')
        self.assertFalse(outbox1.active)

    def test_outbox_clean(self):
        OutboxForm = modelform_factory(Outbox, exclude=['outbox'])
        data = dict(name='first',
                    email_host='nowhere@example.com',
                    email_host_user='nobody@example.com',
                    email_host_password='11111',
                    email_port=587,
                    email_use_ssl=True,
                    email_use_tls=True,
                    active=True)
        form = OutboxForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertTrue('__all__' in form.errors.keys())
