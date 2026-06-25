# QQ Mail Integration Tools

This integration connects the email assistant to QQ Mail using IMAP for reading
messages and SMTP for sending replies.

## Setup

1. In QQ Mail, enable POP3/IMAP/SMTP service and generate an authorization code.
   Use the authorization code instead of your QQ password.

2. Add these values to `.env`:

```bash
QQ_EMAIL="your-email@qq.com"
QQ_EMAIL_AUTH_CODE="your-qq-mail-authorization-code"
QQ_IMAP_HOST="imap.qq.com"
QQ_IMAP_PORT="993"
QQ_SMTP_HOST="smtp.qq.com"
QQ_SMTP_PORT="465"
QQ_MAILBOX="INBOX"
```

3. Start the local LangGraph server:

```bash
langgraph dev
```

4. In another terminal, ingest recent QQ Mail messages:

```bash
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 120
```

By default, the script sends messages to the
`email_assistant_hitl_memory_qqmail` graph at `http://127.0.0.1:2024`.

## Notes

- QQ Mail does not provide the same Gmail REST API used by the Gmail version of
  this project, so this integration uses standard mail protocols.
- Calendar tools are mock/draft helpers. QQ Mail calendar scheduling is not
  implemented as a real API call here.
- IMAP message UIDs are used as `email_id` values for replies and marking
  messages as read.
