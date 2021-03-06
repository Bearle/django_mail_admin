import django
import copy
from datetime import timedelta
from django.utils import timezone
from django.core import mail
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.forms.models import modelform_factory
from django.test import TestCase
from django.test.utils import override_settings
from django_mail_admin.models import OutgoingEmail, Log, PRIORITY, STATUS, EmailTemplate, Attachment, TemplateVariable
from django_mail_admin.mail import send, send_many, get_queued


class OutgoingModelTest(TestCase):
    def test_email_message(self):
        """
        Test to make sure that model's "email_message" method
        returns proper email classes.
        """

        # If ``html_message`` is set, ``EmailMultiAlternatives`` is expected
        email = OutgoingEmail.objects.create(to=['to@example.com'],
                                             from_email='from@example.com', subject='Subject',
                                             message='Message', html_message='<p>HTML</p>')
        message = email.email_message()
        self.assertEqual(type(message), EmailMultiAlternatives)
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')
        self.assertEqual(message.alternatives, [('<p>HTML</p>', 'text/html')])

        # Without ``html_message``, ``EmailMessage`` class is expected
        email = OutgoingEmail.objects.create(to=['to@example.com'],
                                             from_email='from@example.com', subject='Subject',
                                             message='Message')
        message = email.email_message()
        self.assertEqual(type(message), EmailMessage)
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')

    def test_email_message_queue(self):
        email = OutgoingEmail.objects.create(to=['to@example.com'],
                                             from_email='from@example.com', subject='Subject',
                                             message='Message', html_message='<p>HTML</p>')
        email.queue()
        self.assertEqual(OutgoingEmail.objects.filter(status=STATUS.queued).count(), 1)

    def test_email_message_render(self):
        """
        Ensure Email instance with template is properly rendered.
        """
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            email_html_text='Content {{ name }}'
        )

        email = OutgoingEmail.objects.create(to=['to@example.com'], template=template,
                                             from_email='from@e.com')
        var1 = TemplateVariable.objects.create(name='name', value='test', email=email)
        message = email.email_message()
        self.assertEqual(message.subject, 'Subject test')
        self.assertEqual(message.alternatives[0][0], 'Content test')

    def test_dispatch(self):
        """
        Ensure that email.dispatch() actually sends out the email
        """
        email = OutgoingEmail.objects.create(to=['to@example.com'], from_email='from@example.com',
                                             subject='Test dispatch', message='Message', backend_alias='locmem')
        email.dispatch()
        self.assertEqual(mail.outbox[0].subject, 'Test dispatch')

    def test_status_and_log(self):
        """
        Ensure that status and log are set properly on successful sending
        """
        email = OutgoingEmail.objects.create(to=['to@example.com'], from_email='from@example.com',
                                             subject='Test', message='Message', backend_alias='locmem', id=333)
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(log.email, email)

    @override_settings(DJANGO_MAIL_ADMIN={'LOG_LEVEL': 1})
    def test_log_levels(self):
        # Logs with LOG_LEVEL=1 should only be created when email failed to send
        email = OutgoingEmail.objects.create(to=['to@example.com'], from_email='from@example.com',
                                             subject='Test', message='Message', backend_alias='locmem', id=333)
        email.dispatch()
        log = list(Log.objects.all())
        self.assertEqual(log, [])
        email = OutgoingEmail.objects.create(to=['to@example.com'], from_email='from@example.com',
                                             subject='Test', message='Message',
                                             backend_alias='error')
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(log.email, email)

    def test_status_and_log_on_error(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = OutgoingEmail.objects.create(to=['to@example.com'], from_email='from@example.com',
                                             subject='Test', message='Message',
                                             backend_alias='error')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertEqual(log.message, 'Fake Error')
        self.assertEqual(log.exception_type, 'Exception')

    def test_errors_while_getting_connection_are_logged(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = OutgoingEmail.objects.create(to=['to@example.com'], subject='Test',
                                             from_email='from@example.com',
                                             message='Message', backend_alias='random')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertIn('is not a valid', log.message)

    def test_send_argument_checking(self):
        """
        mail.send() should raise an Exception if:
        - "template" is used with "subject", "message" or "html_message"
        - recipients is not in tuple or list format
        """
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', subject='bar')
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', message='bar')
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', html_message='bar')
        self.assertRaises(ValueError, send, 'to@example.com', 'from@a.com',
                          template='foo', html_message='bar')
        self.assertRaises(ValueError, send, cc='cc@example.com', sender='from@a.com',
                          template='foo', html_message='bar')
        self.assertRaises(ValueError, send, bcc='bcc@example.com', sender='from@a.com',
                          template='foo', html_message='bar')

    def test_send_with_template(self):
        """
        Ensure mail.send correctly creates templated emails to recipients
        """
        OutgoingEmail.objects.all().delete()
        headers = {'Reply-to': 'reply@email.com'}
        email_template = EmailTemplate.objects.create(name='foo', subject='{{bar}}',
                                                      email_html_text='{{baz}} {{booz}}')
        scheduled_time = timezone.now() + timedelta(days=1)
        email = send(recipients=['to1@example.com', 'to2@example.com'], sender='from@a.com',
                     headers=headers, template=email_template,
                     scheduled_time=scheduled_time)
        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.headers, headers)
        self.assertEqual(email.scheduled_time, scheduled_time)

        # Test without header
        OutgoingEmail.objects.all().delete()
        email = send(recipients=['to1@example.com', 'to2@example.com'], sender='from@a.com',
                     template=email_template)
        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.headers, None)

        # Now with variables
        context = {'bar': 'foo', 'baz': 5, 'booz': (6, 7)}
        OutgoingEmail.objects.all().delete()
        email = send(recipients=['to1@example.com', 'to2@example.com'], sender='from@a.com',
                     template=email_template, variable_dict=context)
        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.headers, None)
        email_message = email.email_message()
        self.assertEqual(email_message.subject, context['bar'])
        self.assertEqual(email_message.alternatives[0][0], str(context['baz']) + " " + str(context['booz']))

        # Now with tags
        OutgoingEmail.objects.all().delete()
        email_template_tags = \
            EmailTemplate.objects.create(name='foo',
                                         subject='{{bar|capfirst}}',
                                         email_html_text='{{ baz }} {{ booz|first }}')
        email = send(recipients=['to1@example.com', 'to2@example.com'], sender='from@a.com',
                     template=email_template_tags, variable_dict=context)
        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.headers, None)
        email_message = email.email_message()
        self.assertEqual(email_message.subject, context['bar'][0].upper() + context['bar'][1:])
        self.assertEqual(email_message.alternatives[0][0], str(context['baz']) + " " + "(")

    def test_send_without_template(self):
        headers = {'Reply-to': 'reply@email.com'}
        scheduled_time = timezone.now() + timedelta(days=1)
        email = send(sender='from@a.com',
                     recipients=['to1@example.com', 'to2@example.com'],
                     cc=['cc1@example.com', 'cc2@example.com'],
                     bcc=['bcc1@example.com', 'bcc2@example.com'],
                     subject='foo', message='bar', html_message='baz',
                     headers=headers,
                     scheduled_time=scheduled_time, priority=PRIORITY.low)

        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.cc, ['cc1@example.com', 'cc2@example.com'])
        self.assertEqual(email.bcc, ['bcc1@example.com', 'bcc2@example.com'])
        self.assertEqual(email.subject, 'foo')
        self.assertEqual(email.message, 'bar')
        self.assertEqual(email.html_message, 'baz')
        self.assertEqual(email.headers, headers)
        self.assertEqual(email.priority, PRIORITY.low)
        self.assertEqual(email.scheduled_time, scheduled_time)

    def test_invalid_syntax(self):
        """
        Ensures that invalid template syntax will result in validation errors
        when saving a ModelForm of an EmailTemplate.
        """
        data = dict(
            name='cost',
            subject='Hi there!{{ }}',
            email_html_text='Welcome {{ name|titl }} to the site.'
        )

        EmailTemplateForm = modelform_factory(EmailTemplate, exclude=['template'])
        form = EmailTemplateForm(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['email_html_text'], [u"Invalid filter: 'titl'"])
        self.assertIn(form.errors['subject'],
                      [[u'Empty variable tag'], [u'Empty variable tag on line 1']])

    def test_string_priority(self):
        """
        Regression test for:
        https://github.com/ui/django-post_office/issues/23
        """
        email = send('from@a.com', ['to1@example.com'], priority='low')
        self.assertEqual(email.priority, PRIORITY.low)

    def test_default_priority(self):
        email = send(recipients=['to1@example.com'], sender='from@a.com')
        self.assertEqual(email.priority, PRIORITY.medium)

    def test_string_priority_exception(self):
        invalid_priority_send = lambda: send(['to1@example.com'], 'from@a.com', priority='hgh')

        with self.assertRaises(ValueError) as context:
            invalid_priority_send()

        self.assertEqual(
            str(context.exception),
            'Invalid priority, must be one of: low, medium, high, now'
        )

    def test_send_recipient_display_name(self):
        """
        Regression test for:
        https://github.com/ui/django-post_office/issues/73
        """
        email = send(recipients=['Alice Bob <email@example.com>'], sender='from@a.com')
        self.assertTrue(email.to)

    def test_attachment_filename(self):
        attachment = Attachment()

        attachment.file.save(
            'test.txt',
            content=ContentFile('test file content'),
            save=True
        )
        self.assertEqual(attachment.name, 'test.txt')

    def test_attachments_email_message(self):
        email = OutgoingEmail.objects.create(to=['to@example.com'],
                                             from_email='from@example.com',
                                             subject='Subject')

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
        email.attachments.add(attachment)
        message = email.email_message()

        # https://docs.djangoproject.com/en/1.11/releases/1.11/#email
        if django.VERSION >= (1, 11,):
            self.assertEqual(message.attachments,
                             [('test.txt', 'test file content', 'text/plain')])
        else:
            self.assertEqual(message.attachments,
                             [('test.txt', b'test file content', None)])

    def test_attachments_email_message_with_mimetype(self):
        email = OutgoingEmail.objects.create(to=['to@example.com'],
                                             from_email='from@example.com',
                                             subject='Subject')

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
        attachment.mimetype = 'text/plain'
        attachment.save()
        email.attachments.add(attachment)
        message = email.email_message()

        if django.VERSION >= (1, 11,):
            self.assertEqual(message.attachments,
                             [('test.txt', 'test file content', 'text/plain')])
        else:
            self.assertEqual(message.attachments,
                             [('test.txt', b'test file content', 'text/plain')])

    def test_models_str(self):
        self.assertEqual(str(Attachment(name='test')), 'test')
        self.assertEqual(str(EmailTemplate(name='test')),
                         'test')

    def test_send_many(self):
        emails = [dict(sender='from@a.com',
                       recipients=['to1@example.com', 'to2@example.com'],
                       cc=['cc1@example.com', 'cc2@example.com'],
                       bcc=['bcc1@example.com', 'bcc2@example.com'],
                       subject='foo', message='bar', html_message='baz'),
                  dict(sender='from@a.com',
                       recipients=['to3@example.com', 'to4@example.com'],
                       cc=['cc3@example.com', 'cc4@example.com'],
                       bcc=['bcc3@example.com', 'bcc4@example.com'],
                       subject='fooo', message='barr', html_message='bazz'),
                  ]
        with self.assertRaises(ValueError):
            emails_falsy = copy.deepcopy(emails)
            emails_falsy[0]['priority'] = PRIORITY.now
            send_many(emails_falsy)
        with self.assertRaises(ValueError):
            emails_falsy = copy.deepcopy(emails)
            attachment = Attachment()
            attachment.file.save(
                'test.txt', content=ContentFile('test file content'), save=True
            )
            attachment.mimetype = 'text/plain'
            attachment.save()
            emails_falsy[0]['attachments'] = [attachment]
            send_many(emails_falsy)
        send_many(emails)
        queued = get_queued()
        self.assertEqual(queued.count(), 2)
