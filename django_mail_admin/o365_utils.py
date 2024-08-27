"""
Helper utility classes/ functions for O365 support
"""
import logging
import hashlib
from typing import Optional

from base64 import b64encode
from datetime import datetime
from django.conf import settings
from django.core.mail.message import EmailMessage, EmailMultiAlternatives

from O365.utils import BaseTokenBackend

from O365 import MSGraphProtocol
from O365 import Account, Message, FileSystemTokenBackend
from O365.mailbox import MailBox

logger = logging.getLogger(__name__)


class O365NotAuthenticated(Exception):
    pass


class O365Connection:
    SCHEME = "office365"
    O365_PROTOCOL = "MSGraphProtocol"
    DEFAULT_CLIENT_ID_KEY = "O365_CLIENT_ID"
    DEFAULT_CLIENT_SECRET_KEY = "O365_CLIENT_SECRET"
    MESSAGE_ID_KEY = "Message-ID"

    def __init__(
        self,
        from_email: str,
        client_app_id: str,
        client_id_key: str,
        client_secret_key: str,
        protocol: str = O365_PROTOCOL,
    ) -> None:
        self.from_email = from_email
        if not self.from_email:
            raise ValueError("from_email required.")

        self.account = None
        self.selected_settings = None
        try:
            client_id, client_secret = self._get_auth_info(
                client_app_id,
                client_id_key if client_id_key else self.DEFAULT_CLIENT_ID_KEY,
                client_secret_key
                if client_secret_key
                else self.DEFAULT_CLIENT_SECRET_KEY,
            )
            self._connect(client_app_id, client_id, client_secret, protocol)
        except (TypeError, ValueError) as e:
            logger.warning("O365Connection: Couldn't authenticate %s" % e)

    def _get_auth_info(
        self, client_app_id: str, client_id_key: str, client_secret_key: str
    ):
        selected_settings = (
            settings.O365_CLIENT_APP_SETTINGS.get(client_app_id, {})
            if client_app_id
            else settings.O365_ADMIN_SETTINGS
        )
        if not selected_settings:
            if client_app_id:
                raise ValueError(
                    f"Settings not found for client_app_id: '{client_app_id}'"
                )
            else:
                raise ValueError(f"O365_ADMIN_SETTINGS not defined!")

        client_id = selected_settings.get(client_id_key, "")
        if not client_id:
            raise ValueError(f"{client_app_id}.{client_id_key} not set! ")

        client_secret = selected_settings.get(client_secret_key, "")
        if not client_secret:
            raise ValueError(f"{client_app_id}.{client_secret_key} not set!")

        return client_id, client_secret

    def _get_token_backend(
        self, client_app_id: str = None, client_id: str = None
    ) -> Optional[object]:
        selected_settings = (
            settings.O365_CLIENT_APP_SETTINGS.get(client_app_id, {})
            if client_app_id
            else settings.O365_ADMIN_SETTINGS
        )
        if not selected_settings:
            raise ValueError("Selected settings not yet set!")

        token_backend = selected_settings.get("TOKEN_BACKEND", "FileSystemTokenBackend")
        backend_settings = settings.O365_TOKEN_BACKENDS.get(token_backend, {})

        if "FileSystemTokenBackend" == token_backend:
            return FileSystemTokenBackend(
                token_path=backend_settings.get("O365_AUTH_BACKEND_TOKEN_DIR", "."),
                token_filename=self._decorate_token_name(
                    client_id,
                    token_name_pattern=backend_settings.get(
                        "O365_AUTH_BACKEND_TOKEN_FILE"
                    ),
                ),
            )

        if "AZBlobStorageTokenBackend" == token_backend:
            return AZBlobStorageTokenBackend(
                connection_str=backend_settings.get(
                    "O365_AUTH_BACKEND_AZ_CONNECTION_STR"
                ),
                container_name=backend_settings.get(
                    "O365_AUTH_BACKEND_AZ_CONTAINER_PATH"
                ),
                blob_name=self._decorate_token_name(
                    client_id,
                    token_name_pattern=backend_settings.get(
                        "O365_AUTH_BACKEND_AZ_BLOB_NAME"
                    ),
                ),
            )
        return None

    def _decorate_token_name(self, client_id: str, token_name_pattern: Optional[str]):
        if not token_name_pattern:
            token_name_pattern = "o365_token.txt"
        return "{}/{}".format(
            hashlib.sha1(
                client_id.encode("utf-8") + self.from_email.encode("utf-8")
            ).hexdigest(),
            token_name_pattern,
        )

    def _connect(self, client_app_id, client_id, client_secret, protocol) -> None:
        # connect_id/ and secret should have been already setup
        # for offline & message_all scopes, for on behalf of user access.
        protocol_selected = (
            MSGraphProtocol(api_version="beta")
            if protocol == self.O365_PROTOCOL
            else None
        )
        if not protocol_selected:
            raise ValueError(f"Unsupported protocol {protocol}")

        token_backend = self._get_token_backend(
            client_app_id=client_app_id, client_id=client_id
        )

        self.account = Account(
            credentials=(client_id, client_secret),
            protocol=protocol_selected,
            scopes=["offline_access", "message_all"],
            token_backend=token_backend,
        )

    def _get_message_by_id(
        self, mailbox: MailBox, message_id: str, folder_name="Inbox"
    ) -> Optional[Message]:
        """retrieve message by id from given mailbox"""
        if not message_id:
            return None
        mail_folder = mailbox.get_folder(folder_name=folder_name) if mailbox else None
        qstr = f"internetMessageId eq '{message_id}'"
        emails = mail_folder.get_messages(query=qstr) if mail_folder else []
        for email in emails:
            return email
        return None

    def _get_reply_to_message(
        self, mailbox: MailBox, msg: EmailMessage
    ) -> Optional[Message]:
        """retrieve message representing in-reply-to id in msg headers"""
        if not msg or not msg.extra_headers or not mailbox:
            return None
        msg_id = msg.extra_headers.get("In-Reply-To", None)
        reply_to_msg = self._get_message_by_id(mailbox, msg_id) if msg_id else None
        return reply_to_msg

    def _prepare_new_message(self, mailbox, msg: EmailMessage):
        """create new or reply-to draft based on msg in-reply-to header"""
        reply_to_message = self._get_reply_to_message(mailbox, msg)
        new_draft_message = (
            reply_to_message.reply() if reply_to_message else mailbox.new_message()
        )
        return new_draft_message

    def _prepare_attachment_for_dispatch(self, attachment) -> dict:
        """bridge from Django EmailMessage Attachment to O365 Attachment"""
        content = attachment[1]
        b64content = b64encode(
            content if isinstance(content, bytes) else bytes(content, "utf-8")
        ).decode("utf-8")
        return {"name": f"{attachment[0]}", "content": b64content, "on_disk": False}

    def _get_html_body(self, msg) -> Optional[str]:
        if isinstance(msg, EmailMultiAlternatives):
            for msg_alt in msg.alternatives:
                alt_content, alt_content_type = msg_alt
                if "text/html" == alt_content_type:
                    return alt_content
        return None

    def _get_draft_message_id(
        self,
        mailbox: MailBox,
        object_id: str,
    ) -> Optional[str]:
        """helper to get internet_message_id from the saved draft of given object_id message."""
        draft_folder = mailbox.get_folder(folder_name="Drafts")
        if not draft_folder:
            return None
        dm = draft_folder.get_message(object_id=object_id, download_attachments=False)
        return dm.internet_message_id if dm else None

    def _update_message_id_header(
        self, msg: EmailMessage, internet_message_id: str
    ) -> bool:
        """add internet message-id of external email message to EmailMessage.extra_headers

        Ensure this is called after the outbound message has had a chance to have an internet message id, e.g. when a message draft is saved in the mail-server.

        This helps mail-admin to associate the OutgoingEmail to the internet-message-id, and tie any replies to the external email back to this OutgoingEmail.
        """
        if not msg or not internet_message_id:
            return False
        msg.extra_headers.update(
            {
                self.MESSAGE_ID_KEY: internet_message_id,
            }
        )
        return True

    def send_messages(self, email_messages, fail_silently: bool = False) -> int:
        sent_messages = 0
        if not (self.account and self.account.is_authenticated):
            logger.error("send_messages unavailable; account not authenticated!")
            if not fail_silently:
                raise O365NotAuthenticated(
                    "get_messages unavailable; account not yet authenticated!"
                )
        mailbox = self.account.mailbox(self.from_email)
        for msg in email_messages:
            try:
                m = self._prepare_new_message(mailbox, msg)
                m.to.add(msg.to)
                m.cc.add(msg.cc)
                m.bcc.add(msg.bcc)
                m.reply_to.add(msg.reply_to)
                html_body = self._get_html_body(msg)
                m.body = msg.body if not html_body else html_body
                if msg.subject:
                    m.subject = msg.subject
                m.save_message()
                m.attachments.add(
                    [
                        self._prepare_attachment_for_dispatch(attachment)
                        for attachment in msg.attachments
                    ]
                )
                for attachment in m.attachments:
                    # workaround: avoid NoneType compare w/ int, O365 exception
                    attachment.size = len(attachment.content)
                m.save_draft()
                self._update_message_id_header(
                    msg,
                    m.internet_message_id
                    if m.internet_message_id
                    else self._get_draft_message_id(
                        mailbox=mailbox, object_id=m.object_id
                    ),
                )
                m.send()
                sent_messages += 1
            except Exception as e:
                logger.error(f"Exception in sending message: error info: {e}")
                if not fail_silently:
                    raise e
        return sent_messages

    def get_messages(self, owner_email: str, last_polled: datetime, condition):
        if not (self.account and self.account.is_authenticated):
            logger.error("get_messages unavailable; account not authenticated!")
            raise O365NotAuthenticated(
                "get_messages unavailable; account not yet authenticated!"
            )
        mailbox = self.account.mailbox(owner_email)
        mail_folder = mailbox.get_folder(folder_name="Inbox")
        qstr = ""
        order_by = f"receivedDateTime DESC"
        if last_polled:
            # ISO 8601 format AND in UTC time.
            # For example, midnight UTC on Jan 1, 2022 is 2022-01-01T00:00:00Z.
            qstr = f"receivedDateTime gt {last_polled.replace(microsecond=0).isoformat()[:-6]}Z"
        for mail in mail_folder.get_messages(order_by=order_by, query=qstr):
            yield (mail.get_mime_content())


