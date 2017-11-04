import logging
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django_mail_admin.models import EmailTemplate
from jsonfield import JSONField

logger = logging.getLogger(__name__)

PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))

#TODO: implement mailings
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

    @property
    def status(self):
        try:
            return self.post_office_email.get_status_display()
        except:
            return "-"

    status.fget.short_description = _("Status")

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


@receiver(signal=post_delete, sender=OutgoingEmail)
def delete_related(sender, instance, **kwargs):
    try:
        instance.post_office_email.delete()
    except:
        logger.warning(f"Related PostOffice object for {instance} not found.")
