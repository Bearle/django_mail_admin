from django.test import TestCase
from django_mail_admin.validators import validate_email_with_name, validate_comma_separated_emails
from django.core.exceptions import ValidationError


class ValidatorsTest(TestCase):
    def test_validate_comma_separated_emails(self):
        with self.assertRaises(ValidationError):
            validate_comma_separated_emails('a')

    def test_validate_email_with_name(self):
        with self.assertRaises(ValidationError):
            validate_email_with_name('><fckit')
        with self.assertRaises(ValidationError):
            validate_email_with_name('<test@example.com>>')
