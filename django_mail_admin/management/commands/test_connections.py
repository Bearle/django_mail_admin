import logging
from django.core.management.base import BaseCommand, CommandError
from django_mail_admin.models import Mailbox, Outbox

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test connections for Mailboxes and Outboxes"

    def add_arguments(self, parser):
        parser.add_argument("--mailbox", type=int, help="ID of the mailbox to test")
        parser.add_argument("--outbox", type=int, help="ID of the outbox to test")
        parser.add_argument(
            "--all", action="store_true", help="Test all mailboxes and outboxes"
        )

    def handle(self, *args, **options):
        mailbox_id = options.get("mailbox")
        outbox_id = options.get("outbox")
        test_all = options.get("all")

        if not any([mailbox_id, outbox_id, test_all]):
            self.stdout.write(
                self.style.WARNING("Please specify --mailbox, --outbox, or --all")
            )
            return

        if mailbox_id:
            self.test_mailbox(mailbox_id)
        elif outbox_id:
            self.test_outbox(outbox_id)
        elif test_all:
            self.test_all_mailboxes()
            self.test_all_outboxes()

    def test_mailbox(self, mailbox_id):
        """Test connection for a specific mailbox"""
        try:
            mailbox = Mailbox.objects.get(id=mailbox_id)
            self.stdout.write(
                f"Testing connection for Mailbox: {mailbox.name} (ID: {mailbox.id})"
            )
            success, message = mailbox.test_connection()

            if success:
                self.stdout.write(self.style.SUCCESS(f"  SUCCESS: {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"  FAILED: {message}"))

        except Mailbox.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Mailbox with ID {mailbox_id} does not exist.")
            )

    def test_outbox(self, outbox_id):
        """Test connection for a specific outbox"""
        try:
            outbox = Outbox.objects.get(id=outbox_id)
            self.stdout.write(
                f"Testing connection for Outbox: {outbox.name} (ID: {outbox.id})"
            )
            success, message = outbox.test_connection()

            if success:
                self.stdout.write(self.style.SUCCESS(f"  SUCCESS: {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"  FAILED: {message}"))

        except Outbox.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Outbox with ID {outbox_id} does not exist.")
            )

    def test_all_mailboxes(self):
        """Test connections for all mailboxes"""
        mailboxes = Mailbox.objects.all()

        if not mailboxes:
            self.stdout.write(self.style.WARNING("No mailboxes found."))
            return

        self.stdout.write(self.style.NOTICE("Testing all mailboxes:"))
        for mailbox in mailboxes:
            self.stdout.write(
                f"Testing connection for Mailbox: {mailbox.name} (ID: {mailbox.id})"
            )
            success, message = mailbox.test_connection()

            if success:
                self.stdout.write(self.style.SUCCESS(f"  SUCCESS: {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"  FAILED: {message}"))

    def test_all_outboxes(self):
        """Test connections for all outboxes"""
        outboxes = Outbox.objects.all()

        if not outboxes:
            self.stdout.write(self.style.WARNING("No outboxes found."))
            return

        self.stdout.write(self.style.NOTICE("Testing all outboxes:"))
        for outbox in outboxes:
            self.stdout.write(
                f"Testing connection for Outbox: {outbox.name} (ID: {outbox.id})"
            )
            success, message = outbox.test_connection()

            if success:
                self.stdout.write(self.style.SUCCESS(f"  SUCCESS: {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"  FAILED: {message}"))
