import logging
import base64
import smtplib
import ssl
import threading
from typing import Optional
from urllib import parse

from django.core.mail.backends.smtp import EmailBackend
from django_mail_admin.models.outgoing import EmailAddressOAuthMapping
from django_mail_admin.transports import (
    ImapTransport,
)

from .mail import create
from .models import Outbox, Mailbox, create_attachments
from .utils import PRIORITY

from social_django.models import UserSocialAuth
from django.core.mail.backends.base import BaseEmailBackend

from django_mail_admin.o365_utils import O365Connection
from django_mail_admin.google_utils import generate_oauth2_string, refresh_authorization

logger = logging.getLogger(__name__)


class CustomEmailBackend(EmailBackend):
    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=False,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs,
    ):
        super(CustomEmailBackend, self).__init__(fail_silently=fail_silently)
        # March2025 Note: keeping active=True in case we use this.
        # if we copy this we should add Outbox.email_host_user filtering like O365/Gmail backends
        configurations = Outbox.objects.filter(active=True)
        if len(configurations) > 1 or len(configurations) == 0:
            raise ValueError(
                "Got %(l)s active Outboxes, expected 1" % {"l": len(configurations)}
            )
        else:
            configuration = configurations.first()
        self.host = host or configuration.email_host
        self.port = port or configuration.email_port
        self.username = configuration.email_host_user if username is None else username
        self.password = (
            configuration.email_host_password if password is None else password
        )
        self.use_tls = configuration.email_use_tls if use_tls is None else use_tls
        self.use_ssl = configuration.email_use_ssl if use_ssl is None else use_ssl
        self.timeout = configuration.email_timeout if timeout is None else timeout
        self.ssl_keyfile = (
            configuration.email_ssl_keyfile if ssl_keyfile is None else ssl_keyfile
        )
        self.ssl_certfile = (
            configuration.email_ssl_certfile if ssl_certfile is None else ssl_certfile
        )
        self.connection = None
        self._lock = threading.RLock()


class SMTPOutboxBackend(EmailBackend):
    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=False,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs,
    ):
        super(SMTPOutboxBackend, self).__init__(fail_silently=fail_silently)
        self.host = None
        self.port = None
        self.username = None
        self.password = None
        self.use_tls = None
        self.use_ssl = None
        self.timeout = None
        self.ssl_keyfile = None
        self.ssl_certfile = None
        self.conn: Optional[SMTPOutboxBackend] | None = None
        self.connection = None
        # from_email might be hydrated by us (ChargeUp) in a few scenarios:
        # 1. after class __init__ (Django will create this class so we can't add directly to __init__)
        # 2. during email sending when a new connection needs to be opened
        self.from_email: str | None = None
        self.configuration_id: Optional[int] = None

        self._lock = threading.RLock()

    def close(self):
        """Closes and cleans up the current connection"""
        with self._lock:
            if self.conn:
                self.conn = None
                self.from_email = None
                self.configuration_id = None
            super().close()

    def get_password(self, outbox: Outbox):
        return outbox.email_host_password

    def open(self):
        with self._lock:
            outbox = Outbox.objects.filter(
                email_host_user__iexact=self.from_email  # ignore case
            ).first()

            if not outbox:
                raise ValueError(
                    f"Unable to find an Outbox with email_host_user={self.from_email}"
                )

            # existing saved connection is valid. no need for a new one
            if self.configuration_id and self.configuration_id == outbox.id:
                return
            elif self.configuration_id:
                # close the existing invalid connection
                self.from_email = outbox.email_host_user
                self.configuration_id = outbox.id

            self.host = outbox.email_host
            self.port = outbox.email_port
            self.username = outbox.email_host_user
            self.password = self.get_password(outbox)
            self.use_tls = outbox.email_use_tls
            self.use_ssl = outbox.email_use_ssl
            self.timeout = outbox.email_timeout
            self.ssl_keyfile = outbox.email_ssl_keyfile
            self.ssl_certfile = outbox.email_ssl_certfile

            return super().open()

    def _get_imap_sent_folder_name(
        self, imap_transport: ImapTransport | None
    ) -> str | None:
        sent_folder: str | None = None
        try:
            if imap_transport:
                sent_folder = imap_transport.get_sent_folder_name()
        except Exception as e:
            logger.error(
                f"Error retrieving sent folder name: imap_transport: {imap_transport},error: {e}"
            )
            sent_folder = None
        return sent_folder

    def _get_imap_transport(self) -> ImapTransport | None:
        imap_transport: ImapTransport | None = None
        try:
            imap_mailbox: Mailbox | None = None
            for imap_mailbox in Mailbox.objects.filter(
                from_email__iexact=self.from_email
            ).all():
                if imap_mailbox and "imap" == imap_mailbox.type:
                    break
            if imap_mailbox and "imap" == imap_mailbox.type:
                imap_transport = imap_mailbox.get_connection()
        except Exception as e:
            logger.error(f"Error retrieving imap_transport: {e}")
            imap_transport = None
        return imap_transport

    def send_messages(self, email_messages) -> int:
        """
        Sends email messages via underlying SMTP connection and saves the same to Sent folder

        SMTP only sends messages, do not deal with ensuring a copy is stored in sent folder
        """
        if not email_messages:
            return 0
        num_sent_ok = 0
        with self._lock:
            imap_transport: ImapTransport | None = self._get_imap_transport()
            sent_folder: str | None = self._get_imap_sent_folder_name(imap_transport)
            for email_message in email_messages:
                num_sent = super().send_messages([email_message])
                if 1 != num_sent:
                    continue
                if imap_transport and sent_folder:
                    imap_transport.store_message_in_folder(
                        sent_folder, email_message.message()
                    )  # not sending any flags
                num_sent_ok += 1
        return num_sent_ok


class OutboxEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        for msg in email_messages:
            try:
                email = create(
                    sender=msg.from_email,
                    recipients=msg.to,
                    cc=msg.cc,
                    bcc=msg.bcc,
                    subject=msg.subject,
                    message=msg.body,
                    headers=msg.extra_headers,
                    priority=PRIORITY.medium,
                )
                alternatives = getattr(msg, "alternatives", [])
                for content, mimetype in alternatives:
                    if mimetype == "text/html":
                        email.html_message = content
                        email.save()

                if msg.attachments:
                    attachments = create_attachments(msg.attachments)
                    email.attachments.add(*attachments)

            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Email queue failed")

        return len(email_messages)


class O365Backend(EmailBackend):
    """
    Backend to handle sending emails via o365 connection
    """

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        super().__init__(fail_silently, **kwargs)
        self.conn: Optional[O365Connection] = None

        # from_email might be hydrated by us (ChargeUp) in a few scenarios:
        # 1. after class __init__ (Django will create this class so we can't add directly to __init__)
        # 2. during email sending when a new connection needs to be opened
        self.from_email: str | None = None

        self.fail_silently: bool = fail_silently
        self.configuration_id: Optional[int] = None
        self._lock = threading.RLock()

    def close(self):
        """Closes and cleans up the current connection"""
        with self._lock:
            if self.conn:
                self.conn = None
                self.from_email = None
                self.configuration_id = None
            super().close()

    def open(self):
        """Opens a new O365 connection using the relevant configuration"""
        with self._lock:
            configuration = Outbox.objects.filter(
                email_host__icontains="office365",
                email_host_user__iexact=self.from_email,  # ignore case
            ).first()

            if not configuration:
                raise ValueError(
                    f"Unable to find an Outbox with email_host__icontains=office365 email_host_user={self.from_email}"
                )

            # existing saved connection is valid. no need for a new one
            if self.conn and self.configuration_id == configuration.id:
                return
            elif self.conn:
                # close the existing invalid connection
                self.close()
                self.from_email = configuration.email_host_user
                self.configuration_id = configuration.id

            # Parse O365 connection details from email_host
            parseresult = parse.urlparse(configuration.email_host)
            if not O365Connection.SCHEME == parseresult.scheme.lower():
                raise ValueError(
                    f'Invalid EMAIL_HOST scheme, expected "{O365Connection.SCHEME}", got "{parseresult.scheme}"'
                )

            # Extract connection parameters from query string
            query_dict = dict(parse.parse_qsl(parseresult.query))
            client_app_id = query_dict.get("client_app_id", "")
            client_id_key = query_dict.get("client_id_key", "")
            client_secret_key = query_dict.get("client_secret_key", "")

            try:
                # Create new connection with current configuration
                self.conn = O365Connection(
                    from_email=self.from_email,
                    client_app_id=client_app_id,
                    client_id_key=client_id_key,
                    client_secret_key=client_secret_key,
                )
            except Exception as e:
                self.close()  # Clean up on failure
                raise

    def send_messages(self, email_messages) -> int:
        """Sends email messages via O365 connection matching the from_email for each message"""
        if not email_messages:
            return 0

        with self._lock:
            sent_count = 0

            # sort by from_email to try to reduce connection closing/opening
            email_messages = sorted(email_messages, key=lambda m: m.from_email)

            for msg in email_messages:
                try:
                    # Use EmailAddressOAuthMapping to find oauth_username
                    oauth_username = (
                        EmailAddressOAuthMapping.objects.filter(
                            send_as_email=msg.from_email
                        )
                        .values_list("oauth_username", flat=True)
                        .first()
                    ) or msg.from_email

                    # If connection doesn't match this message's configuration, create new connection
                    if not self.conn or self.from_email != oauth_username:
                        self.close()
                        self.from_email = oauth_username
                        # TODO: we could leverage a connection cache rather than re-init each time
                        self.open()

                    # Send the message
                    if self.conn.send_messages([msg], fail_silently=self.fail_silently):
                        sent_count += 1

                except Exception as e:
                    if not self.fail_silently:
                        raise
                    logger.error(
                        f"Failed to send message from {msg.from_email}: {str(e)}"
                    )

            return sent_count


