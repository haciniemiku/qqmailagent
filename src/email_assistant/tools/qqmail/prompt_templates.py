"""Tool prompt templates for QQ Mail integration."""

QQMAIL_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - Fetch recent emails from QQ Mail over IMAP
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - Send a reply over QQ Mail SMTP
3. check_calendar_tool(dates) - Check calendar availability for specific dates
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - Draft a meeting invitation email
5. triage_email(ignore, notify, respond) - Triage emails into one of three categories
6. Done - E-mail has been sent
"""
