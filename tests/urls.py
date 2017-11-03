# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include

from django_mail_admin.urls import urlpatterns as django_mail_admin_urls

urlpatterns = [
    url(r'^', include(django_mail_admin_urls, namespace='django_mail_admin')),
]
