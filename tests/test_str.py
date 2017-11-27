from django.test import TestCase
from django_mail_admin.models import OutgoingEmail, Log, EmailTemplate, TemplateVariable, STATUS, \
    create_attachments, Mailbox, Outbox, IncomingEmail, IncomingAttachment
from django.core.files.base import ContentFile


class ModelsStrTest(TestCase):
    def test_models_str(self):
        self.assertEqual(str(EmailTemplate(name='test')), 'test')
        self.assertEqual(str(TemplateVariable(name='test')), 'test')
        email = OutgoingEmail.objects.create(from_email='from@example.com', to=['test@example.com'],
                                             subject='test_subject')
        log = Log.objects.create(email=email, status=STATUS.sent)
        self.assertEqual(str(log), str(log.date))
        self.assertEqual(str(email),
                         "from@example.com -> ['test@example.com'] (test_subject)")
        attachments = create_attachments({
            'attachment_file1.txt': ContentFile('content'),
        })
        self.assertEqual(str(attachments[0]), 'attachment_file1.txt')
        mailbox = Mailbox.objects.create(from_email='from@example.com', name='example.com')
        self.assertEqual(str(mailbox), 'example.com')
        outbox = Outbox.objects.create(email_host_user='from', email_host='example.com', email_port='587')
        self.assertEqual(str(outbox), 'from@example.com:587')
        incoming_email = IncomingEmail.objects.create(mailbox=mailbox, subject='test')
        self.assertEqual(str(incoming_email), 'test')
