import base64
from email.message import EmailMessage as PythonEmailMessage

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


class GmailAPIEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):

        if not email_messages:
            return 0

        credentials = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            scopes=GMAIL_SCOPES,
        )

        credentials.refresh(Request())

        service = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        sent_count = 0

        for email_message in email_messages:

            message = PythonEmailMessage()

            message["From"] = settings.GMAIL_SENDER_EMAIL
            message["To"] = ", ".join(email_message.to)
            message["Subject"] = email_message.subject

            if email_message.cc:
                message["Cc"] = ", ".join(email_message.cc)

            if email_message.reply_to:
                message["Reply-To"] = ", ".join(
                    email_message.reply_to
                )

            # Plain-text version
            message.set_content(email_message.body)

            # HTML alternative, if Django/allauth provides one
            for alternative in getattr(
                email_message,
                "alternatives",
                []
            ):
                content = getattr(
                    alternative,
                    "content",
                    alternative[0]
                )

                mimetype = getattr(
                    alternative,
                    "mimetype",
                    alternative[1]
                )

                if mimetype == "text/html":
                    message.add_alternative(
                        content,
                        subtype="html"
                    )

            encoded_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            service.users().messages().send(
                userId="me",
                body={
                    "raw": encoded_message
                }
            ).execute()

            sent_count += 1

        return sent_count