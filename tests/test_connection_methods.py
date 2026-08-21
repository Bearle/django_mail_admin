import unittest
from unittest.mock import patch, MagicMock

from django.test import TestCase

from django_mail_admin.models import Mailbox, Outbox


class MailboxConnectionTestCase(TestCase):
    """Test the Mailbox.test_connection method"""

    def setUp(self):
        self.mailbox = Mailbox.objects.create(
            name="Test IMAP Mailbox", uri="imap://user:password@example.com"
        )

    @patch("django_mail_admin.models.configurations.ImapTransport")
    def test_imap_connection_success(self, mock_imap):
        """Test successful IMAP connection"""
        # Set up the mock
        mock_connection = MagicMock()
        mock_connection.server.noop.return_value = True
        mock_imap.return_value = mock_connection

        # Test the connection
        success, message = self.mailbox.test_connection()

        # Verify the result
        self.assertTrue(success)
        self.assertIn("Successfully connected", message)
        mock_connection.server.noop.assert_called_once()

    @patch("django_mail_admin.models.configurations.ImapTransport")
    def test_imap_connection_failure(self, mock_imap):
        """Test failed IMAP connection"""
        # Set up the mock to raise an exception
        mock_connection = MagicMock()
        mock_connection.server.noop.side_effect = Exception("Connection refused")
        mock_imap.return_value = mock_connection

        # Test the connection
        success, message = self.mailbox.test_connection()

        # Verify the result
        self.assertFalse(success)
        self.assertIn("Connection failed", message)
        self.assertIn("Connection refused", message)


class OutboxConnectionTestCase(TestCase):
    """Test the Outbox.test_connection method"""

    def setUp(self):
        self.outbox = Outbox.objects.create(
            name="Test SMTP Outbox",
            email_host="smtp.example.com",
            email_host_user="user@example.com",
            email_host_password="password",
            email_port=587,
        )

    @patch("django_mail_admin.models.configurations.connections")
    def test_smtp_connection_success(self, mock_connections):
        """Test successful SMTP connection"""
        # Set up the mock
        mock_connection = MagicMock()
        mock_connection.connection.noop.return_value = True
        mock_connections.__getitem__.return_value = mock_connection

        # Test the connection
        success, message = self.outbox.test_connection()

        # Verify the result
        self.assertTrue(success)
        self.assertIn("Successfully connected", message)
        mock_connection.connection.noop.assert_called_once()

    @patch("django_mail_admin.models.configurations.connections")
    def test_smtp_connection_failure(self, mock_connections):
        """Test failed SMTP connection"""
        # Set up the mock to raise an exception
        mock_connection = MagicMock()
        mock_connection.connection.noop.side_effect = Exception("Authentication failed")
        mock_connections.__getitem__.return_value = mock_connection

        # Test the connection
        success, message = self.outbox.test_connection()

        # Verify the result
        self.assertFalse(success)
        self.assertIn("Connection failed", message)
        self.assertIn("Authentication failed", message)


if __name__ == "__main__":
    unittest.main()