class GmailOAuth2Backend(EmailBackend):
    """Email backend that uses XOAUTH2 for SMTP authentication"""

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        super().__init__(fail_silently=fail_silently)
        self.connection = None
        self._lock = threading.RLock()

        # from_email might be hydrated by us (ChargeUp) in a few scenarios:
        # 1. after class __init__ (Django will create this class so we can't add directly to __init__)
        # this is currently not useful for Gmail but mirrors what's done with Outlook
        # 2. during email sending when a new connection needs to be opened
        self.from_email = None

        self.configuration_id = None
        # Initialize these to None - they'll be set when sending
        self.host = None
        self.port = None
        self.username = None
        self.password = None
        self.use_tls = None
        self.use_ssl = None
        self.timeout = None
        self.ssl_keyfile = None
        self.ssl_certfile = None

    def _initialize_connection(self, from_email: str) -> None:
        """Initialize connection settings based on from_email"""
        configuration = Outbox.objects.filter(
            email_host__icontains="gmail", email_host_user=from_email
        ).first()

        if not configuration:
            raise ValueError(
                f"Unable to find an Outbox with email_host__icontains=gmail email_host_user={from_email}"
            )

        logger.info(
            "Found a Gmail Outbox with: "
            f"email_use_tls={configuration.email_use_tls} "
            f"email_use_ssl={configuration.email_use_ssl} "
            f"email_host={configuration.email_host} "
            f"email_host_user={configuration.email_host_user} "
            f"email_port={configuration.email_port} "
            f"email_timeout={configuration.email_timeout} "
        )

        self.configuration_id = configuration.id
        self.from_email = from_email

        # Initialize settings from configuration
        self.host = configuration.email_host or "smtp.gmail.com"
        self.port = configuration.email_port or "587"
        self.username = from_email  # Important: this is used for OAuth lookup
        self.password = ""  # No password needed for XOAUTH2
        self.use_tls = configuration.email_use_tls
        self.use_ssl = configuration.email_use_ssl
        self.timeout = configuration.email_timeout
        self.ssl_keyfile = configuration.email_ssl_keyfile
        self.ssl_certfile = configuration.email_ssl_certfile

    def _connect_for_social_auth(self, user_social_auth: UserSocialAuth) -> None:
        creds_info = user_social_auth.extra_data
        auth_string = generate_oauth2_string(
            user_social_auth.uid, creds_info["access_token"], base64_encode=False
        )
        self.connection.docmd(
            "AUTH",
            "XOAUTH2 " + base64.b64encode(auth_string.encode("utf-8")).decode("utf-8"),
        )

    def open(self, auth_uid=None):
        """Override to use OAuth instead of password authentication"""

        try:
            # First establish the SMTP connection
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout
                )
            else:
                self.connection = smtplib.SMTP(
                    self.host, self.port, timeout=self.timeout
                )

            if self.use_tls:
                self.connection.starttls()

            user_social_auth = UserSocialAuth.objects.get(
                uid=auth_uid or self.from_email, provider="google-oauth2"
            )

            logger.info(
                f"Found UserSocialAuth with pk={user_social_auth.pk} uid={user_social_auth.uid}"
            )

            try:
                self._connect_for_social_auth(user_social_auth)
            except Exception as e:
                # TODO: we can avoid an except on all exceptions
                # and we can proactively refresh based on expiring soon
                # but we currently don't store access token expiration date
                logger.exception(
                    f"Failed connecting via OAuth. Attemping a token refresh for UserSocialAuth.uid={user_social_auth.uid}"
                )
                updated_social_auth = refresh_authorization(user_social_auth.uid)
                self._connect_for_social_auth(updated_social_auth)
            return True
        except Exception:
            logger.exception(
                f"gmail failed to open connection: auth_uid={auth_uid} from_email={self.from_email}"
            )
            return None

    def close(self):
        """Close the connection to the email server."""
        if self.connection is None:
            return
        try:
            try:
                self.connection.quit()
                logger.info(f"Connection quit for {self.from_email}")
            except (ssl.SSLError, smtplib.SMTPServerDisconnected) as e:
                logger.exception(
                    f"Exception while quitting a connection for {self.from_email}: {e}"
                )
                self.connection.close()
                logger.info(f"Connection closed for {self.from_email}")
            except smtplib.SMTPException as e:
                logger.exception(
                    f"SMTPException while quitting a connection for {self.from_email}: {e}"
                )
                if self.fail_silently:
                    return
                raise
        finally:
            self.connection = None
            self.from_email = None
            self.configuration_id = None

    def send_messages(self, email_messages):
        """Send messages, reinitializing connection if from_email changes"""
        if not email_messages:
            return 0

        with self._lock:
            num_sent = 0

            # sort by from_email to reduce connection opening
            email_messages = sorted(email_messages, key=lambda m: m.from_email)

            for message in email_messages:
                try:
                    # hack way to get the original username
                    # TODO: could do a cache here
                    # not all accounts are in EmailAddressOAuthMapping. but here's how one:
                    #
                    # EmailAddressOAuthMapping: oauth_username=company_oauth@g.company.ai send_as_email=person@customer.com
                    # UserSocialAuth: uid=company_oauth@g.company.ai provider=google-oauth2 created=2024-09-22 16:32:46.641390+00:00 modified=2025-03-07 17:52:45.714140+00:00
                    # OutgoingEmail: id=545 from_email=person@customer.com created=2025-03-07 01:00:00.824912+00:00 last_updated=2025-03-07 01:00:00.824923+00:00
                    # Outbox: email_host_user=company_oauth@g.company.ai email_host=smtp.gmail.com
                    #
                    # so for a OutgoingEmail from person@customer.com
                    # we get EmailAddressOAuthMapping with send_as_email from person@customer.com
                    # which has an EmailAddressOAuthMapping.oauth_username of company_oauth@g.company.ai, which maps to Outbox.email_host_user=company_oauth@g.company.ai
                    # and UserSocialAuth: uid=company_oauth@g.company.ai
                    #
                    # another example without EmailAddressOAuthMapping:
                    #
                    # UserSocialAuth: uid=customer2@g.company.ai provider=google-oauth2 created=2025-02-04 17:45:13.116982+00:00 modified=2025-03-07 17:52:00.138284+00:00
                    # UserSocialAuth: uid=company@customer2.com provider=google-oauth2 created=2025-02-03 18:47:19.157579+00:00 modified=2025-03-07 17:52:01.547400+00:00
                    # OutgoingEmail: id=546 from_email=company@customer2.com created=2025-03-07 01:00:00.898387+00:00 last_updated=2025-03-07 16:25:05.930577+00:00
                    # Outbox: email_host_user=customer2@g.company.ai email_host=smtp.gmail.com
                    # Outbox: email_host_user=company@customer2.com email_host=smtp.gmail.com
                    #
                    # OutgoingEmail is from company@customer2.com
                    # which maps to the Outbox of company@customer2.com
                    # and UserSocialAuth: uid=company@customer2.com
                    oauth_username = (
                        EmailAddressOAuthMapping.objects.filter(
                            send_as_email=message.from_email
                        )
                        .values_list("oauth_username", flat=True)
                        .first()
                    ) or message.from_email

                    # Check if we need to reinitialize for a different from_email
                    if (
                        not self.connection
                        or self.from_email != oauth_username
                        or not self.configuration_id
                    ):

                        logger.info(
                            f"Opening a new connection in send_messages: "
                            f"self.from_email={self.from_email} "
                            f"oauth_username={oauth_username} "
                            f"connection_exists={bool(self.connection)} "
                            f"configuration_id_exists={bool(self.configuration_id)} "
                        )

                        self.close()
                        # TODO: we could leverage a connection cache rather than re-init each time
                        self._initialize_connection(oauth_username)
                        new_conn_created = self.open(auth_uid=oauth_username)

                        if not self.connection or new_conn_created is None:
                            # Previously this just `continue`d — silently
                            # dropping the message instead of failing it.
                            # open() already swallows its own exceptions
                            # (logs + returns None) so a dead/expired OAuth
                            # token that also fails to refresh left nothing
                            # here to signal a problem. The caller
                            # (django_mail_admin's OutgoingEmail.dispatch())
                            # only marks STATUS.failed when an exception
                            # actually propagates — with the old `continue`,
                            # dispatch() saw a clean return from .send() and
                            # marked the email STATUS.sent even though
                            # nothing was ever delivered. Raising here routes
                            # through the same per-message except block below
                            # (raise if not fail_silently, else log+continue
                            # to the next message) — consistent with every
                            # other failure path in this loop, and the
                            # underlying open()/refresh_authorization() error
                            # is already in the logs just above.
                            logger.info(
                                f"No connection available: "
                                f"self.from_email={self.from_email} "
                                f"oauth_username={oauth_username} "
                                f"connection_exists={bool(self.connection)} "
                                f"new_conn_created={bool(new_conn_created)} "
                            )
                            raise ConnectionError(
                                f"Unable to establish an authenticated Gmail "
                                f"SMTP connection for oauth_username="
                                f"{oauth_username} (from_email="
                                f"{message.from_email}) — OAuth token invalid/"
                                f"expired and refresh failed. See preceding "
                                f"logs for the underlying error."
                            )

                    if self._send(message):
                        num_sent += 1

                except Exception as e:
                    if not self.fail_silently:
                        raise
                    logger.error(
                        f"Failed to send message from {message.from_email}: {str(e)}"
                    )

            if self.connection:
                self.close()

            return num_sent
