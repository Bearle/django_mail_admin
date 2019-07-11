from mailbox import MH

from django_mail_admin.transports.generic import GenericFileMailbox


class MHTransport(GenericFileMailbox):
    _variant = MH
