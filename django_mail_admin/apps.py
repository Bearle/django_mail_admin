# -*- coding: utf-8
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DjangoMailAdminConfig(AppConfig):
    name = 'django_mail_admin'
    verbose_name = _('Mail Admin')
