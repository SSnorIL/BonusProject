# PRD: Gmail and Google Calendar Agent

## Objective

Build a Python agent that connects to a Gmail account and Google Calendar using Google OAuth, scans recent Gmail messages, detects free-text meeting requests, and schedules valid meetings only when the calendar is available.

## Scope

The project works only with Gmail and Google Calendar. It does not support Outlook, company mail systems, or non-Google calendars.

## Functional Requirements

1. Authenticate with Google using OAuth and local token storage.
2. Read Gmail messages from the last two days by default.
3. Detect whether an email is a meeting request written in free text.
4. Distinguish between meeting emails and non-meeting emails.
5. Extract meeting details:
   - Date.
   - Start time.
   - Duration or end time.
   - Participants when available.
   - Location or meeting link when available.
   - Meeting topic or title.
6. Treat date, start time, duration or end time, and meeting topic as required fields.
7. If required details are missing, reply to the original sender asking for the missing details.
8. If all required details exist, check Google Calendar availability.
9. If the calendar is free, create a Google Calendar event.
10. If the calendar is busy, reply to the sender with: `לא ניתן לקיים את הפגישה.`
11. If no meeting emails are found, send an email to the scanned account saying: `No meetings were found in this email.`

## Non-Functional Requirements

- Do not request or store the user's Google password.
- Use OAuth scopes required for Gmail modification and Calendar access.
- Keep credentials and tokens local.
- Avoid duplicate handling by labeling processed Gmail messages.
- Avoid duplicate calendar events by storing Gmail message metadata in Calendar event extended properties.

## Acceptance Criteria

- The script can authenticate using `credentials.json` and `token.json`.
- The script can scan Gmail messages from the last two days.
- The script can classify at least two email types: meeting request and non-meeting message.
- Incomplete meeting emails receive a missing-details reply.
- Complete meeting emails are checked against Google Calendar availability.
- Available meetings are inserted into Google Calendar.
- Busy meeting slots trigger the required Hebrew reply.
- The project includes `README.md`, `PRD.md`, `PLAN.md`, and `TODO.md`.
