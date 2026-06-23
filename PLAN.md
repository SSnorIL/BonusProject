# Implementation Plan

## 1. Project Setup

- Keep the project as a Python application.
- Use the existing Google API dependencies in `pyproject.toml`.
- Store OAuth client credentials in `credentials.json`.
- Store OAuth tokens in `token.json` after first authorization.

## 2. Gmail Integration

- Build a Gmail API service with OAuth credentials.
- Search Gmail using a default query for the last two days.
- Exclude spam and trash by default.
- Fetch subject, sender, message headers, received date, and body text.
- Decode plain text and HTML message bodies.

## 3. Meeting Detection

- Identify free-text meeting requests using meeting-related terms and date/time signals.
- Ignore unrelated emails.
- Keep detection conservative enough to distinguish meeting messages from ordinary messages.

## 4. Detail Extraction

- Extract date from ISO dates, slash dates, month names, `today`, `tomorrow`, and weekdays.
- Extract start time from 24-hour and AM/PM expressions.
- Extract duration from minute and hour expressions.
- Extract location from common video links or `location` / `where` fields.
- Extract attendee email addresses from the message body.
- Generate a title from the subject or first useful body line.

## 5. Missing Data Flow

- Treat date, start time, duration or end time, and meeting topic as mandatory.
- Reply to the original sender when mandatory data is missing.
- Include the missing fields in the reply.
- Label processed messages to reduce duplicate replies.

## 6. Calendar Flow

- Convert meeting date and time to the configured time zone.
- Check Google Calendar availability with the freebusy API.
- If the slot is free, create a calendar event.
- If the slot is busy, reply to the sender that the meeting cannot be held.
- Store Gmail message metadata on the calendar event to reduce duplicate event creation.

## 7. Verification

- Run Python syntax checks.
- Run the script with the existing OAuth setup.
- Confirm output logs for:
  - Non-meeting detection.
  - Missing-parameter replies.
  - Busy-calendar replies.
  - Calendar event creation.
  - No-meetings-found notification.

## 8. Local Submission Files

- Keep `README.md` in the project root.
- Keep Markdown documents for `PRD`, `PLAN`, and `TODO`.
- Do not upload or push anything from this environment.
