import logging
from django.db import models
from django.template import Template, Context
from django_mail_admin.models import OutgoingEmail
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


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

    subject = models.CharField(
        verbose_name=_("Subject"),
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
