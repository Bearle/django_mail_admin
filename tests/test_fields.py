from django.test import TestCase
from django_mail_admin.fields import CommaSeparatedEmailField


class FieldsTest(TestCase):
    def test_formfield(self):
        field = CommaSeparatedEmailField('test')
        formfield = field.formfield()
        self.assertIn('invalid', formfield.error_messages)
