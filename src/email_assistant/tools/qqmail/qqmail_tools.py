"""QQ Mail tools implemented with IMAP and SMTP."""

import imaplib
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
import re
from typing import Any, Dict, Iterator, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from email_assistant.tools.default.calendar_tools import (
    check_calendar_availability,
    schedule_meeting,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in ("", None) else default


def _auth_code() -> str | None:
    return _env("QQ_EMAIL_AUTH_CODE") or _env("QQMAIL_AUTH_CODE") or _env("QQ_EMAIL_PASSWORD")


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _addresses(value: str | None) -> str:
    decoded = _decode(value)
    pairs = getaddresses([decoded])
    if not pairs:
        return decoded
    return ", ".join(
        f"{name} <{addr}>" if name else addr
        for name, addr in pairs
        if addr or name
    )


def _message_text(message: Message) -> str:
    if message.is_multipart():
        html_fallback = ""
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            if content_type == "text/plain":
                return part.get_content()
            if content_type == "text/html" and not html_fallback:
                html_fallback = part.get_content()
        return html_fallback

    if message.get_content_maintype() == "text":
        return message.get_content()
    return ""


def _message_datetime(message: Message) -> datetime:
    date_header = message.get("Date")
    if not date_header:
        return datetime.now().astimezone()
    parsed = parsedate_to_datetime(date_header)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _connect_imap() -> imaplib.IMAP4_SSL:
    email_address = _env("QQ_EMAIL")
    auth_code = _auth_code()
    if not email_address or not auth_code:
        raise RuntimeError("Set QQ_EMAIL and QQ_EMAIL_AUTH_CODE in .env before using QQ Mail.")

    host = _env("QQ_IMAP_HOST", "imap.qq.com")
    port = int(_env("QQ_IMAP_PORT", "993") or "993")
    client = imaplib.IMAP4_SSL(host, port)
    client.login(email_address, auth_code)
    return client


def _fetch_message_by_uid(client: imaplib.IMAP4_SSL, uid: str) -> Message | None:
    status, data = client.uid("fetch", uid, "(RFC822)")
    if status != "OK":
        return None
    for item in data:
        if isinstance(item, tuple):
            return BytesParser(policy=policy.default).parsebytes(item[1])
    return None


def _thread_id(message: Message, uid: str) -> str:
    """Return a stable root identifier for an email conversation."""
    message_id = _decode(message.get("Message-ID")) or f"qqmail-{uid}"
    references = _decode(message.get("References"))
    in_reply_to = _decode(message.get("In-Reply-To"))

    # References often contains the whole chain: "<root> <reply-1> <reply-2>".
    # Use the first Message-ID so every reply maps back to the same root thread.
    if references:
        ids = re.findall(r"<[^>]+>", references)
        if ids:
            return ids[0]
        return references.split()[0]

    if in_reply_to:
        ids = re.findall(r"<[^>]+>", in_reply_to)
        if ids:
            return ids[0]
        return in_reply_to.split()[0]

    return message_id


def _email_data(uid: str, message: Message) -> Dict[str, Any]:
    return {
        "from_email": _addresses(message.get("Reply-To") or message.get("From")),
        "to_email": _addresses(message.get("To")),
        "subject": _decode(message.get("Subject")) or "No Subject",
        "page_content": _message_text(message),
        "id": uid,
        "thread_id": _thread_id(message, uid),
        "send_time": _message_datetime(message).isoformat(),
    }


def fetch_group_emails(
    email_address: str,
    minutes_since: int = 30,
    include_read: bool = False,
    skip_filters: bool = False,
) -> Iterator[Dict[str, Any]]:
    """Fetch recent QQ Mail messages using IMAP."""
    cutoff = datetime.now().astimezone() - timedelta(minutes=minutes_since)
    mailbox = _env("QQ_MAILBOX", "INBOX") or "INBOX"
    client = _connect_imap()

    try:
        client.select(mailbox)
        since = cutoff.strftime("%d-%b-%Y")
        criteria = ["SINCE", since]
        if not include_read:
            criteria.insert(0, "UNSEEN")

        status, data = client.uid("search", None, *criteria)
        if status != "OK" or not data or not data[0]:
            return

        for uid_bytes in data[0].split():
            uid = uid_bytes.decode()
            message = _fetch_message_by_uid(client, uid)
            if message is None:
                continue

            send_time = _message_datetime(message)
            if send_time < cutoff:
                continue

            from_header = _addresses(message.get("From"))
            if email_address.lower() in from_header.lower() and not skip_filters:
                yield {"id": uid, "thread_id": _decode(message.get("Message-ID")) or uid, "user_respond": True}
                continue

            yield _email_data(uid, message)
    finally:
        try:
            client.close()
        except Exception:
            pass
        client.logout()


class FetchEmailsInput(BaseModel):
    """Input schema for fetching QQ Mail messages."""

    email_address: str = Field(description="Email address to fetch emails for")
    minutes_since: int = Field(default=30, description="Only retrieve emails newer than this many minutes")


@tool(args_schema=FetchEmailsInput)
def fetch_emails_tool(email_address: str, minutes_since: int = 30) -> str:
    """Fetch recent emails from QQ Mail."""
    emails = list(fetch_group_emails(email_address, minutes_since))
    if not emails:
        return "No new emails found."

    result = f"Found {len(emails)} new emails:\n\n"
    for i, email in enumerate(emails, 1):
        if email.get("user_respond", False):
            result += f"{i}. You already responded to this email (Thread ID: {email['thread_id']})\n\n"
            continue
        result += f"{i}. From: {email['from_email']}\n"
        result += f"   To: {email['to_email']}\n"
        result += f"   Subject: {email['subject']}\n"
        result += f"   Time: {email['send_time']}\n"
        result += f"   ID: {email['id']}\n"
        result += f"   Thread ID: {email['thread_id']}\n"
        result += f"   Content: {email['page_content'][:200]}...\n\n"
    return result


class SendEmailInput(BaseModel):
    """Input schema for sending QQ Mail replies."""

    email_id: str = Field(description="QQ Mail IMAP UID to reply to, or NEW_EMAIL for a new email")
    response_text: str = Field(description="Content of the reply")
    email_address: str = Field(description="Current user's email address")
    additional_recipients: Optional[List[str]] = Field(default=None, description="Optional CC recipients")


def send_email(
    email_id: str,
    response_text: str,
    email_address: str,
    addn_receipients: Optional[List[str]] = None,
) -> bool:
    """Send a QQ Mail reply over SMTP."""
    auth_code = _auth_code()
    if not auth_code:
        raise RuntimeError("Set QQ_EMAIL_AUTH_CODE in .env before sending QQ Mail.")

    to_email = ""
    subject = "Response"
    in_reply_to = ""
    references = ""

    if email_id and email_id != "NEW_EMAIL":
        client = _connect_imap()
        try:
            client.select(_env("QQ_MAILBOX", "INBOX") or "INBOX")
            original = _fetch_message_by_uid(client, email_id)
            if original is not None:
                to_email = _addresses(original.get("Reply-To") or original.get("From"))
                subject = _decode(original.get("Subject")) or subject
                if not subject.lower().startswith("re:"):
                    subject = f"Re: {subject}"
                in_reply_to = _decode(original.get("Message-ID"))
                references = _decode(original.get("References")) or in_reply_to
        finally:
            try:
                client.close()
            except Exception:
                pass
            client.logout()

    if not to_email:
        if not addn_receipients:
            raise RuntimeError("No recipient found. Provide additional_recipients for NEW_EMAIL.")
        to_email = addn_receipients[0]
        addn_receipients = addn_receipients[1:]

    msg = EmailMessage()
    msg["From"] = email_address
    msg["To"] = to_email
    msg["Subject"] = subject
    if addn_receipients:
        msg["Cc"] = ", ".join(addn_receipients)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    msg.set_content(response_text)

    host = _env("QQ_SMTP_HOST", "smtp.qq.com")
    port = int(_env("QQ_SMTP_PORT", "465") or "465")
    with smtplib.SMTP_SSL(host, port) as server:
        server.login(email_address, auth_code)
        server.send_message(msg)
    return True


@tool(args_schema=SendEmailInput)
def send_email_tool(
    email_id: str,
    response_text: str,
    email_address: str,
    additional_recipients: Optional[List[str]] = None,
) -> str:
    """Send a reply to an existing QQ Mail message or create a new email."""
    try:
        send_email(email_id, response_text, email_address, addn_receipients=additional_recipients)
        return f"Email reply sent successfully to message ID: {email_id}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


class CheckCalendarInput(BaseModel):
    """Input schema for checking calendar availability."""

    dates: List[str] = Field(description="List of dates to check in DD-MM-YYYY format")


@tool(args_schema=CheckCalendarInput)
def check_calendar_tool(dates: List[str]) -> str:
    """Check calendar availability using the default mock calendar."""
    return "\n".join(check_calendar_availability.invoke({"day": date}) for date in dates)


class ScheduleMeetingInput(BaseModel):
    """Input schema for drafting a meeting invitation."""

    attendees: List[str] = Field(description="Email addresses of meeting attendees")
    title: str = Field(description="Meeting title/subject")
    start_time: str = Field(description="Meeting start time in ISO format")
    end_time: str = Field(description="Meeting end time in ISO format")
    organizer_email: str = Field(description="Email address of the meeting organizer")
    timezone: str = Field(default="Asia/Shanghai", description="Timezone for the meeting")


@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting_tool(
    attendees: List[str],
    title: str,
    start_time: str,
    end_time: str,
    organizer_email: str,
    timezone: str = "Asia/Shanghai",
) -> str:
    """Draft a meeting invitation note for QQ Mail users."""
    return (
        f"Meeting invitation drafted: '{title}' from {start_time} to {end_time} "
        f"({timezone}) with {len(attendees)} attendees. Organizer: {organizer_email}. "
        "QQ Mail does not expose a calendar API here, so send the invite details by email."
    )


def mark_as_read(message_id: str) -> None:
    """Mark a QQ Mail message as read by IMAP UID."""
    client = _connect_imap()
    try:
        client.select(_env("QQ_MAILBOX", "INBOX") or "INBOX")
        client.uid("store", message_id, "+FLAGS", r"(\Seen)")
    finally:
        try:
            client.close()
        except Exception:
            pass
        client.logout()
