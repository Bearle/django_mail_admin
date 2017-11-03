# -*- coding: utf-8 -*-
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import models
from django.template import Template, Context
from django.utils.translation import ugettext_lazy as _
from post_office import models as post_office_models
from post_office.fields import CommaSeparatedEmailField
from django_mailbox.models import Mailbox
from ckeditor.fields import RichTextField

logger = logging.getLogger(__name__)
# Hack for not overriding model
Mailbox.__str__ = lambda obj: obj.name


def default_from_email():
    mailbox = Mailbox.objects.filter(active=True).first()
    if mailbox:
        return mailbox.from_email


def default_from_name():
    mailbox = Mailbox.objects.filter(active=True).first()
    if mailbox:
        return mailbox.name


class EmailTemplate(models.Model):
    # TODO: add description about vars availiable
    class Meta:
        verbose_name = _('Email template')
        verbose_name_plural = _('Email templates')

    name = models.CharField(
        verbose_name=_("Template name"),
        max_length=254
    )

    description = models.TextField(
        verbose_name=_("Template description"),
        blank=True
    )

    email_topic = models.CharField(
        verbose_name=_("Email topic"),
        max_length=254,
        blank=False
    )

    email_text = models.TextField(
        verbose_name=_("Email text"),
        blank=True
    )

    email_html_text = RichTextField(
        verbose_name=_("Email html text"),
        blank=True
    )

    def email_text_preview(self, context):
        try:
            template = Template(self.email_text)
            return template.render(context)
        except Exception:
            return _("Error template rendering")

    def email_html_text_preview(self, context):
        try:
            template = Template(self.email_html_text)
            return template.render(context)
        except Exception:
            return _("Error template rendering")

    def __str__(self):
        return self.name


class OutgoingEmail(models.Model):
    class Meta:
        verbose_name = _("Email letter")
        verbose_name_plural = _("Email letters")

    from_email = models.CharField(
        verbose_name=_("From email"),
        max_length=254,
        default=default_from_email
    )

    to = CommaSeparatedEmailField(
        verbose_name=_("To email(s)"),
    )

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
        max_length=254,
        blank=True
    )

    html_message = RichTextField(
        verbose_name=_("HTML Message"),
        blank=True,
        help_text=_("Used only if template is not selected")
    )

    scheduled_time = models.DateTimeField(
        verbose_name=_('The scheduled sending time'),
        null=True,
        blank=True
    )

    send_now = models.BooleanField(
        verbose_name=_("Send now"),
        default=False
    )

    post_office_email = models.OneToOneField(
        post_office_models.Email,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

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


class TemplateVariable(models.Model):
    class Meta:
        verbose_name = _("Template variable")
        verbose_name_plural = _("Template variables")

    email = models.ForeignKey(
        OutgoingEmail,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        verbose_name=_("Variable name"),
        max_length=254,
        blank=False
    )

    value = models.TextField(
        verbose_name=_("Variable value"),
        blank=True
    )

    def __str__(self):
        return self.name

class EmailConfiguration(models.Model):
    name = models.CharField('Name', max_length=255)
    email_use_tls = models.BooleanField('EMAIL_USE_TLS', default=True)
    email_use_ssl = models.BooleanField('EMAIL_USE_SSL', default=False)
    email_ssl_keyfile = models.CharField('EMAIL_SSL_KEYFILE', max_length=1024, null=True, blank=True)
    email_ssl_certfile = models.CharField('EMAIL_SSL_CERTFILE', max_length=1024, null=True, blank=True)
    email_host = models.CharField('EMAIL_HOST', max_length=1024)
    email_host_user = models.CharField('EMAIL_HOST_USER', max_length=255)
    email_host_password = models.CharField('EMAIL_HOST_PASSWORD', max_length=255)
    email_port = models.PositiveSmallIntegerField('EMAIL_PORT', default=587)
    email_timeout = models.PositiveSmallIntegerField('EMAIL_TIMEOUT', null=True, blank=True)
    active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.active:
            # select all other active items
            qs = type(self).objects.filter(active=True)
            # except self (if self already exists)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            # and deactive them
            qs.update(active=False)

        super(EmailConfiguration, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.email_host_user}@{self.email_host}:{self.email_port}"