class AZBlobStorageTokenBackend(BaseTokenBackend):
    """An Azure Blob store backend for token management"""

    def __init__(self, connection_str, container_name, blob_name):
        """
        Init Backend
        :param str connection_str: Connection str for the Blob storage account
        :param str container_name: Container string for blob file.
        :param str blob_name: Blob name
        """
        if not (connection_str and container_name and blob_name):
            raise ValueError(
                "At least one required inputs is empty! "
                + f"connection_str:'{connection_str}', container_name:'{container_name}', blob_name:'{blob_name}'"
            )

        self.container_name = container_name
        self.blob_name = blob_name
        try:
            from azure.storage.blob import BlobClient
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "Please install the azure-storage-blob package to use this token backend."
            ) from e
        super().__init__()

        self._client = BlobClient.from_connection_string(
            connection_str,  # type: ignore
            container_name=container_name,  # type: ignore
            blob_name=blob_name,  # type: ignore
        )

    def __repr__(self):
        return "AzureTokenBackend('{}', '{}')".format(
            self.connection_str, self.container_name
        )

    def load_token(self):
        """
        Retrieves the token from the store
        :return dict or None: The token if exists, None otherwise
        """
        token = None
        try:
            downloader = self._client.download_blob(max_concurrency=1, encoding="UTF-8")
            token_str = downloader.readall()
            token = self.token_constructor(self.serializer.loads(token_str))
        except Exception as e:
            logger.error(
                "Token (blob_text: {}/{}) could not be retrieved from the backend: {}".format(
                    self.container_name, self.blob_name, e
                )
            )

        return token

    def save_token(self):
        """
        Saves the token dict in the store
        :return bool: Success / Failure
        """
        if self.token is None:
            raise ValueError('You have to set the "token" first.')

        try:
            r = self._client.upload_blob(
                self.serializer.dumps(self.token), overwrite=True
            )
        except Exception as e:
            logger.error("Token secret could not be created: {}".format(e))
            return False
        return True

    def delete_token(self):
        """
        Deletes the token from the store
        :return bool: Success / Failure
        """
        try:
            r = self._client.delete_blob()
        except Exception as e:
            logger.error("Token secret could not be deleted: {}".format(e))
            return False
        else:
            logger.warning(
                "Deleted token secret {} ({}).".format(
                    self.container_name, self.blob_name
                )
            )
            return True

    def check_token(self):
        """
        Checks if the token exists
        :return bool: True if it exists on the store
        """
        try:
            _ = self._client.exists()
        except:
            return False
        else:
            return True
