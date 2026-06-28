from __future__ import annotations

import argparse
import base64
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
DEFAULT_TIME_ZONE = os.getenv("DEFAULT_TIME_ZONE", "Asia/Jerusalem")
DEFAULT_CALENDAR_ID = os.getenv("DEFAULT_CALENDAR_ID", "primary")
DEFAULT_DURATION_MINUTES = os.getenv("DEFAULT_MEETING_DURATION_MINUTES")
DEFAULT_PROCESSED_LABEL = os.getenv("PROCESSED_LABEL", "MeetingSkillProcessed")

MEETING_KEYWORDS = (
    "meeting",
    "meet",
    "call",
    "appointment",
    "sync",
    "interview",
    "demo",
    "review",
    "session",
    "check-in",
    "schedule",
    "calendar",
    "invite",
    "discussion",
)

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class GmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    message_id_header: str
    references: str
    received_at: datetime
    body: str


@dataclass(frozen=True)
class MeetingDetails:
    title: str | None
    meeting_date: date | None
    start_time: time | None
    duration_minutes: int | None
    location: str | None
    attendees: list[str]

    @property
    def missing_fields(self) -> list[str]:
        missing = []
        if self.meeting_date is None:
            missing.append("date")
        if self.start_time is None:
            missing.append("start time")
        if self.title is None:
            missing.append("meeting title or topic")
        if self.duration_minutes is None:
            missing.append("end time or duration")
        return missing


