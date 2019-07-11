from mailbox import mbox

from django_mail_admin.transports.generic import GenericFileMailbox


class MboxTransport(GenericFileMailbox):
    _variant = mbox
