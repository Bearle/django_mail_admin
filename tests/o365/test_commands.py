import time
import random

from urllib import parse
from datetime import datetime

from django.test import TestCase
from django.conf import settings
from django.template.loader import render_to_string

from django_mail_admin.models import Outbox, IncomingEmail, OutgoingEmail, STATUS
from django_mail_admin.models import Mailbox
from django_mail_admin.mail import send_queued
from django_mail_admin.connections import connections

from django_mail_admin.o365_utils import O365NotAuthenticated


class O365CommandTest(TestCase):
    O365_BACKEND_ALIAS = "o365"

    def print_incoming_emails(self):
        for email in IncomingEmail.objects.all().order_by("processed"):
            print(f"{email.message_id} | {email.subject} | {email.processed}")

    def _get_html_draft(
        self,
        text_body: str,
        message_hash: str,
        legal_disclaimer="This is a test legal disclaimer",
    ):
        context = {
            "bodylines": text_body.splitlines(),
            "message_hash": message_hash,
            "legal_disclaimer": legal_disclaimer,
        }
        return render_to_string("html_email_draft.html", context)

    def send_email(self, outgoing_email) -> bool:
        retry_send = False
        send_successful = False
        while True:
            try:
                outgoing_email.dispatch(commit=True)
            except O365NotAuthenticated as uae:
                connection = connections[self.O365_BACKEND_ALIAS]
                print(f"warning: send_mail: {uae};")
                if not retry_send:
                    retry_send = connection.conn.account.authenticate()
                    print(
                        f"authentication attempt: "
                        + ("successful " if retry_send else " failed!")
                    )
                else:
                    retry_send = False
            except Exception as e:
                print(f"error: send_mail: {e}")
            else:
                send_successful = True
                retry_send = False

            if send_successful or not retry_send:
                break
        return send_successful

    def test_o365(self):
        """
        An end-to-end test of sending one email from the mailbox of user1, and checking if it is received in the mailbox of configured user2, if no user2 is configured, sends it to user1.

        It is likely to through O365NotAuthenticated if the mailboxe authorizations are not already setup for user1 and user2.
        """
        from_user_email = settings.O365_TEST_ADMIN.get("test_from_email")
        to_user_email = settings.O365_TEST_ADMIN.get("test_to_email", from_user_email)

        from_user_email_str = parse.quote(from_user_email)
        from_user_o365_con = f"office365://{from_user_email_str}@outlook.office365.com?client_app_id=test_webapp1"

        Outbox.objects.create(
            name="O365CommandTest_Outbox",
            email_host=from_user_o365_con,
            email_host_user=from_user_email,
            email_host_password="ase123hgfd",
            active=True,
        )

        test_subject = f"UnitTest Subject Dated {datetime.now()}"
        message_hash = random.random()
        # do not use '\n' sequence in test body, the returning email will collapse all new line sequences to a single space
        text_body = f"UnitTest Body. Line1 Hi\nLine2 This is a test draft"
        test_body = f"{text_body}\n{message_hash}"
        test_html_body = self._get_html_draft(text_body, message_hash)
        """
        print(f"\ntest_subject: {test_subject}")
        print(f"test_body: {test_body}\n")
        """
        outgoing_emails = []
        for tst_body in [test_body, test_html_body]:
            outgoing_emails.append(
                OutgoingEmail.objects.create(
                    from_email=from_user_email,
                    to=[to_user_email],
                    status=STATUS.queued,
                    subject=test_subject,
                    message=tst_body,
                    backend_alias=self.O365_BACKEND_ALIAS,
                )
            )

        to_user_email_str = parse.quote(to_user_email)
        to_user_o365_con = f"office365://{to_user_email_str}@outlook.office365.com?client_app_id=test_webapp1"

        inbox = Mailbox.objects.create(
            name="O365CommandTest_Inbox", uri=to_user_o365_con, from_email=to_user_email
        )
        # first poll for inbox emails of user2
        new_emails = inbox.get_new_mail()
        print(f"received {len(new_emails)} new emails")
        # time.sleep(10)

        # send new email(s) from user1 to user2
        for outgoing_email in outgoing_emails:
            send_successful = self.send_email(outgoing_email)

        assert send_successful == True
        # sleep for sync
        # time.sleep(10)

        # get inbox emails for user2 hoping to have received the recently sent email.
        max_attempts = 3
        # if the recent attempt did not succeed in receiving the new email, try again for max_attempts times to fetch new emails.
        latest_emails = []
        while max_attempts:
            max_attempts -= 1
            time.sleep(2)
            new_emails = inbox.get_new_mail()
            print(f"received {len(new_emails)} new emails")
            latest_emails.extend(new_emails)
            if len(latest_emails) == 2:
                break
            print(
                f"\tContinue seeking new mails; retry attempts remaining {max_attempts}"
            )

        assert latest_emails
        test_body_wo_newlines = test_body.replace("\n", " ")
        for latest_email in latest_emails:
            assert latest_email.subject == test_subject
            body_matches = (latest_email.text == test_body_wo_newlines) or (
                str(message_hash) in latest_email.html
            )
            assert body_matches
