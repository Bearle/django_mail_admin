#!/usr/bin/env python
"""
Example script demonstrating how to test Mailbox and Outbox connections
using the new test_connection methods.

This script can be run from the command line to test connections for
all configured Mailboxes and Outboxes, or specific ones by ID.
"""

import os
import sys
import django
import argparse

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")
django.setup()

from django_mail_admin.models import Mailbox, Outbox


def test_mailbox_connection(mailbox_id=None):
    """
    Test connection for a specific mailbox or all mailboxes.

    Args:
        mailbox_id (int, optional): ID of the mailbox to test. If None, test all mailboxes.
    """
    if mailbox_id:
        try:
            mailboxes = [Mailbox.objects.get(id=mailbox_id)]
        except Mailbox.DoesNotExist:
            print(f"Mailbox with ID {mailbox_id} does not exist.")
            return
    else:
        mailboxes = Mailbox.objects.all()

    if not mailboxes:
        print("No mailboxes found.")
        return

    for mailbox in mailboxes:
        print(f"Testing connection for Mailbox: {mailbox.name} (ID: {mailbox.id})")
        success, message = mailbox.test_connection()
        status = "SUCCESS" if success else "FAILED"
        print(f"  Status: {status}")
        print(f"  Message: {message}")
        print()


def test_outbox_connection(outbox_id=None):
    """
    Test connection for a specific outbox or all outboxes.

    Args:
        outbox_id (int, optional): ID of the outbox to test. If None, test all outboxes.
    """
    if outbox_id:
        try:
            outboxes = [Outbox.objects.get(id=outbox_id)]
        except Outbox.DoesNotExist:
            print(f"Outbox with ID {outbox_id} does not exist.")
            return
    else:
        outboxes = Outbox.objects.all()

    if not outboxes:
        print("No outboxes found.")
        return

    for outbox in outboxes:
        print(f"Testing connection for Outbox: {outbox.name} (ID: {outbox.id})")
        success, message = outbox.test_connection()
        status = "SUCCESS" if success else "FAILED"
        print(f"  Status: {status}")
        print(f"  Message: {message}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test email connections for django_mail_admin."
    )
    parser.add_argument(
        "--mailbox", type=int, help="ID of the mailbox to test", default=None
    )
    parser.add_argument(
        "--outbox", type=int, help="ID of the outbox to test", default=None
    )
    parser.add_argument(
        "--all", action="store_true", help="Test all mailboxes and outboxes"
    )

    args = parser.parse_args()

    if args.mailbox:
        test_mailbox_connection(args.mailbox)
    elif args.outbox:
        test_outbox_connection(args.outbox)
    elif args.all:
        print("Testing all mailboxes:")
        test_mailbox_connection()
        print("\nTesting all outboxes:")
        test_outbox_connection()
    else:
        parser.print_help()
