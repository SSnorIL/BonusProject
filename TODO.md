# TODO

## Done

- [x] Create a PRD for the Gmail and Calendar agent.
- [x] Implement Google OAuth authentication.
- [x] Configure required Google scopes.
- [x] Scan Gmail messages from the last two days by default.
- [x] Detect likely free-text meeting requests.
- [x] Distinguish non-meeting emails from meeting emails.
- [x] Extract date, start time, duration, location, attendees, and title where available.
- [x] Reply when mandatory meeting parameters are missing.
- [x] Check Google Calendar availability before creating an event.
- [x] Create Google Calendar events when the slot is available.
- [x] Reply with `לא ניתן לקיים את הפגישה.` when the slot is busy.
- [x] Send a no-meetings-found email when no meeting emails are detected.
- [x] Add local `README.md`, `PRD.md`, `PLAN.md`, and `TODO.md`.

## Remaining Manual / User Actions

- [ ] Verify in Google Cloud Console that Gmail API is enabled.
- [ ] Verify in Google Cloud Console that Google Calendar API is enabled.
- [ ] Verify the OAuth consent screen includes the required scopes.
- [ ] Verify the Gmail account is listed as a test user while the app is in testing mode.
- [ ] Keep `credentials.json` and `token.json` private.
- [ ] Manually review sent replies and created calendar events after each real run.

## Optional Improvements

- [ ] Replace rule-based extraction with an LLM parser for stronger free-text understanding.
- [ ] Add automated unit tests for parsing date, time, duration, attendees, and meeting detection.
- [ ] Add a dry-run mode that prints intended actions without sending email or creating events.
- [ ] Add a configurable processed label name.
