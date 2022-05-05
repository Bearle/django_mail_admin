import logging

from django.core.files import File
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import models
from django.template import Template, Context
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField

from django_mail_admin.connections import connections
from django_mail_admin.fields import CommaSeparatedEmailField
from django_mail_admin.settings import get_log_level, get_backend_names_str
from django_mail_admin.signals import email_sent, email_failed_to_send, email_queued
from django_mail_admin.utils import get_attachment_save_path, PRIORITY, STATUS
from django_mail_admin.validators import validate_email_with_name
from .templates import EmailTemplate

logger = logging.getLogger(__name__)


class OutgoingEmail(models.Model):
    PRIORITY_CHOICES = [(PRIORITY.low, _("low")), (PRIORITY.medium, _("medium")),
                        (PRIORITY.high, _("high")), (PRIORITY.now, _("now"))]
    STATUS_CHOICES = [(STATUS.sent, _("sent")), (STATUS.failed, _("failed")),
                      (STATUS.queued, _("queued"))]

    class Meta:
        verbose_name = _("Outgoing email")
        verbose_name_plural = _("Outgoing emails")

    from_email = models.CharField(
        verbose_name=_("From email"),
        max_length=254,
        validators=[validate_email_with_name]
    )

    to = CommaSeparatedEmailField(_("To email(s)"))
    cc = CommaSeparatedEmailField(_("Cc"))
    bcc = CommaSeparatedEmailField(_("Bcc"))

    template = models.ForeignKey(
        EmailTemplate,
        verbose_name=_("Template"),
        null=True,
        blank=True,
        help_text=_("If template is selected, HTML message and "
                    "subject fields will not be used - they will be populated from template"),
        on_delete=models.CASCADE
    )

    subject = models.CharField(
        verbose_name=_("Subject"),
        max_length=989,
        blank=True
    )
    message = models.TextField(_("Message"), blank=True)

    html_message = models.TextField(
        verbose_name=_("HTML Message"),
        blank=True,
        help_text=_("Used only if template is not selected")
    )
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)
    scheduled_time = models.DateTimeField(_('The scheduled sending time'),
                                          blank=True, null=True, db_index=True)
    headers = JSONField(_('Headers'), blank=True, null=True)

    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=STATUS_CHOICES, db_index=True,
        blank=True, null=True)
    priority = models.PositiveSmallIntegerField(_("Priority"),
                                                choices=PRIORITY_CHOICES,
                                                blank=True, null=True)

    send_now = models.BooleanField(
        verbose_name=_("Send now"),
        default=False
    )

    backend_alias = models.CharField(_('Backend alias'), blank=True, default='',
                                     help_text=get_backend_names_str,
                                     max_length=64)

    def __init__(self, *args, **kwargs):
        super(OutgoingEmail, self).__init__(*args, **kwargs)
        self._cached_email_message = None

    def _get_context(self):
        context = {}
        for var in self.templatevariable_set.all().filter(email=self):
            context[var.name] = var.value

        return Context(context)

    def email_message(self):
        """
        Returns Django EmailMessage object for sending.
        """
        if self._cached_email_message:
            return self._cached_email_message

        return self.prepare_email_message()

    def prepare_email_message(self):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object,
        depending on whether html_message is empty.
        """
        message = self.message
        if self.template is not None:
            _context = self._get_context()
            subject = self.template.render_subject(_context)
            html_message = self.template.render_html_text(_context)
        else:
            subject = self.subject
            html_message = self.html_message

        connection = connections[self.backend_alias or 'default']

        if html_message:
            msg = EmailMultiAlternatives(
                subject=subject, body=message, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc,
                headers=self.headers, connection=connection)
            msg.attach_alternative(html_message, "text/html")
        else:
            msg = EmailMessage(
                subject=subject, body=message, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc,
                headers=self.headers, connection=connection)

        for attachment in self.attachments.all():
            msg.attach(attachment.name, attachment.file.read(), mimetype=attachment.mimetype or None)
            attachment.file.close()

        self._cached_email_message = msg
        return msg

    def queue(self):
        self.status = STATUS.queued
        self.save()

    def dispatch(self, log_level=None, commit=True):
        """
        Sends email and log the result.
        """

        email_message = None
        # Priority is handled in mail.send
        try:
            email_message = self.email_message()
            email_message.send()
            status = STATUS.sent
            message = ''
            exception_type = ''
            email_sent.send(sender=self, outgoing_email=email_message)
        except Exception as e:
            status = STATUS.failed
            message = str(e)
            exception_type = type(e).__name__
            if email_message:
                email_failed_to_send.send(sender=self, outgoing_email=email_message)
            # If run in a bulk sending mode, reraise and let the outer
            # layer handle the exception
            if not commit:
                raise

        if commit:
            self.status = status
            self.save(update_fields=['status'])

            if log_level is None:
                log_level = get_log_level()

            # If log level is 0, log nothing, 1 logs only sending failures
            # and 2 means log both successes and failures
            if log_level == 1:
                if status == STATUS.failed:
                    self.logs.create(status=status, message=message,
                                     exception_type=exception_type)
            elif log_level == 2:
                self.logs.create(status=status, message=message,
                                 exception_type=exception_type)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(OutgoingEmail, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.from_email) + " -> " + str(self.to) + " (" + self.subject + ")"


class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    file = models.FileField(_('File'), upload_to=get_attachment_save_path)
    name = models.CharField(_('Name'), max_length=255, help_text=_("The original filename"))
    emails = models.ManyToManyField(OutgoingEmail, related_name='attachments', blank=True,
                                    verbose_name=_('Email addresses'))
    mimetype = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return self.name


def create_attachments(attachment_files):
    """
    Create Attachment instances from files

    attachment_files is a dict of:
        * Key - the filename to be used for the attachment.
        * Value - file-like object, or a filename to open OR a dict of {'file': file-like-object, 'mimetype': string}

    Returns a list of Attachment objects
    """
    attachments = []
    for filename, filedata in attachment_files.items():

        if isinstance(filedata, dict):
            content = filedata.get('file', None)
            mimetype = filedata.get('mimetype', None)
        else:
            content = filedata
            mimetype = None

        opened_file = None

        if isinstance(content, str):
            # `content` is a filename - try to open the file
            opened_file = open(content, 'rb')
            content = File(opened_file)

        attachment = Attachment()
        if mimetype:
            attachment.mimetype = mimetype
        attachment.file.save(filename, content=content, save=True)

        attachments.append(attachment)

        if opened_file is not None:
            opened_file.close()

    return attachments


def send_mail(subject, message, from_email, recipient_list, html_message='',
              scheduled_time=None, headers=None, priority=PRIORITY.medium):
    """
    Add a new message to the mail queue. This is a replacement for Django's
    ``send_mail`` core email method.
    """

    subject = force_str(subject)
    status = None if priority == PRIORITY.now else STATUS.queued
    emails = []
    for address in recipient_list:
        emails.append(
            OutgoingEmail.objects.create(
                from_email=from_email, to=address, subject=subject,
                message=message, html_message=html_message, status=status,
                headers=headers, priority=priority, scheduled_time=scheduled_time
            )
        )
    if priority == PRIORITY.now:
        for email in emails:
            email.dispatch()
    else:
        for email in emails:
            email_queued.send(email)
    return emails
