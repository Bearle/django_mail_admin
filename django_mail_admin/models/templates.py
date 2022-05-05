import logging

from django.db import models
from django.template import Template
from django.utils.translation import gettext_lazy as _

from django_mail_admin.validators import validate_template_syntax

logger = logging.getLogger(__name__)


# TODO: implement cache usage as in post_office
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
        blank=False,
        validators=[validate_template_syntax]
    )

    email_html_text = models.TextField(
        verbose_name=_("Email html text"),
        blank=True,
        validators=[validate_template_syntax]
    )

    def render_html_text(self, context):
        template = Template(self.email_html_text)
        return template.render(context)

    def render_subject(self, context):
        template = Template(self.subject)
        return template.render(context)

    def __str__(self):
        return self.name


class TemplateVariable(models.Model):
    class Meta:
        verbose_name = _("Template variable")
        verbose_name_plural = _("Template variables")

    email = models.ForeignKey(
        'OutgoingEmail',
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
