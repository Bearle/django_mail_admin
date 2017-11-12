#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_django_mail_admin
------------

Tests for `django_mail_admin` models module.
"""

from django.test import TestCase

from django_mail_admin.models import TemplateVariable, OutgoingEmail, EmailTemplate, EmailConfiguration


class TestDjango_mail_admin(TestCase):
    def setUp(self):
        var = TemplateVariable.objects.create(name='Hello', value='Test')

    def test_something(self):
        pass

    def tearDown(self):
        pass
