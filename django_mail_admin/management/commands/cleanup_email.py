import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from django_mail_admin.models import OutgoingEmail, IncomingEmail


class Command(BaseCommand):
    help = 'Place deferred messages back in the queue.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--days',
                            type=int,
                            default=90,
                            help="Cleanup mails older than this many days, defaults to 90."
                            )
        parser.add_argument('-i', '--incoming',
                            type=bool,
                            default=False,
                            help="Cleanup incoming mails (with attachments), defaults to False")
        parser.add_argument('-o', '--outgoing',
                            type=bool,
                            default=True,
                            help="Cleanup outgoing mails, defaults to False")

    def handle(self, verbosity, days, incoming, outgoing, **options):
        # Delete mails and their related logs and queued created before X days
        if not incoming and not outgoing:
            print("Please select either incoming or outgoing emails to delete. Exiting...")
        cutoff_date = now() - datetime.timedelta(days)
        if outgoing:
            count_outgoing = OutgoingEmail.objects.filter(created__lt=cutoff_date).count()
            OutgoingEmail.objects.only('id').filter(created__lt=cutoff_date).delete()
            print("Deleted {0} outgoing mails created before {1} ".format(count_outgoing, cutoff_date))
        if incoming:
            count_incoming = IncomingEmail.objects.filter(processed__lt=cutoff_date).count()
            IncomingEmail.objects.only('id').filter(processed__lt=cutoff_date).delete()
            print("Deleted {0} incoming mails processed before {1} ".format(count_incoming, cutoff_date))
