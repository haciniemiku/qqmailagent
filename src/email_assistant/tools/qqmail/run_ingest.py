#!/usr/bin/env python
"""Ingest QQ Mail messages into a running LangGraph server."""

import argparse
import asyncio
import hashlib
import uuid

from dotenv import load_dotenv
from langgraph_sdk import get_client

from email_assistant.tools.qqmail.qqmail_tools import fetch_group_emails

load_dotenv(".env")


async def ingest_email_to_langgraph(email_data, graph_name, url="http://127.0.0.1:2024"):
    """Ingest one normalized email dictionary to LangGraph."""
    client = get_client(url=url)
    raw_thread_id = email_data["thread_id"]
    thread_id = str(uuid.UUID(hex=hashlib.md5(raw_thread_id.encode("UTF-8")).hexdigest()))
    print(f"QQ Mail thread ID: {raw_thread_id} -> LangGraph thread ID: {thread_id}")

    try:
        await client.threads.get(thread_id)
        thread_exists = True
        print(f"Found existing thread: {thread_id}")
    except Exception:
        thread_exists = False
        print(f"Creating new thread: {thread_id}")
        await client.threads.create(thread_id=thread_id)

    if thread_exists:
        try:
            runs = await client.runs.list(thread_id)
            for run_info in runs:
                run_id = run_info["run_id"] if isinstance(run_info, dict) else run_info.id
                print(f"Deleting previous run {run_id} from thread {thread_id}")
                await client.runs.delete(thread_id, run_id)
        except Exception as e:
            print(f"Error listing/deleting runs: {str(e)}")

    await client.threads.update(thread_id, metadata={"email_id": email_data["id"]})
    run = await client.runs.create(
        thread_id,
        graph_name,
        input={
            "email_input": {
                "from": email_data["from_email"],
                "to": email_data["to_email"],
                "subject": email_data["subject"],
                "body": email_data["page_content"],
                "id": email_data["id"],
            }
        },
        multitask_strategy="rollback",
    )
    print(f"Run created successfully with thread ID: {thread_id}")
    return thread_id, run


async def fetch_and_process_emails(args):
    """Fetch QQ Mail messages and process them through LangGraph."""
    processed_count = 0
    try:
        emails = list(
            fetch_group_emails(
                args.email,
                minutes_since=args.minutes_since,
                include_read=args.include_read,
                skip_filters=args.skip_filters,
            )
        )
    except Exception as e:
        print(f"Failed to fetch QQ Mail messages: {str(e)}")
        return 1

    if not emails:
        print("No emails found matching the criteria")
        return 0

    print(f"Found {len(emails)} emails")
    for i, email_data in enumerate(emails):
        if args.early and i > 0:
            print(f"Early stop after processing {i} emails")
            break
        if email_data.get("user_respond", False) and not args.skip_filters:
            print(f"Skipping thread already answered by you: {email_data['thread_id']}")
            continue

        print(f"\nProcessing email {i + 1}/{len(emails)}:")
        print(f"From: {email_data['from_email']}")
        print(f"Subject: {email_data['subject']}")

        await ingest_email_to_langgraph(email_data, args.graph_name, url=args.url)
        processed_count += 1

    print(f"\nProcessed {processed_count} emails successfully")
    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="QQ Mail ingestion for LangGraph")
    parser.add_argument("--email", type=str, required=True, help="QQ email address to fetch messages for")
    parser.add_argument("--minutes-since", type=int, default=120, help="Only retrieve emails newer than this many minutes")
    parser.add_argument(
        "--graph-name",
        type=str,
        default="email_assistant_hitl_memory_qqmail",
        help="Name of the LangGraph graph to use",
    )
    parser.add_argument("--url", type=str, default="http://127.0.0.1:2024", help="LangGraph deployment URL")
    parser.add_argument("--early", action="store_true", help="Early stop after processing one email")
    parser.add_argument("--include-read", action="store_true", help="Include emails that have already been read")
    parser.add_argument("--skip-filters", action="store_true", help="Skip sender/read filtering")
    return parser.parse_args()


if __name__ == "__main__":
    exit(asyncio.run(fetch_and_process_emails(parse_args())))
