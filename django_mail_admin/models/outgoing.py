import logging
from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from .templates import EmailTemplate
from jsonfield import JSONField
from collections import namedtuple
from django_mail_admin.validators import validate_email_with_name
from django_mail_admin.fields import CommaSeparatedEmailField
from django_mail_admin.settings import context_field_class

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django_mail_admin.utils import get_attachment_save_path
import post_office

logger = logging.getLogger(__name__)

PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


# TODO: implement mailings
class OutgoingEmail(models.Model):
    PRIORITY_CHOICES = [(PRIORITY.low, _("low")), (PRIORITY.medium, _("medium")),
                        (PRIORITY.high, _("high")), (PRIORITY.now, _("now"))]
    STATUS_CHOICES = [(STATUS.sent, _("sent")), (STATUS.failed, _("failed")),
                      (STATUS.queued, _("queued"))]

    class Meta:
        verbose_name = _("Email letter")
        verbose_name_plural = _("Email letters")

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
        help_text=_("If template is selected, HTML message will not be used"),
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

    context = context_field_class(_('Context'), blank=True, null=True)
    backend_alias = models.CharField(_('Backend alias'), blank=True, default='',
                                     max_length=64)

    def __init__(self, *args, **kwargs):
        super(OutgoingEmail, self).__init__(*args, **kwargs)
        self._cached_email_message = None

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
        subject = self.subject

        if self.template is not None:
            _context = Context(self.context)
            subject = Template(self.template.subject).render(_context)
            message = Template(self.template.content).render(_context)
            html_message = Template(self.template.html_content).render(_context)

        else:
            subject = self.subject
            message = self.message
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

    @property
    def status(self):
        return self.get_status_display()

    def _get_context(self):
        context = {}
        for var in self.templatevariable_set.all().filter(email=self):
            context[var.name] = var.value

        return Context(context)

    def queue(self):
        if self.post_office_email:
            self.post_office_email.status = post_office_models.STATUS.queued
            self.post_office_email.save()

    def perform_email(self, send=True):
        # TODO: ensure that priority from admin saving is used correctly
        self.html_message = self.template.email_html_text_preview(self._get_context()) \
            if self.template else self.html_message
        self.subject = self.template.email_topic if self.template else self.subject
        headers = {'From': f'"{default_from_name()}" <{self.from_email}>'}
        if self.post_office_email:
            self.post_office_email.from_email = self.from_email
            self.post_office_email.headers = headers
            self.post_office_email.to = self.to
            self.post_office_email.subject = self.subject
            self.post_office_email.html_message = self.html_message
            self.post_office_email.scheduled_time = self.scheduled_time
            self.post_office_email.priority = post_office_models.PRIORITY.now if self.send_now \
                else post_office_models.PRIORITY.high
            # Set the status to queued again to re-send the email
            if send:
                self.queue()
            self.post_office_email.save()
        else:
            po_email = post_office_models.Email(
                from_email=self.from_email,
                headers=headers,
                to=self.to,
                subject=self.subject,
                html_message=self.html_message,
                scheduled_time=self.scheduled_time,
                priority=post_office_models.PRIORITY.now if self.send_now else post_office_models.PRIORITY.high
            )
            if send:
                self.queue()
            po_email.save()
            self.post_office_email = po_email

    def save(self, **kwargs):
        if 'send' in kwargs:
            send = kwargs.pop('send')
            super(OutgoingEmail, self).save(**kwargs)
            self.perform_email(send=send)
        else:
            super(OutgoingEmail, self).save(**kwargs)
            self.perform_email(send=False)

    def update_related(self):
        self.save(send=True)

    def __str__(self):
        return f"{self.from_email} -> {self.to} ({self.subject})"


class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    file = models.FileField(_('File'), upload_to=get_attachment_save_path)
    name = models.CharField(_('Name'), max_length=255, help_text=_("The original filename"))
    emails = models.ManyToManyField(OutgoingEmail, related_name='attachments',
                                    verbose_name=_('Email addresses'))
    mimetype = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        app_label = 'post_office'
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return self.name
