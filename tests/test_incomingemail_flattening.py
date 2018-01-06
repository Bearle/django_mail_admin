import copy

import mock

from django_mail_admin import models, utils
from django_mail_admin.models import IncomingEmail
from .test_mailbox_base import EmailMessageTestCase
from django_mail_admin.settings import get_config


class TestIncomingEmailFlattening(EmailMessageTestCase):
    def test_quopri_message_is_properly_rehydrated(self):
        incoming_email_object = self._get_email_object(
            'message_with_many_multiparts.eml',
        )
        # Note: this is identical to the above, but it appears that
        # while reading-in an e-mail message, we do alter it slightly
        expected_email_object = self._get_email_object(
            'message_with_many_multiparts.eml',
        )
        models.TEXT_STORED_MIMETYPES = ['text/plain']

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_base64_message_is_properly_rehydrated(self):
        incoming_email_object = self._get_email_object(
            'message_with_attachment.eml',
        )
        # Note: this is identical to the above, but it appears that
        # while reading-in an e-mail message, we do alter it slightly
        expected_email_object = self._get_email_object(
            'message_with_attachment.eml',
        )

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_message_handles_rehydration_problems(self):
        incoming_email_object = self._get_email_object(
            'message_with_defective_attachment_association.eml',
        )
        expected_email_object = self._get_email_object(
            'message_with_defective_attachment_association_result.eml',
        )
        # Note: this is identical to the above, but it appears that
        # while reading-in an e-mail message, we do alter it slightly
        message = IncomingEmail()
        message.body = incoming_email_object.as_string()

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_message_content_type_stripping(self):
        incoming_email_object = self._get_email_object(
            'message_with_many_multiparts.eml',
        )
        expected_email_object = self._get_email_object(
            'message_with_many_multiparts_stripped_html.eml',
        )
        default_settings = get_config()
        with mock.patch('django_mail_admin.settings.get_config') as get_settings:
            altered = copy.deepcopy(default_settings)

            altered['STRIP_UNALLOWED_MIMETYPES'] = True
            altered['ALLOWED_MIMETYPES'] = ['text/plain']
            get_settings.return_value = altered

            msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_message_processing_unknown_encoding(self):
        incoming_email_object = self._get_email_object(
            'message_with_invalid_encoding.eml',
        )

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        expected_text = (
            "We offer loans to private individuals and corporate "
            "organizations at 2% interest rate. Interested serious "
            "applicants should apply via email with details of their "
            "requirements.\n\nWarm Regards,\nLoan Team"
        )
        actual_text = msg.text

        self.assertEqual(actual_text, expected_text)
