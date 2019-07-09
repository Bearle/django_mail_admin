from mailbox import Babyl

from django_mail_admin.transports.generic import GenericFileMailbox


class BabylTransport(GenericFileMailbox):
    _variant = Babyl
