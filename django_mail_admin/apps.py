# -*- coding: utf-8
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoMailAdminConfig(AppConfig):
    name = 'django_mail_admin'
    verbose_name = _('Mail Admin')
    default_auto_field = 'django.db.models.AutoField'