def get_credentials() -> Credentials:
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_header(headers: Iterable[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def decode_body(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode()).decode(
        "utf-8",
        errors="replace",
    )


def extract_text_from_payload(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return decode_body(body_data)

    if mime_type == "text/html" and body_data:
        html = decode_body(body_data)
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    parts = payload.get("parts", [])
    return "\n".join(
        part_text
        for part in parts
        if (part_text := extract_text_from_payload(part))
    )


def fetch_message(gmail_service, message_id: str) -> GmailMessage:
    message = (
        gmail_service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = get_header(headers, "Subject")
    sender = get_header(headers, "From")
    message_id_header = get_header(headers, "Message-ID")
    references = get_header(headers, "References")
    date_header = get_header(headers, "Date")
    received_at = parsedate_to_datetime(date_header) if date_header else datetime.now().astimezone()
    sender_name, sender_email = parseaddr(sender)

    return GmailMessage(
        id=message["id"],
        thread_id=message["threadId"],
        subject=subject,
        sender=sender_name or sender_email,
        sender_email=sender_email,
        message_id_header=message_id_header,
        references=references,
        received_at=received_at,
        body=extract_text_from_payload(payload),
    )


def list_messages(gmail_service, query: str, limit: int) -> list[str]:
    response = (
        gmail_service.users()
        .messages()
        .list(
            userId="me",
            q=query,
            maxResults=limit,
        )
        .execute()
    )
    return [message["id"] for message in response.get("messages", [])]


def get_or_create_label(gmail_service, label_name: str) -> str:
    labels = gmail_service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label.get("name") == label_name:
            return label["id"]

    created = (
        gmail_service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def mark_processed(gmail_service, message_id: str, label_id: str) -> None:
    gmail_service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()


def looks_like_meeting(message: GmailMessage) -> bool:
    text = f"{message.subject}\n{message.body}".lower()
    has_keyword = any(keyword in text for keyword in MEETING_KEYWORDS)
    has_time = re.search(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*(am|pm)\b", text)
    has_date = (
        re.search(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b", text)
        or any(month in text for month in MONTHS)
        or "tomorrow" in text
        or "today" in text
        or any(day in text for day in WEEKDAYS)
    )
    return has_keyword and bool(has_time or has_date or "schedule" in text)


def parse_date(text: str, received_at: datetime) -> date | None:
    lowered = text.lower()

    if match := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", lowered):
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    if match := re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", lowered):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None

    base = received_at.date()
    if "today" in lowered:
        return base
    if "tomorrow" in lowered:
        return base + timedelta(days=1)

    for month_name, month_number in MONTHS.items():
        if match := re.search(rf"\b{month_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", lowered):
            try:
                candidate = date(base.year, month_number, int(match.group(1)))
            except ValueError:
                return None
            if candidate < base:
                candidate = date(base.year + 1, month_number, int(match.group(1)))
            return candidate

    next_week = "next " in lowered
    for weekday_name, weekday_number in WEEKDAYS.items():
        if weekday_name in lowered:
            days_ahead = weekday_number - base.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            if next_week:
                days_ahead += 7
            return base + timedelta(days=days_ahead)

    return None


def parse_time(text: str) -> time | None:
    lowered = text.lower()

    if match := re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", lowered):
        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        try:
            return time(hour, minute)
        except ValueError:
            return None

    if match := re.search(r"\b(\d{1,2})\s*(am|pm)\b", lowered):
        hour = int(match.group(1))
        meridiem = match.group(2)
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        try:
            return time(hour, 0)
        except ValueError:
            return None

    return None


def parse_duration_minutes(text: str, start_time: time | None = None) -> int | None:
    lowered = text.lower()

    if match := re.search(r"\bfor\s+(\d+)\s*(minutes?|mins?)\b", lowered):
        duration = int(match.group(1))
        return duration if duration > 0 else None

    if match := re.search(r"\bfor\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?)\b", lowered):
        duration = int(float(match.group(1)) * 60)
        return duration if duration > 0 else None

    end_match = re.search(
        r"\b(?:to|until|till|-)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        lowered,
    )
    if start_time is not None and end_match:
        end_hour = int(end_match.group(1))
        end_minute = int(end_match.group(2) or 0)
        meridiem = end_match.group(3)
        if meridiem == "pm" and end_hour < 12:
            end_hour += 12
        if meridiem == "am" and end_hour == 12:
            end_hour = 0
        try:
            end_time = time(end_hour, end_minute)
        except ValueError:
            return None
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        return end_minutes - start_minutes

    if DEFAULT_DURATION_MINUTES:
        try:
            duration = int(DEFAULT_DURATION_MINUTES)
            return duration if duration > 0 else None
        except ValueError:
            return None

    return None


def parse_location(text: str) -> str | None:
    if match := re.search(r"(https://meet\.google\.com/[^\s]+|https://zoom\.us/[^\s]+|https://teams\.microsoft\.com/[^\s]+)", text):
        return match.group(1).rstrip(".,)")
    if match := re.search(r"\b(?:location|where):\s*(.+)", text, re.IGNORECASE):
        return match.group(1).strip()
    return None


def parse_attendees(text: str, sender_email: str) -> list[str]:
    emails = {
        email.lower()
        for email in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    }
    emails.discard(sender_email.lower())
    return sorted(emails)


def clean_title(subject: str, body: str) -> str | None:
    subject = re.sub(r"^(re|fw|fwd):\s*", "", subject.strip(), flags=re.IGNORECASE)
    if subject and len(subject) > 3 and subject.lower() not in {"meeting", "call", "schedule"}:
        return subject[:120]

    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    if first_line:
        words = first_line.split()
        return " ".join(words[:8]).rstrip(".,")[:120]

    return None


def parse_meeting_details(message: GmailMessage) -> MeetingDetails:
    text = f"{message.subject}\n{message.body}"
    start_time = parse_time(text)
    return MeetingDetails(
        title=clean_title(message.subject, message.body),
        meeting_date=parse_date(text, message.received_at),
        start_time=start_time,
        duration_minutes=parse_duration_minutes(text, start_time),
        location=parse_location(text),
        attendees=parse_attendees(text, message.sender_email),
    )


def encoded_email(message: EmailMessage) -> str:
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def send_email(gmail_service, to_address: str, subject: str, body: str) -> None:
    email = EmailMessage()
    email["To"] = to_address
    email["Subject"] = subject
    email.set_content(body)

    gmail_service.users().messages().send(
        userId="me",
        body={"raw": encoded_email(email)},
    ).execute()


def send_missing_parameter_reply(
    gmail_service,
    message: GmailMessage,
    missing_fields: list[str],
) -> None:
    email = EmailMessage()
    email["To"] = message.sender_email
    email["Subject"] = f"Re: {message.subject}" if message.subject else "Re: Meeting request"
    if message.message_id_header:
        email["In-Reply-To"] = message.message_id_header
    references = " ".join(
        item for item in [message.references, message.message_id_header] if item
    )
    if references:
        email["References"] = references

    fields = "\n".join(f"- {field}" for field in missing_fields)
    email.set_content(
        "Thank you for the meeting request. I need the following information "
        "before I can add it to the calendar:\n\n"
        f"{fields}\n\n"
        "Please reply with the missing details."
    )

    gmail_service.users().messages().send(
        userId="me",
        body={
            "raw": encoded_email(email),
            "threadId": message.thread_id,
        },
    ).execute()


def send_busy_reply(gmail_service, message: GmailMessage) -> None:
    email = EmailMessage()
    email["To"] = message.sender_email
    email["Subject"] = f"Re: {message.subject}" if message.subject else "Re: Meeting request"
    if message.message_id_header:
        email["In-Reply-To"] = message.message_id_header
    references = " ".join(
        item for item in [message.references, message.message_id_header] if item
    )
    if references:
        email["References"] = references
    email.set_content("לא ניתן לקיים את הפגישה.")

    gmail_service.users().messages().send(
        userId="me",
        body={
            "raw": encoded_email(email),
            "threadId": message.thread_id,
        },
    ).execute()


def event_exists(calendar_service, calendar_id: str, message_id: str) -> bool:
    response = (
        calendar_service.events()
        .list(
            calendarId=calendar_id,
            privateExtendedProperty=f"gmailMessageId={message_id}",
            maxResults=1,
            singleEvents=True,
        )
        .execute()
    )
    return bool(response.get("items"))


def event_times(details: MeetingDetails, time_zone: str) -> tuple[datetime, datetime] | None:
    if details.meeting_date is None or details.start_time is None or details.duration_minutes is None:
        return None

    zone = ZoneInfo(time_zone)
    start = datetime.combine(details.meeting_date, details.start_time, tzinfo=zone)
    end = start + timedelta(minutes=details.duration_minutes)
    return start, end


def calendar_is_available(
    calendar_service,
    calendar_id: str,
    start: datetime,
    end: datetime,
    time_zone: str,
) -> bool:
    response = (
        calendar_service.freebusy()
        .query(
            body={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "timeZone": time_zone,
                "items": [{"id": calendar_id}],
            }
        )
        .execute()
    )
    busy = response.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    return not busy


def create_calendar_event(
    calendar_service,
    calendar_id: str,
    message: GmailMessage,
    details: MeetingDetails,
    time_zone: str,
) -> str | None:
    times = event_times(details, time_zone)
    if times is None or event_exists(calendar_service, calendar_id, message.id):
        return None

    start, end = times
    event = {
        "summary": details.title or "Meeting",
        "description": (
            f"Created from Gmail message {message.id}.\n\n"
            f"From: {message.sender} <{message.sender_email}>\n\n"
            f"{message.body[:4000]}"
        ),
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": time_zone,
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": time_zone,
        },
        "extendedProperties": {
            "private": {
                "gmailMessageId": message.id,
                "gmailThreadId": message.thread_id,
            }
        },
    }
    if details.location:
        event["location"] = details.location
    if details.attendees:
        event["attendees"] = [{"email": attendee} for attendee in details.attendees]

    created = (
        calendar_service.events()
        .insert(calendarId=calendar_id, body=event)
        .execute()
    )
    return created["id"]


def process_mailbox(query: str, limit: int, calendar_id: str, time_zone: str) -> None:
    creds = get_credentials()
    gmail_service = build("gmail", "v1", credentials=creds)
    calendar_service = build("calendar", "v3", credentials=creds)
    processed_label_id = get_or_create_label(gmail_service, PROCESSED_LABEL)
    profile = gmail_service.users().getProfile(userId="me").execute()
    scanned_email = profile["emailAddress"]

    message_ids = list_messages(
        gmail_service,
        f"({query}) -label:{PROCESSED_LABEL}",
        limit,
    )
    meeting_count = 0

    for message_id in message_ids:
        message = fetch_message(gmail_service, message_id)
        if not looks_like_meeting(message):
            print(f"No meeting detected: {message.subject or message.id}")
            continue

        meeting_count += 1
        details = parse_meeting_details(message)

        if details.missing_fields:
            send_missing_parameter_reply(gmail_service, message, details.missing_fields)
            mark_processed(gmail_service, message.id, processed_label_id)
            print(
                "Missing-parameter reply sent: "
                f"{message.subject or message.id} ({', '.join(details.missing_fields)})"
            )
            continue

        times = event_times(details, time_zone)
        if times is None:
            send_missing_parameter_reply(gmail_service, message, ["valid date, start time, and duration"])
            mark_processed(gmail_service, message.id, processed_label_id)
            print(f"Missing-parameter reply sent: {message.subject or message.id}")
            continue

        start, end = times
        if not calendar_is_available(calendar_service, calendar_id, start, end, time_zone):
            send_busy_reply(gmail_service, message)
            mark_processed(gmail_service, message.id, processed_label_id)
            print(f"Calendar busy reply sent: {message.subject or message.id}")
            continue

        event_id = create_calendar_event(
            calendar_service,
            calendar_id,
            message,
            details,
            time_zone,
        )
        mark_processed(gmail_service, message.id, processed_label_id)
        if event_id:
            print(f"Calendar event created: {event_id} for {message.subject or message.id}")
        else:
            print(f"Skipped duplicate calendar event: {message.subject or message.id}")

    if meeting_count == 0:
        send_email(
            gmail_service,
            scanned_email,
            "No meetings found",
            "No meetings were found in this email.",
        )
        print("No meeting emails found. Notification email sent.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Gmail for meeting emails and add complete meetings to Google Calendar.",
    )
    parser.add_argument(
        "--query",
        default="newer_than:2d -in:spam -in:trash",
        help="Gmail search query to scan.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of Gmail messages to inspect.",
    )
    parser.add_argument(
        "--calendar-id",
        default=DEFAULT_CALENDAR_ID,
        help="Google Calendar ID to create events in.",
    )
    parser.add_argument(
        "--time-zone",
        default=DEFAULT_TIME_ZONE,
        help="Time zone used to resolve event dates and times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    process_mailbox(
        query=args.query,
        limit=args.limit,
        calendar_id=args.calendar_id,
        time_zone=args.time_zone,
    )


if __name__ == "__main__":
    main()


