# Gmail Calendar Agent

Bonus assignment project for an AI-style Gmail and Google Calendar agent.

The program scans recent Gmail messages, detects free-text meeting requests, extracts meeting details, checks Google Calendar availability, and either creates a calendar event or replies to the sender when the meeting cannot be scheduled.

## Project Files

- `main.py` - main Gmail and Google Calendar automation script.
- `pyproject.toml` - Python project dependencies.
- `credentials.json` - local Google OAuth client credentials.
- `token.json` - local OAuth token created after first authorization.
- `PRD.md` - product requirements document.
- `PLAN.md` - implementation plan.
- `TODO.md` - remaining task checklist.

## Requirements Covered

- Uses Gmail only.
- Uses Google OAuth token-based authentication.
- Scans messages from the last two days by default.
- Detects meeting requests written in free text.
- Extracts date, start time, duration, location, and attendees where possible.
- Treats date, start time, title or topic, and duration or end time as required fields.
- Replies to the sender when required meeting data is missing.
- Checks Google Calendar availability before creating an event.
- Creates a Google Calendar event when the requested time is available.
- Replies with `לא ניתן לקיים את הפגישה.` when the calendar is busy.
- Sends a no-meetings-found notification when no meeting emails are detected.

## Setup

Install dependencies:

```powershell
uv sync
```

Required Google OAuth scopes:

```text
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
```

The Google Cloud project must have both Gmail API and Google Calendar API enabled.

## Run

```powershell
uv run main.py
```

Or with the local virtual environment:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

Optional arguments:

```powershell
.\.venv\Scripts\python.exe .\main.py --query "newer_than:2d -in:spam -in:trash" --limit 25 --calendar-id primary --time-zone Asia/Jerusalem
```

## Security Notes

`credentials.json` and `token.json` are local authentication files. They should not be shared publicly.


---

# Execution Screenshots

## 1. Initial TOML parsing error
![Initial TOML parsing error](1(2).png)

## 2. Dependencies installed and first Python syntax error
![Dependencies installed and first Python syntax error](2(2).png)

## 3. Gmail draft creation and Calendar event creation
![Gmail draft creation and Calendar event creation](3(3).png)

## 4. Gmail draft created
![Gmail draft created](4(1).png)

## 5. Google Calendar event
![Google Calendar event](5(1).png)

## 6. Gmail reply example
![Gmail reply example](6(1).png)

## 7. Successful processing summary
![Successful processing summary](7(1).png)

## 8. Screenshot 1
![Screenshot 1](Screenshot_1(3).png)

## 9. Screenshot 2
![Screenshot 2](Screenshot_2(1).png)

## 10. Screenshot 3
![Screenshot 3](Screenshot_3(1).png)
